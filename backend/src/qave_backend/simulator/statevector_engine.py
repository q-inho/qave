"""Core NumPy statevector engine for Backend A."""

from __future__ import annotations

import hashlib
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from qave_backend.contracts.models import GateOp, QuantumCircuitIR, SimulationRequest
from qave_backend.ir.models import (
    EvolutionState,
    MeasurementExecution,
    StepSnapshot,
    canonicalize_global_phase,
)
from qave_backend.simulator.gates import (
    UnsupportedGateError,
    apply_unitary,
    fractional_unitary,
    matrix_for_gate,
)

PHASE_RATIOS = {
    "pre_gate": 0.2,
    "apply_gate": 0.55,
    "settle": 0.25,
}

PROFILE_SUBSTEP_COUNT = {
    "teaching_default": 24,
    "analysis_slow": 48,
    "presentation_fast": 12,
}


class StatevectorEngine:
    """Pure-state stepwise simulator."""

    def initialize_state(self, num_qubits: int) -> NDArray[np.complex128]:
        """Initialize state."""
        state = np.zeros(2**num_qubits, dtype=np.complex128)
        state[0] = 1.0 + 0.0j
        return state

    def apply_gate(
        self,
        state: NDArray[np.complex128],
        gate: GateOp,
        num_qubits: int,
    ) -> NDArray[np.complex128]:
        """Apply gate."""
        if gate.kind != "unitary":
            return state.copy()

        matrix, qubits = matrix_for_gate(gate)
        return apply_unitary(state, matrix, qubits, num_qubits)

    def step(self, ir: QuantumCircuitIR, req: SimulationRequest) -> list[StepSnapshot]:
        """Step."""
        snapshots: list[StepSnapshot] = []
        state = self.initialize_state(ir.qubits)
        total_substeps = self._substep_count(req.animation_profile)
        schedule = self._phase_schedule(total_substeps)
        rng = np.random.default_rng(req.seed)

        for idx, gate in enumerate(ir.steps):
            state_before = state.copy()
            measurement_execution: MeasurementExecution | None = None
            if gate.kind == "unitary":
                matrix, qubits = matrix_for_gate(gate)
                state = apply_unitary(state, matrix, qubits, ir.qubits)
                evolution_states = self._unitary_evolution(
                    state_before=state_before,
                    state_after=state,
                    unitary=matrix,
                    qubits=qubits,
                    num_qubits=ir.qubits,
                    schedule=schedule,
                )
            elif gate.kind == "measurement":
                probabilities = self._measurement_probabilities(state, gate.targets)
                outcomes = [
                    (self._outcome_label(outcome_idx, len(gate.targets)), float(probability))
                    for outcome_idx, probability in enumerate(probabilities)
                ]
                if req.measurement_mode != "collapse":
                    msg = "measurement_mode must be 'collapse'; branching is no longer supported"
                    raise UnsupportedGateError(msg)
                outcome_index = self._sample_outcome(rng, probabilities)
                selected_outcome = self._outcome_label(outcome_index, len(gate.targets))
                state = self._collapse_state(state, gate.targets, outcome_index)
                measurement_gate_matrix = self._measurement_projector_matrix(
                    outcome_index,
                    len(gate.targets),
                )

                measurement_execution = MeasurementExecution(
                    qubits=list(gate.targets),
                    outcomes=outcomes,
                    selected_outcome=selected_outcome,
                    deferred=False,
                )
                evolution_states = self._constant_evolution(
                    state,
                    schedule,
                    gate_matrix=measurement_gate_matrix,
                )
            elif gate.kind == "reset":
                state, sampled_bits = self._execute_reset(state, gate.targets, rng)
                reset_gate_matrix = self._reset_branch_matrix(sampled_bits)
                evolution_states = self._constant_evolution(
                    state,
                    schedule,
                    gate_matrix=reset_gate_matrix,
                )
            else:
                msg = f"Unknown gate kind {gate.kind!r}"
                raise UnsupportedGateError(msg)

            snapshots.append(
                StepSnapshot(
                    step_index=idx,
                    gate=gate,
                    state_before=state_before,
                    state_after=state.copy(),
                    evolution_states=evolution_states,
                    measurement_execution=measurement_execution,
                )
            )

        return snapshots

    @staticmethod
    def state_hash(state: NDArray[np.complex128]) -> str:
        """Build deterministic state hash after phase and signed-zero canonicalization."""
        canonical = canonicalize_global_phase(state)
        rounded = np.round(np.column_stack((canonical.real, canonical.imag)), decimals=12)
        rounded[rounded == 0.0] = 0.0
        return hashlib.sha256(rounded.tobytes()).hexdigest()

    @staticmethod
    def _substep_count(animation_profile: str) -> int:
        """Resolve the configured number of in-gate evolution samples."""
        return PROFILE_SUBSTEP_COUNT.get(animation_profile, 24)

    @staticmethod
    def _phase_schedule(
        total_substeps: int,
    ) -> list[tuple[Literal["pre_gate", "apply_gate", "settle"], float, float]]:
        """Build ordered phase schedule tuples of `(phase, t_normalized, tau)`."""
        total = max(6, total_substeps)

        pre_count = max(1, round(total * PHASE_RATIOS["pre_gate"]))
        apply_count = max(2, round(total * PHASE_RATIOS["apply_gate"]))
        settle_count = max(1, total - pre_count - apply_count)

        schedule: list[tuple[Literal["pre_gate", "apply_gate", "settle"], float, float]] = []

        for idx in range(pre_count):
            frac = idx / float(pre_count) if pre_count > 0 else 0.0
            t_norm = PHASE_RATIOS["pre_gate"] * frac
            schedule.append(("pre_gate", float(t_norm), 0.0))

        for idx in range(apply_count):
            frac = idx / float(max(1, apply_count - 1))
            t_norm = PHASE_RATIOS["pre_gate"] + PHASE_RATIOS["apply_gate"] * frac
            schedule.append(("apply_gate", float(t_norm), float(frac)))

        for idx in range(1, settle_count + 1):
            frac = idx / float(settle_count)
            t_norm = (
                PHASE_RATIOS["pre_gate"]
                + PHASE_RATIOS["apply_gate"]
                + PHASE_RATIOS["settle"] * frac
            )
            schedule.append(("settle", float(t_norm), 1.0))

        return schedule

    @staticmethod
    def _constant_evolution(
        state: NDArray[np.complex128],
        schedule: list[tuple[Literal["pre_gate", "apply_gate", "settle"], float, float]],
        gate_matrix: NDArray[np.complex128] | None = None,
    ) -> list[EvolutionState]:
        """Emit static evolution samples that hold one state across all phases."""
        evolution_states: list[EvolutionState] = []
        for sample_index, (phase, t_normalized, _) in enumerate(schedule):
            evolution_states.append(
                EvolutionState(
                    sample_index=sample_index,
                    phase=phase,
                    t_normalized=t_normalized,
                    state=state.copy(),
                    gate_matrix=(
                        gate_matrix.astype(np.complex128, copy=True)
                        if gate_matrix is not None
                        else None
                    ),
                )
            )
        return evolution_states

    @staticmethod
    def _measurement_probabilities(
        state: NDArray[np.complex128],
        qubits: list[int],
    ) -> NDArray[np.float64]:
        """Compute normalized outcome probabilities for measured qubits."""
        if not qubits:
            return np.array([1.0], dtype=np.float64)

        indices = np.arange(state.shape[0], dtype=np.int64)
        outcome_indices = np.zeros_like(indices)
        for bit_index, qubit in enumerate(qubits):
            outcome_indices |= ((indices >> qubit) & 1) << bit_index

        probabilities = np.bincount(
            outcome_indices,
            weights=np.abs(state) ** 2,
            minlength=2 ** len(qubits),
        ).astype(np.float64)
        total = float(probabilities.sum())
        if total <= 1e-15:
            probabilities = np.zeros_like(probabilities)
            probabilities[0] = 1.0
            return probabilities
        probabilities /= total
        return probabilities

    @staticmethod
    def _outcome_label(outcome_index: int, width: int) -> str:
        """Format a measurement outcome index as fixed-width binary text."""
        return format(outcome_index, f"0{max(1, width)}b")

    @staticmethod
    def _sample_outcome(
        rng: np.random.Generator,
        probabilities: NDArray[np.float64],
    ) -> int:
        """Sample one measurement outcome index from a probability vector."""
        return int(rng.choice(probabilities.size, p=probabilities))

    @staticmethod
    def _collapse_state(
        state: NDArray[np.complex128],
        qubits: list[int],
        outcome_index: int,
    ) -> NDArray[np.complex128]:
        """Project a state onto one measurement outcome and renormalize."""
        if not qubits:
            return state.copy()

        indices = np.arange(state.shape[0], dtype=np.int64)
        outcome_indices = np.zeros_like(indices)
        for bit_index, qubit in enumerate(qubits):
            outcome_indices |= ((indices >> qubit) & 1) << bit_index
        mask = outcome_indices == outcome_index

        collapsed = np.where(mask, state, np.complex128(0.0 + 0.0j))
        norm = float(np.linalg.norm(collapsed))
        if norm <= 1e-15:
            return state.copy()
        collapsed_normalized = collapsed / norm
        return collapsed_normalized.astype(np.complex128)

    @staticmethod
    def _measurement_projector_matrix(
        outcome_index: int,
        width: int,
    ) -> NDArray[np.complex128]:
        """Build the projector matrix corresponding to a sampled outcome branch."""
        dimension = 1 << max(0, width)
        projector = np.zeros((dimension, dimension), dtype=np.complex128)
        little_endian_index = int(np.clip(outcome_index, 0, max(0, dimension - 1)))
        index = StatevectorEngine._little_endian_to_matrix_basis_index(
            little_endian_index,
            width,
        )
        projector[index, index] = 1.0 + 0.0j
        return projector

    @staticmethod
    def _reset_branch_matrix(sampled_bits: list[int]) -> NDArray[np.complex128]:
        """Build a linear operator encoding the sampled reset branch transition."""
        width = len(sampled_bits)
        dimension = 1 << width
        operator = np.zeros((dimension, dimension), dtype=np.complex128)
        sampled_little_endian_index = 0
        for bit_index, bit in enumerate(sampled_bits):
            sampled_little_endian_index |= (int(bit) & 1) << bit_index
        sampled_index = StatevectorEngine._little_endian_to_matrix_basis_index(
            sampled_little_endian_index,
            width,
        )
        operator[0, sampled_index] = 1.0 + 0.0j
        return operator

    @staticmethod
    def _little_endian_to_matrix_basis_index(index: int, width: int) -> int:
        """Convert little-endian outcome bits to matrix-basis index ordering."""
        safe_width = max(0, int(width))
        mapped = 0
        for bit_index in range(safe_width):
            bit = (int(index) >> bit_index) & 1
            mapped |= bit << (safe_width - bit_index - 1)
        return mapped

    @staticmethod
    def _apply_x_to_qubit(
        state: NDArray[np.complex128],
        qubit: int,
    ) -> NDArray[np.complex128]:
        """Apply an X permutation to one qubit in the statevector basis."""
        indices = np.arange(state.shape[0], dtype=np.int64)
        flipped = np.bitwise_xor(indices, 1 << qubit)
        updated = np.zeros_like(state)
        updated[flipped] = state
        return updated

    def _execute_reset(
        self,
        state: NDArray[np.complex128],
        targets: list[int],
        rng: np.random.Generator,
    ) -> tuple[NDArray[np.complex128], list[int]]:
        """Execute reset by measuring each target and conditionally applying X."""
        updated = state.copy()
        sampled_bits: list[int] = []
        for qubit in targets:
            probabilities = self._measurement_probabilities(updated, [qubit])
            outcome_index = self._sample_outcome(rng, probabilities)
            sampled_bits.append(int(outcome_index) & 1)
            updated = self._collapse_state(updated, [qubit], outcome_index)
            if outcome_index == 1:
                updated = self._apply_x_to_qubit(updated, qubit)
        return updated, sampled_bits

    @staticmethod
    def _unitary_evolution(
        state_before: NDArray[np.complex128],
        state_after: NDArray[np.complex128],
        unitary: NDArray[np.complex128],
        qubits: list[int],
        num_qubits: int,
        schedule: list[tuple[Literal["pre_gate", "apply_gate", "settle"], float, float]],
    ) -> list[EvolutionState]:
        """Emit physically sampled in-gate states from fractional unitaries."""
        evolution_states: list[EvolutionState] = []
        dim = unitary.shape[0]

        for sample_index, (phase, t_normalized, tau) in enumerate(schedule):
            if np.isclose(tau, 0.0):
                state_sample = state_before.copy()
                matrix_sample = np.eye(dim, dtype=np.complex128)
            elif np.isclose(tau, 1.0):
                state_sample = state_after.copy()
                matrix_sample = unitary.astype(np.complex128, copy=True)
            else:
                unitary_tau = fractional_unitary(unitary, tau)
                state_sample = apply_unitary(state_before, unitary_tau, qubits, num_qubits)
                matrix_sample = unitary_tau

            evolution_states.append(
                EvolutionState(
                    sample_index=sample_index,
                    phase=phase,
                    t_normalized=t_normalized,
                    state=state_sample,
                    gate_matrix=matrix_sample,
                )
            )

        return evolution_states
