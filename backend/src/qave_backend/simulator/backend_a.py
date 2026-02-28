"""Backend A orchestration for pure-state statevector simulation."""

from __future__ import annotations

import time
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from qave_backend.contracts.models import (
    AlgorithmTrace,
    AmplitudeComplex,
    AnimationKeyframe,
    AnimationPhaseRatio,
    AnimationTimelineSpec,
    ApproximationPolicy,
    BackendCapability,
    BasisProbability,
    BoundaryCheckpoint,
    ConventionCheck,
    Diagnostic,
    GateMatrixSample,
    GateOp,
    MeasurementHistogramEntry,
    MeasurementOutcome,
    MeasurementShotReplay,
    MeasurementShotReplayEvent,
    MeasurementShotReplayOutcome,
    MeasurementShotReplayState,
    MeasurementShotReplayTimeline,
    MeasurementStepInfo,
    ObservableSnapshot,
    PhaseWindow,
    QuantumCircuitIR,
    ReducedDensityBlock,
    ScalabilityPolicy,
    SimulationRequest,
    SimulationResult,
    StateCheckpoint,
    StateSummary,
    StepEvolutionSample,
    TopKAmplitude,
    TraceAnnotation,
    TraceStep,
    TransitionHints,
    ValidationCheck,
    ValidationReport,
)
from qave_backend.measurement.model import build_measurement_model
from qave_backend.observables.extractor import ObservableExtractor
from qave_backend.simulator.gates import UnsupportedGateError
from qave_backend.simulator.statevector_engine import StatevectorEngine
from qave_backend.validation.reference_qiskit import parity_error, reference_statevector

UNSUPPORTED_GATE = "UNSUPPORTED_GATE"
NUMERICAL_INSTABILITY = "NUMERICAL_INSTABILITY"
EVOLUTION_SETTLE_HASH_MISMATCH = "EVOLUTION_SETTLE_HASH_MISMATCH"
PARITY_PREFIX_ONLY = "PARITY_PREFIX_ONLY"
DEFAULT_SHOT_REPLAY_COUNT = 100
SHOT_REPLAY_CAMERA_PULLBACK_FRAMES = 36
SHOT_REPLAY_HISTOGRAM_PROJECT_FRAMES = 60
SHOT_REPLAY_FRAMES_PER_SHOT = 6
SHOT_REPLAY_SEED_MIX = 0x5DEECE66D


DEFAULT_SCALABILITY_POLICY = ScalabilityPolicy(
    small_n_max=8,
    medium_n_max=16,
    small_mode_features=["full_amplitudes", "bloch", "purity_entropy", "full_density"],
    medium_mode_features=["top_k_amplitudes", "bloch", "purity_entropy", "full_density"],
    large_mode_features=["full_density", "entanglement_metrics", "measurement_distribution"],
    approximation_policy=ApproximationPolicy(
        allow_approx_backends=True,
        fallback_backend_order=["statevector", "stabilizer", "tensor_network"],
    ),
)

DEFAULT_BACKEND_CAPABILITY = BackendCapability(
    backend_id="backend_a_statevector_numpy",
    supports_pure_state=True,
    supports_mixed_state=False,
    supports_noise=False,
    supports_approximation=False,
    max_recommended_qubits=16,
)


def _phase_windows() -> list[PhaseWindow]:
    """Return canonical per-step animation phase windows."""
    return [
        PhaseWindow(phase="pre_gate", t_start=0.0, t_end=0.2),
        PhaseWindow(phase="apply_gate", t_start=0.2, t_end=0.75),
        PhaseWindow(phase="settle", t_start=0.75, t_end=1.0),
    ]


def _build_timeline(
    trace_steps: list[TraceStep],
    step_duration_ms: int,
    contract_version: str,
) -> AnimationTimelineSpec:
    """Build timeline keyframes from emitted evolution samples or defaults."""
    keyframes: list[AnimationKeyframe] = []
    for step in trace_steps:
        if step.evolution_samples:
            for sample in step.evolution_samples:
                keyframes.append(
                    AnimationKeyframe(
                        frame_id=f"s{step.step_index}_sample_{sample.sample_index}",
                        step_index=step.step_index,
                        phase=sample.phase,
                        t_normalized=sample.t_normalized,
                    )
                )
            continue

        keyframes.extend(
            [
                AnimationKeyframe(
                    frame_id=f"s{step.step_index}_pre",
                    step_index=step.step_index,
                    phase="pre_gate",
                    t_normalized=0.0,
                ),
                AnimationKeyframe(
                    frame_id=f"s{step.step_index}_apply",
                    step_index=step.step_index,
                    phase="apply_gate",
                    t_normalized=0.2,
                ),
                AnimationKeyframe(
                    frame_id=f"s{step.step_index}_settle",
                    step_index=step.step_index,
                    phase="settle",
                    t_normalized=0.75,
                ),
            ]
        )

    return AnimationTimelineSpec(
        contract_version=contract_version,
        timeline_id="backend_a_timeline",
        total_steps=len(trace_steps),
        default_step_duration_ms=step_duration_ms,
        phase_ratio=AnimationPhaseRatio(pre_gate=0.2, apply_gate=0.55, settle=0.25),
        keyframes=keyframes,
        sync_fence_ids=[f"step_{step.step_index}" for step in trace_steps],
    )


