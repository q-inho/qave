# ruff: noqa: E501
"""Tests for measurement and reset behavior in the statevector engine."""

from __future__ import annotations

import numpy as np

from qave_backend.contracts.models import GateOp, QuantumCircuitIR, SimulationRequest
from qave_backend.simulator.statevector_engine import StatevectorEngine


def _request(seed: int = 7) -> SimulationRequest:
    """Build deterministic request fixture for measurement/reset tests."""
    return SimulationRequest(
        contract_version="0.1.0",
        request_id="req_measurement",
        algorithm_id="bell",
        params={},
        mode="preview",
        seed=seed,
        precision_profile="balanced",
        measurement_mode="collapse",
        animation_profile="teaching_default",
    )


def _ir_for_steps(steps: list[GateOp], qubits: int, classical_bits: int) -> QuantumCircuitIR:
    """Build deterministic single-step IR for measurement/reset tests."""
    return QuantumCircuitIR(
        contract_version="0.1.0",
        circuit_id="measurement_reset",
        source_format="qiskit_json",
        source_metadata={},
        qubits=qubits,
        classical_bits=classical_bits,
        steps=steps,
        moments_or_steps_mode="single_gate_steps",
        classical_map=[],
        parameters={},
        metadata={},
    )


def test_collapse_measurement_preserves_normalization_and_outcome() -> None:
    """Given measured Hadamard state, when collapsing, then post-state is normalized with selected outcome."""
    ir = _ir_for_steps(
        [
            GateOp(id="g0", kind="unitary", name="h", targets=[0], time_index=0, metadata={}),
            GateOp(
                id="g1",
                kind="measurement",
                name="measure",
                targets=[0],
                classical_targets=[0],
                time_index=1,
                metadata={},
            ),
        ],
        qubits=1,
        classical_bits=1,
    )

    snapshots = StatevectorEngine().step(ir, _request())
    measurement_snapshot = snapshots[-1]
    assert np.isclose(np.linalg.norm(measurement_snapshot.state_after), 1.0, atol=1e-10)
    assert measurement_snapshot.measurement_execution is not None
    assert measurement_snapshot.measurement_execution.selected_outcome is not None


def test_measurement_projector_matrix_uses_matrix_basis_order_for_multitarget() -> None:
    """Given multi-target measurement, when sampling collapse, then projector index matches matrix basis order."""
    ir = _ir_for_steps(
        [
            GateOp(id="g0", kind="unitary", name="x", targets=[0], time_index=0, metadata={}),
            GateOp(
                id="g1",
                kind="measurement",
                name="measure",
                targets=[0, 1],
                classical_targets=[0, 1],
                time_index=1,
                metadata={},
            ),
        ],
        qubits=2,
        classical_bits=2,
    )

    measurement_snapshot = StatevectorEngine().step(ir, _request(seed=7))[-1]
    selected = measurement_snapshot.measurement_execution
    assert selected is not None
    assert selected.selected_outcome is not None

    for sample in measurement_snapshot.evolution_states:
        assert sample.gate_matrix is not None
        assert sample.gate_matrix.shape == (4, 4)
        assert np.isclose(np.trace(sample.gate_matrix), 1.0 + 0.0j)


def test_reset_step_emits_branch_matrix_and_zeroes_target_qubit() -> None:
    """Given reset operation on excited state, when stepping engine, then reset branch matrix is emitted."""
    ir = _ir_for_steps(
        [
            GateOp(id="g0", kind="unitary", name="x", targets=[0], time_index=0, metadata={}),
            GateOp(id="g1", kind="reset", name="reset", targets=[0], time_index=1, metadata={}),
        ],
        qubits=1,
        classical_bits=0,
    )

    snapshots = StatevectorEngine().step(ir, _request(seed=3))
    reset_snapshot = snapshots[-1]
    assert np.allclose(reset_snapshot.state_after, np.array([1.0 + 0.0j, 0.0 + 0.0j]))

    for sample in reset_snapshot.evolution_states:
        assert sample.gate_matrix is not None
        assert sample.gate_matrix.shape == (2, 2)


def test_measurement_probability_helpers_handle_empty_and_zero_norm_states() -> None:
    """Given helper edge cases, when computing probabilities and collapse, then safe defaults are used."""
    state = np.array([0.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128)

    probs_empty = StatevectorEngine._measurement_probabilities(state, [])
    probs_zero = StatevectorEngine._measurement_probabilities(state, [0])
    collapsed_empty = StatevectorEngine._collapse_state(state, [], 0)
    collapsed_zero = StatevectorEngine._collapse_state(state, [0], 1)

    assert np.allclose(probs_empty, np.array([1.0]))
    assert np.allclose(probs_zero, np.array([1.0, 0.0]))
    assert np.allclose(collapsed_empty, state)
    assert np.allclose(collapsed_zero, state)


def test_private_index_and_reset_matrix_helpers_follow_expected_mapping() -> None:
    """Given little-endian outcome and sampled bits, when converting helpers run, then mappings are stable."""
    mapped = StatevectorEngine._little_endian_to_matrix_basis_index(0b10, 2)
    reset_matrix = StatevectorEngine._reset_branch_matrix([1, 0])

    assert mapped == 1
    assert reset_matrix.shape == (4, 4)
    assert np.isclose(np.sum(np.abs(reset_matrix)), 1.0)