def _state_vector_output(state: np.ndarray) -> list[list[float]]:
    """Encode a complex statevector as `[re, im]` pairs."""
    return [[float(np.real(value)), float(np.imag(value))] for value in state]


def _to_evolution_sample(
    sample_index: int,
    phase: Literal["pre_gate", "apply_gate", "settle"],
    t_normalized: float,
    state_hash: str,
    observable: ObservableSnapshot,
    gate_name: str,
    gate_qubits: list[int],
    gate_matrix: NDArray[np.complex128] | None,
) -> StepEvolutionSample:
    """Convert observable and matrix payloads into a contract evolution sample."""
    gate_matrix_payload = None
    if gate_matrix is not None:
        gate_matrix_payload = GateMatrixSample(
            gate_name=gate_name,
            qubits=gate_qubits,
            real=np.real(gate_matrix).tolist(),
            imag=np.imag(gate_matrix).tolist(),
        )

    return StepEvolutionSample(
        sample_index=sample_index,
        phase=phase,
        t_normalized=t_normalized,
        state_hash=state_hash,
        top_k_amplitudes=[
            TopKAmplitude(
                basis=item.basis,
                magnitude=item.magnitude,
                phase=item.phase,
            )
            for item in observable.top_k_amplitudes
        ],
        reduced_density_blocks=[
            ReducedDensityBlock(
                qubits=item.qubits,
                real=item.real,
                imag=item.imag,
            )
            for item in observable.reduced_density_blocks
        ],
        measurement_histogram=[
            MeasurementHistogramEntry(
                outcome=item.outcome,
                probability=item.probability,
                samples=item.samples,
            )
            for item in observable.measurement_histogram
        ],
        gate_matrix=gate_matrix_payload,
    )


def _gate_matrix_qubits(controls: list[int], targets: list[int]) -> list[int]:
    """Resolve gate-matrix qubit ordering from controls and targets."""
    if controls:
        return [*controls, *targets]
    return targets


def _classical_index_for_measurement_bit(gate: GateOp, bit_index: int) -> int:
    """Map a measured bit offset to its classical register index."""
    classical_targets = gate.classical_targets or []
    if bit_index < len(classical_targets):
        return int(classical_targets[bit_index])
    if bit_index < len(gate.targets):
        return int(gate.targets[bit_index])
    return bit_index


def _selected_bits_by_classical_index(gate: GateOp, selected_outcome: str) -> dict[int, int]:
    """Decode selected outcome label into classical-indexed bit assignments."""
    bits: dict[int, int] = {}
    # selected_outcome labels are MSB->LSB while gate targets/classical targets are LSB-first.
    for bit_index, symbol in enumerate(reversed(selected_outcome)):
        if symbol not in {"0", "1"}:
            continue
        bits[_classical_index_for_measurement_bit(gate, bit_index)] = int(symbol)
    return bits


def _encode_aggregated_selected_outcome(bits_by_classical_index: dict[int, int]) -> str:
    """Encode ordered classical bits into one compact little-endian outcome label."""
    if not bits_by_classical_index:
        return ""
    ordered_indices = sorted(bits_by_classical_index.keys())
    value = 0
    for bit_offset, classical_index in enumerate(ordered_indices):
        bit = int(bits_by_classical_index[classical_index]) & 1
        value |= bit << bit_offset
    return format(value, f"0{len(ordered_indices)}b")


def _measurement_outcome_bits_by_classical_index(
    gate: GateOp,
    outcome_index: int,
) -> dict[int, int]:
    """Map a sampled measurement index to classical-indexed bits."""
    bits: dict[int, int] = {}
    for bit_index in range(len(gate.targets)):
        classical_index = _classical_index_for_measurement_bit(gate, bit_index)
        bits[classical_index] = (int(outcome_index) >> bit_index) & 1
    return bits


def _resolved_measurement_classical_targets(gate: GateOp) -> list[int]:
    """Resolve classical targets for every measured qubit position."""
    return [
        _classical_index_for_measurement_bit(gate, bit_index)
        for bit_index in range(len(gate.targets))
    ]


def _resolved_shot_count(req: SimulationRequest) -> int:
    """Resolve replay shot count with safe defaults and lower bound."""
    if req.shot_count is None:
        return DEFAULT_SHOT_REPLAY_COUNT
    return max(1, int(req.shot_count))


def _outcome_index_from_label(label: str, fallback: int) -> int:
    """Parse a binary outcome label, falling back on invalid input."""
    if not label:
        return fallback
    if any(bit not in {"0", "1"} for bit in label):
        return fallback
    try:
        return int(label, 2)
    except ValueError:
        return fallback


def _shot_replay_state_for_outcome(
    *,
    engine: StatevectorEngine,
    extractor: ObservableExtractor,
    source_state: NDArray[np.complex128],
    measured_qubits: list[int],
    outcome_index: int,
    step_index: int,
) -> tuple[str, MeasurementShotReplayState]:
    """Build replay state payload for a sampled measurement outcome branch."""
    collapsed_state = engine._collapse_state(source_state, measured_qubits, int(outcome_index))
    observable = extractor.extract(
        collapsed_state,
        step_index,
        DEFAULT_SCALABILITY_POLICY,
    )
    state_hash = engine.state_hash(collapsed_state)
    replay_state = MeasurementShotReplayState(
        label=format(int(outcome_index), f"0{max(1, len(measured_qubits))}b"),
        state_hash=state_hash,
        top_k_amplitudes=[
            TopKAmplitude(
                basis=item.basis,
                magnitude=item.magnitude,
                phase=item.phase,
            )
            for item in observable.top_k_amplitudes
        ],
        reduced_density_blocks=[
            ReducedDensityBlock(
                qubits=item.qubits,
                real=item.real,
                imag=item.imag,
            )
            for item in observable.reduced_density_blocks
        ],
    )
    return state_hash, replay_state


def _build_measurement_shot_replay(
    *,
    req: SimulationRequest,
    engine: StatevectorEngine,
    extractor: ObservableExtractor,
    snapshot: Any,
) -> MeasurementShotReplay | None:
    """Build deterministic shot-replay payload for one measurement snapshot.

    Args:
        req: Simulation request containing seed and shot count settings.
        engine: Statevector engine used to collapse branch states.
        extractor: Observable extractor for replay-state payloads.
        snapshot: Step snapshot for the measurement event.

    Returns:
        Replay payload for measurement visualization, or `None` when not applicable.
    """
    gate = snapshot.gate
    if gate.kind != "measurement":
        return None
    execution = snapshot.measurement_execution
    if execution is None or not execution.outcomes:
        return None

    measured_qubits = list(gate.targets)
    measured_classical_targets = _resolved_measurement_classical_targets(gate)
    source_state = snapshot.state_before
    step_index = int(snapshot.step_index)
    outcomes_sorted = [
        (str(label), float(probability)) for label, probability in execution.outcomes
    ]
    if not outcomes_sorted:
        return None

    outcome_states_by_label: dict[str, MeasurementShotReplayState] = {}
    outcome_hash_by_label: dict[str, str] = {}
    outcomes_payload: list[MeasurementShotReplayOutcome] = []
    outcome_payload_index_by_label: dict[str, int] = {}

    for fallback_index, (label, probability) in enumerate(outcomes_sorted):
        if label not in outcome_payload_index_by_label:
            outcome_payload_index_by_label[label] = fallback_index
        outcomes_payload.append(
            MeasurementShotReplayOutcome(
                label=label,
                probability=float(np.clip(probability, 0.0, 1.0)),
                state_hash=None,
            )
        )

    probability_vector = np.array(
        [max(0.0, float(item.probability)) for item in outcomes_payload],
        dtype=np.float64,
    )
    total_probability = float(probability_vector.sum())
    if total_probability <= 1e-15:
        probability_vector = np.zeros_like(probability_vector)
        probability_vector[0] = 1.0
    else:
        probability_vector /= total_probability

    shots_total = _resolved_shot_count(req)
    sampling_seed = int(req.seed) ^ SHOT_REPLAY_SEED_MIX
    rng = np.random.default_rng(sampling_seed)
    sampled_indices = rng.choice(
        len(outcomes_payload),
        size=shots_total,
        replace=True,
        p=probability_vector,
    )

    shot_events: list[MeasurementShotReplayEvent] = []
    for shot_index, outcome_payload_index in enumerate(sampled_indices):
        outcome_idx = int(outcome_payload_index)
        outcome_label = outcomes_payload[outcome_idx].label
        state_hash = outcome_hash_by_label.get(outcome_label)
        if state_hash is None:
            outcome_index = _outcome_index_from_label(outcome_label, outcome_idx)
            resolved_hash, replay_state = _shot_replay_state_for_outcome(
                engine=engine,
                extractor=extractor,
                source_state=source_state,
                measured_qubits=measured_qubits,
                outcome_index=outcome_index,
                step_index=step_index,
            )
            replay_state = replay_state.model_copy(update={"label": outcome_label})
            outcome_states_by_label[outcome_label] = replay_state
            outcome_hash_by_label[outcome_label] = resolved_hash
            state_hash = resolved_hash
            payload_index = outcome_payload_index_by_label.get(outcome_label)
            if payload_index is not None:
                outcomes_payload[payload_index] = outcomes_payload[payload_index].model_copy(
                    update={"state_hash": resolved_hash}
                )

        shot_events.append(
            MeasurementShotReplayEvent(
                shot_index=shot_index,
                outcome_label=outcome_label,
                state_hash=state_hash,
            )
        )

    outcome_states = [
        outcome_states_by_label[label]
        for label, _ in outcomes_sorted
        if label in outcome_states_by_label
    ]

    return MeasurementShotReplay(
        source_step_index=step_index,
        measured_qubits=measured_qubits,
        measured_classical_targets=measured_classical_targets,
        shots_total=shots_total,
        sampling_seed=sampling_seed,
        outcomes=outcomes_payload,
        outcome_states=outcome_states,
        shot_events=shot_events,
        timeline=MeasurementShotReplayTimeline(
            camera_pullback_frames=SHOT_REPLAY_CAMERA_PULLBACK_FRAMES,
            histogram_project_frames=SHOT_REPLAY_HISTOGRAM_PROJECT_FRAMES,
            frames_per_shot=SHOT_REPLAY_FRAMES_PER_SHOT,
        ),
    )


def _group_safe_terminal_measurements(ir: QuantumCircuitIR) -> QuantumCircuitIR:
    """Merge trailing independent measurement steps into one grouped measurement gate."""
    steps = ir.steps
    if len(steps) < 2:
        return ir

    trailing_start = len(steps)
    for step_index in range(len(steps) - 1, -1, -1):
        if steps[step_index].kind != "measurement":
            break
        trailing_start = step_index

    trailing_measurements = steps[trailing_start:]
    if len(trailing_measurements) <= 1:
        return ir

    seen_qubits: set[int] = set()
    seen_classical_targets: set[int] = set()
    grouped_targets: list[int] = []
    grouped_classical_targets: list[int] = []

    for gate in trailing_measurements:
        if gate.kind != "measurement":
            return ir

        for qubit in gate.targets:
            qubit_index = int(qubit)
            if qubit_index in seen_qubits:
                return ir
            seen_qubits.add(qubit_index)
            grouped_targets.append(qubit_index)

        for classical_target in _resolved_measurement_classical_targets(gate):
            classical_index = int(classical_target)
            if classical_index in seen_classical_targets:
                return ir
            seen_classical_targets.add(classical_index)
            grouped_classical_targets.append(classical_index)

    if not grouped_targets:
        return ir

    first_gate = trailing_measurements[0]
    grouped_metadata = dict(first_gate.metadata)
    grouped_metadata["terminal_measurement_grouped"] = True
    grouped_metadata["terminal_measurement_group_size"] = len(trailing_measurements)

    grouped_gate = first_gate.model_copy(
        update={
            "targets": grouped_targets,
            "classical_targets": grouped_classical_targets,
            "controls": [],
            "params": [],
            "metadata": grouped_metadata,
        }
    )

    grouped_steps = [*steps[:trailing_start], grouped_gate]
    return ir.model_copy(update={"steps": grouped_steps})


def _matches_selected_bits(
    bits_by_classical_index: dict[int, int],
    selected_bits_by_classical_index: dict[int, int],
) -> bool:
    """Check whether observed classical bits satisfy selected outcome requirements."""
    for classical_index, required_bit in selected_bits_by_classical_index.items():
        observed = bits_by_classical_index.get(classical_index)
        if observed is None or (int(observed) & 1) != (int(required_bit) & 1):
            return False
    return True


def _matches_latest_writer_bits_for_event(
    bits_by_classical_index: dict[int, int],
    selected_bits_by_classical_index: dict[int, int],
    latest_writer_event_by_classical_index: dict[int, int],
    measurement_event_index: int,
) -> bool:
    """Validate required bits only for classical indices written by the current event."""
    for classical_index, required_bit in selected_bits_by_classical_index.items():
        latest_event = latest_writer_event_by_classical_index.get(classical_index)
        if latest_event != measurement_event_index:
            continue
        observed = bits_by_classical_index.get(classical_index)
        if observed is None or (int(observed) & 1) != (int(required_bit) & 1):
            return False
    return True


def _exact_selected_outcome_probability(
    *,
    ir: QuantumCircuitIR,
    selected_bits_by_classical_index: dict[int, int],
    latest_writer_event_by_classical_index: dict[int, int],
    min_branch_probability: float = 1e-15,
) -> float:
    """Compute exact selected-outcome probability via explicit branch enumeration.

    Args:
        ir: Circuit IR to execute with exact branching semantics.
        selected_bits_by_classical_index: Required selected classical bits.
        latest_writer_event_by_classical_index: Last measurement writer index per classical bit.
        min_branch_probability: Pruning threshold for negligible branches.

    Returns:
        Exact probability mass consistent with selected classical-bit constraints.
    """
    required_bits = {
        int(classical_index): int(bit) & 1
        for classical_index, bit in selected_bits_by_classical_index.items()
    }
    if not required_bits:
        return 1.0

    engine = StatevectorEngine()
    branches: list[tuple[NDArray[np.complex128], float, dict[int, int]]] = [
        (engine.initialize_state(ir.qubits), 1.0, {})
    ]
    measurement_event_index = 0

    for gate in ir.steps:
        if not branches:
            return 0.0

        if gate.kind == "unitary":
            next_branches_for_unitary: list[
                tuple[NDArray[np.complex128], float, dict[int, int]]
            ] = []
            for state, branch_probability, bits_by_classical_index in branches:
                next_state = engine.apply_gate(state, gate, ir.qubits)
                next_branches_for_unitary.append(
                    (next_state, branch_probability, bits_by_classical_index)
                )
            branches = next_branches_for_unitary
            continue

        if gate.kind == "measurement":
            next_branches_for_measurement: list[
                tuple[NDArray[np.complex128], float, dict[int, int]]
            ] = []
            for state, branch_probability, bits_by_classical_index in branches:
                outcome_probabilities = engine._measurement_probabilities(state, gate.targets)
                for outcome_index, outcome_probability in enumerate(outcome_probabilities):
                    conditional_probability = float(outcome_probability)
                    if conditional_probability <= min_branch_probability:
                        continue

                    candidate_probability = branch_probability * conditional_probability
                    if candidate_probability <= min_branch_probability:
                        continue

                    collapsed_state = engine._collapse_state(
                        state,
                        gate.targets,
                        int(outcome_index),
                    )
                    next_bits = dict(bits_by_classical_index)
                    next_bits.update(
                        _measurement_outcome_bits_by_classical_index(gate, int(outcome_index))
                    )

                    if not _matches_latest_writer_bits_for_event(
                        next_bits,
                        required_bits,
                        latest_writer_event_by_classical_index,
                        measurement_event_index,
                    ):
                        continue

                    next_branches_for_measurement.append(
                        (collapsed_state, candidate_probability, next_bits)
                    )
            branches = next_branches_for_measurement
            measurement_event_index += 1
            continue

        if gate.kind == "reset":
            next_branches_for_reset: list[tuple[NDArray[np.complex128], float, dict[int, int]]] = []
            for state, branch_probability, bits_by_classical_index in branches:
                reset_branches: list[tuple[NDArray[np.complex128], float]] = [(state, 1.0)]
                for qubit in gate.targets:
                    updated_reset_branches: list[tuple[NDArray[np.complex128], float]] = []
                    for reset_state, reset_probability in reset_branches:
                        outcome_probabilities = engine._measurement_probabilities(
                            reset_state,
                            [qubit],
                        )
                        for outcome_index, outcome_probability in enumerate(outcome_probabilities):
                            conditional_probability = float(outcome_probability)
                            if conditional_probability <= min_branch_probability:
                                continue

                            updated_probability = reset_probability * conditional_probability
                            if updated_probability <= min_branch_probability:
                                continue

                            collapsed_state = engine._collapse_state(
                                reset_state,
                                [qubit],
                                int(outcome_index),
                            )
                            if int(outcome_index) == 1:
                                collapsed_state = engine._apply_x_to_qubit(collapsed_state, qubit)
                            updated_reset_branches.append((collapsed_state, updated_probability))
                    reset_branches = updated_reset_branches
                    if not reset_branches:
                        break

                for reset_state, reset_probability in reset_branches:
                    candidate_probability = branch_probability * reset_probability
                    if candidate_probability <= min_branch_probability:
                        continue
                    next_branches_for_reset.append(
                        (reset_state, candidate_probability, bits_by_classical_index)
                    )
            branches = next_branches_for_reset
            continue

    selected_probability = 0.0
    for _, branch_probability, bits_by_classical_index in branches:
        if _matches_selected_bits(bits_by_classical_index, required_bits):
            selected_probability += branch_probability
    return float(np.clip(selected_probability, 0.0, 1.0))


def simulate_backend_a(
    ir: QuantumCircuitIR,
    req: SimulationRequest,
) -> tuple[SimulationResult, AlgorithmTrace, ValidationReport | None]:
    """Run Backend A simulation and produce contract outputs."""
    normalized_ir = _group_safe_terminal_measurements(ir)
    engine = StatevectorEngine()
    extractor = ObservableExtractor()
    diagnostics: list[Diagnostic] = []
    annotations: list[TraceAnnotation] = []

    simulate_start = time.perf_counter()
    try:
        snapshots = engine.step(normalized_ir, req)
    except UnsupportedGateError as exc:
        diagnostics.append(Diagnostic(code=UNSUPPORTED_GATE, message=str(exc)))
        empty_measurement = build_measurement_model(req.measurement_mode, [])
        empty_trace = AlgorithmTrace(
            contract_version=req.contract_version,
            algorithm_id=req.algorithm_id,
            steps=[],
            annotations=[TraceAnnotation(kind="error", message=str(exc))],
            measurement_model=empty_measurement,
            observable_snapshots=[],
            scalability_policy=DEFAULT_SCALABILITY_POLICY,
            timeline=_build_timeline([], req.target_timeline_step_ms or 800, req.contract_version),
            view_sync_groups=["circuit", "amplitude", "probability"],
        )
        result = SimulationResult(
            contract_version=req.contract_version,
            request_id=req.request_id,
            status="error",
            outputs={},
            observables=[],
            measurement_model=empty_measurement,
            backend_capability=DEFAULT_BACKEND_CAPABILITY,
            diagnostics=diagnostics,
            state_checkpoints=[],
        )
        return result, empty_trace, None

    simulate_ms = (time.perf_counter() - simulate_start) * 1000.0

    observe_start = time.perf_counter()
    trace_steps: list[TraceStep] = []
    observables = []
    checkpoints: list[StateCheckpoint] = []
    selected_measurement_outcome: str | None = None
    measurement_outcomes_override: list[MeasurementOutcome] | None = None
    max_norm_error = 0.0
    parity_unitary_steps: list[GateOp] = []
    parity_state = engine.initialize_state(normalized_ir.qubits)
    non_unitary_seen = False
    unitary_after_non_unitary = False
    collapse_bits_by_classical_index: dict[int, int] = {}
    collapse_latest_writer_event_by_classical_index: dict[int, int] = {}
    collapse_measurement_event_index = 0

    for snapshot in snapshots:
        if snapshot.gate.kind == "unitary":
            if non_unitary_seen:
                unitary_after_non_unitary = True
            else:
                parity_unitary_steps.append(snapshot.gate)
                parity_state = snapshot.state_after.copy()
        else:
            non_unitary_seen = True

        start_hash = engine.state_hash(snapshot.state_before)
        end_hash = engine.state_hash(snapshot.state_after)
        checkpoints.append(StateCheckpoint(step_index=snapshot.step_index, state_hash=end_hash))

        norm = float(np.linalg.norm(snapshot.state_after))
        norm_error = abs(norm - 1.0)
        max_norm_error = max(max_norm_error, norm_error)

        observable = extractor.extract(
            snapshot.state_after,
            snapshot.step_index,
            DEFAULT_SCALABILITY_POLICY,
        )
        observables.append(observable)
        evolution_samples: list[StepEvolutionSample] = []
        gate_matrix_qubits = _gate_matrix_qubits(snapshot.gate.controls, snapshot.gate.targets)

        for evolution_state in snapshot.evolution_states:
            sample_observable = extractor.extract(
                evolution_state.state,
                snapshot.step_index,
                DEFAULT_SCALABILITY_POLICY,
            )
            sample_hash = engine.state_hash(evolution_state.state)
            evolution_samples.append(
                _to_evolution_sample(
                    sample_index=evolution_state.sample_index,
                    phase=evolution_state.phase,
                    t_normalized=evolution_state.t_normalized,
                    state_hash=sample_hash,
                    observable=sample_observable,
                    gate_name=snapshot.gate.name,
                    gate_qubits=gate_matrix_qubits,
                    gate_matrix=evolution_state.gate_matrix,
                )
            )

        if not evolution_samples:
            evolution_samples.append(
                _to_evolution_sample(
                    sample_index=0,
                    phase="settle",
                    t_normalized=1.0,
                    state_hash=end_hash,
                    observable=observable,
                    gate_name=snapshot.gate.name,
                    gate_qubits=gate_matrix_qubits,
                    gate_matrix=None,
                )
            )

        amplitudes = []
        for top in observable.top_k_amplitudes:
            idx = int(top.basis, 2)
            amp = snapshot.state_after[idx]
            amplitudes.append(
                AmplitudeComplex(
                    basis=top.basis,
                    re=float(np.real(amp)),
                    im=float(np.imag(amp)),
                )
            )

        probabilities = [
            BasisProbability(basis=item.outcome, p=item.probability)
            for item in observable.measurement_histogram
        ]

        measurement_info: MeasurementStepInfo | None = None
        if snapshot.gate.kind == "measurement":
            outcome_labels: list[str] | None = None
            execution = snapshot.measurement_execution
            if execution is not None and execution.outcomes:
                outcome_labels = [item[0] for item in execution.outcomes]
                measurement_outcomes_override = [
                    MeasurementOutcome(label=item[0], probability=item[1])
                    for item in execution.outcomes
                ]
                if execution.selected_outcome is not None:
                    selected_measurement_outcome = execution.selected_outcome
                    outcome_labels = [execution.selected_outcome]
                    selected_bits = _selected_bits_by_classical_index(
                        snapshot.gate,
                        execution.selected_outcome,
                    )
                    collapse_bits_by_classical_index.update(selected_bits)

                    event_index = collapse_measurement_event_index
                    collapse_measurement_event_index += 1
                    if selected_bits:
                        for classical_index in selected_bits:
                            collapse_latest_writer_event_by_classical_index[classical_index] = (
                                event_index
                            )
            measurement_info = MeasurementStepInfo(
                is_measurement=True,
                outcome_labels=outcome_labels,
            )

        settle_hash = ""
        for sample in evolution_samples:
            if sample.phase == "settle":
                settle_hash = sample.state_hash
        if not settle_hash:
            settle_hash = evolution_samples[-1].state_hash

        if settle_hash != end_hash:
            diagnostics.append(
                Diagnostic(
                    code=EVOLUTION_SETTLE_HASH_MISMATCH,
                    message=(
                        "Final settle sample hash does not match gate end checkpoint "
                        f"at step {snapshot.step_index}."
                    ),
                )
            )

        trace_steps.append(
            TraceStep(
                step_index=snapshot.step_index,
                operation_id=snapshot.gate.id,
                operation_name=snapshot.gate.name,
                operation_qubits=list(gate_matrix_qubits),
                operation_controls=list(snapshot.gate.controls),
                operation_targets=list(snapshot.gate.targets),
                state_summary=StateSummary(norm=norm, entropy=None),
                amplitudes=amplitudes,
                probabilities=probabilities,
                measurement=measurement_info,
                phase_windows=_phase_windows(),
                boundary_checkpoint=BoundaryCheckpoint(
                    gate_start_hash=start_hash,
                    gate_end_hash=end_hash,
                ),
                transition_hints=TransitionHints(
                    interpolation="ease_in_out",
                    emphasis_targets=None,
                ),
                evolution_samples=evolution_samples,
            )
        )

    observe_ms = (time.perf_counter() - observe_start) * 1000.0

    if unitary_after_non_unitary:
        diagnostics.append(
            Diagnostic(
                code=PARITY_PREFIX_ONLY,
                message=(
                    "Validation parity checks are restricted to the contiguous "
                    "unitary prefix before the first non-unitary operation."
                ),
            )
        )

    tolerance = 1e-9 if req.mode == "validation" else 1e-4
    if max_norm_error > tolerance:
        diagnostics.append(
            Diagnostic(
                code=NUMERICAL_INSTABILITY,
                message=(
                    f"Normalization error {max_norm_error:.3e} exceeded tolerance {tolerance:.1e}."
                ),
            )
        )

    diagnostics.append(
        Diagnostic(
            code="TIMING",
            message=(
                f"simulate_ms={simulate_ms:.3f}; observe_ms={observe_ms:.3f}; "
                f"total_ms={simulate_ms + observe_ms:.3f}"
            ),
        )
    )

    if collapse_bits_by_classical_index:
        aggregated_selected_outcome = _encode_aggregated_selected_outcome(
            collapse_bits_by_classical_index
        )
        aggregated_probability = _exact_selected_outcome_probability(
            ir=normalized_ir,
            selected_bits_by_classical_index=collapse_bits_by_classical_index,
            latest_writer_event_by_classical_index=collapse_latest_writer_event_by_classical_index,
        )

        selected_measurement_outcome = aggregated_selected_outcome
        measurement_outcomes_override = [
            MeasurementOutcome(
                label=aggregated_selected_outcome,
                probability=aggregated_probability,
            )
        ]

    measurement_model = build_measurement_model(
        req.measurement_mode,
        observables,
        outcomes_override=measurement_outcomes_override,
        selected_outcome=selected_measurement_outcome,
    )
    measurement_shot_replay = None
    if snapshots and snapshots[-1].gate.kind == "measurement":
        measurement_shot_replay = _build_measurement_shot_replay(
            req=req,
            engine=engine,
            extractor=extractor,
            snapshot=snapshots[-1],
        )

    timeline = _build_timeline(
        trace_steps,
        req.target_timeline_step_ms or 800,
        req.contract_version,
    )
    trace = AlgorithmTrace(
        contract_version=req.contract_version,
        algorithm_id=req.algorithm_id,
        steps=trace_steps,
        annotations=annotations,
        measurement_model=measurement_model,
        observable_snapshots=observables,
        scalability_policy=DEFAULT_SCALABILITY_POLICY,
        timeline=timeline,
        view_sync_groups=["circuit", "amplitude", "probability"],
        measurement_shot_replay=measurement_shot_replay,
    )

    final_state = (
        snapshots[-1].state_after if snapshots else engine.initialize_state(normalized_ir.qubits)
    )
    result_outputs: dict[str, object] = {
        "final_statevector": _state_vector_output(final_state),
        "num_steps": len(snapshots),
    }

    result = SimulationResult(
        contract_version=req.contract_version,
        request_id=req.request_id,
        status="ok",
        outputs=result_outputs,
        observables=observables,
        measurement_model=measurement_model,
        backend_capability=DEFAULT_BACKEND_CAPABILITY,
        diagnostics=diagnostics,
        state_checkpoints=checkpoints,
    )

    validation_report: ValidationReport | None = None
    if req.mode == "validation":
        parity_reference_ir = ir
        parity_reference_state = final_state
        evidence_ref = "qiskit_reference_statevector"

        if non_unitary_seen:
            parity_reference_ir = ir.model_copy(update={"steps": parity_unitary_steps})
            parity_reference_state = parity_state
            evidence_ref = "qiskit_reference_statevector_unitary_prefix"

        reference = reference_statevector(parity_reference_ir)
        parity = parity_error(parity_reference_state, reference)
        checks = [
            ValidationCheck.model_validate(
                {
                    "name": "normalization_error",
                    "tolerance": tolerance,
                    "measured": max_norm_error,
                    "pass": max_norm_error <= tolerance,
                }
            ),
            ValidationCheck.model_validate(
                {
                    "name": "reference_parity_error",
                    "tolerance": 1e-9,
                    "measured": parity,
                    "pass": parity <= 1e-9,
                }
            ),
        ]
        all_pass = all(check.pass_ for check in checks)
        validation_report = ValidationReport(
            contract_version=req.contract_version,
            request_id=req.request_id,
            checks=checks,
            overall_pass=all_pass,
            evidence_refs=[evidence_ref],
            convention_checks=[
                ConventionCheck.model_validate(
                    {
                        "name": "global_phase_invariance",
                        "pass": True,
                        "details": "State hashing canonicalizes global phase before comparison.",
                    }
                ),
                ConventionCheck.model_validate(
                    {
                        "name": "basis_ordering_consistency",
                        "pass": True,
                        "details": (
                            "Little-endian qubit indexing enforced in importer and simulator."
                        ),
                    }
                ),
            ],
        )

    return result, trace, validation_report
