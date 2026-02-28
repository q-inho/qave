# ruff: noqa: E501
"""Tests for unitary-only behavior in the statevector engine."""

from __future__ import annotations

from typing import Literal

import numpy as np

from qave_backend.contracts.models import GateOp, QuantumCircuitIR, SimulationRequest
from qave_backend.simulator.gates import matrix_for_gate
from qave_backend.simulator.statevector_engine import StatevectorEngine


def _request(
    animation_profile: Literal["teaching_default", "analysis_slow", "presentation_fast"] = (
        "teaching_default"
    ),
) -> SimulationRequest:
    """Build deterministic request fixture for statevector unitary tests."""
    return SimulationRequest(
        contract_version="0.1.0",
        request_id="req_engine",
        algorithm_id="bell",
        params={},
        mode="validation",
        seed=7,
        precision_profile="strict",
        measurement_mode="collapse",
        animation_profile=animation_profile,
    )


def _unitary_ir(steps: list[GateOp], qubits: int) -> QuantumCircuitIR:
    """Build single-gate-step IR fixture for statevector tests."""
    return QuantumCircuitIR(
        contract_version="0.1.0",
        circuit_id="unitary_test",
        source_format="qiskit_json",
        source_metadata={},
        qubits=qubits,
        classical_bits=0,
        steps=steps,
        moments_or_steps_mode="single_gate_steps",
        classical_map=[],
        parameters={},
        metadata={},
    )


def test_unitary_steps_preserve_norm() -> None:
    """Given sequence of unitary gates, when stepping engine, then every state remains normalized."""
    ir = _unitary_ir(
        [
            GateOp(id="g0", kind="unitary", name="h", targets=[0], time_index=0, metadata={}),
            GateOp(
                id="g1",
                kind="unitary",
                name="rz",
                targets=[1],
                params=[0.75],
                time_index=1,
                metadata={},
            ),
            GateOp(
                id="g2",
                kind="unitary",
                name="cx",
                targets=[1],
                controls=[0],
                time_index=2,
                metadata={},
            ),
        ],
        qubits=2,
    )

    snapshots = StatevectorEngine().step(ir, _request())
    assert snapshots
    for snapshot in snapshots:
        assert np.isclose(np.linalg.norm(snapshot.state_after), 1.0)


def test_state_hash_is_global_phase_invariant() -> None:
    """Given globally phase-shifted statevectors, when hashing, then hashes are identical."""
    engine = StatevectorEngine()
    state = np.array([1 / np.sqrt(2), 1j / np.sqrt(2)], dtype=np.complex128)
    phased = state * np.exp(1j * np.pi / 3)
    assert engine.state_hash(state) == engine.state_hash(phased)


def test_state_hash_is_signed_zero_invariant() -> None:
    """Given signed-zero-equivalent statevectors, when hashing, then hashes are identical."""
    engine = StatevectorEngine()
    positive_zero_state = np.array(
        [complex(0.0, 0.0), complex(1 / np.sqrt(2), 0.0), complex(0.0, 1 / np.sqrt(2))],
        dtype=np.complex128,
    )
    negative_zero_state = np.array(
        [complex(0.0, -0.0), complex(1 / np.sqrt(2), 0.0), complex(0.0, 1 / np.sqrt(2))],
        dtype=np.complex128,
    )

    assert np.array_equal(positive_zero_state, negative_zero_state)
    assert engine.state_hash(positive_zero_state) == engine.state_hash(negative_zero_state)


def test_evolution_samples_follow_phase_order_and_endpoint_matrices() -> None:
    """Given single-H circuit, when emitting evolution samples, then phase ordering and endpoints are exact."""
    ir = _unitary_ir(
        [GateOp(id="g0", kind="unitary", name="h", targets=[0], time_index=0, metadata={})],
        qubits=1,
    )

    snapshot = StatevectorEngine().step(ir, _request())[0]
    phases = [sample.phase for sample in snapshot.evolution_states]

    pre_idx = [idx for idx, phase in enumerate(phases) if phase == "pre_gate"]
    apply_idx = [idx for idx, phase in enumerate(phases) if phase == "apply_gate"]
    settle_idx = [idx for idx, phase in enumerate(phases) if phase == "settle"]

    assert pre_idx and apply_idx and settle_idx
    assert max(pre_idx) < min(apply_idx)
    assert max(apply_idx) < min(settle_idx)

    for sample in snapshot.evolution_states:
        assert np.isclose(np.linalg.norm(sample.state), 1.0, atol=1e-10)
        assert sample.gate_matrix is not None

    expected_matrix, _ = matrix_for_gate(ir.steps[0])
    first_gate_matrix = snapshot.evolution_states[0].gate_matrix
    final_gate_matrix = snapshot.evolution_states[-1].gate_matrix
    assert first_gate_matrix is not None
    assert final_gate_matrix is not None
    assert np.allclose(first_gate_matrix, np.eye(2, dtype=np.complex128))
    assert np.allclose(final_gate_matrix, expected_matrix)


def test_gate_matrix_samples_match_gate_arity() -> None:
    """Given two-qubit controlled gate, when sampling evolution, then gate matrix dimensions match arity."""
    ir = _unitary_ir(
        [
            GateOp(
                id="g0",
                kind="unitary",
                name="cx",
                targets=[1],
                controls=[0],
                time_index=0,
                metadata={},
            )
        ],
        qubits=2,
    )

    snapshot = StatevectorEngine().step(ir, _request())[0]
    for sample in snapshot.evolution_states:
        assert sample.gate_matrix is not None
        assert sample.gate_matrix.shape == (4, 4)


def test_animation_profile_controls_substep_density() -> None:
    """Given different animation profiles, when stepping, then sample density follows slow > default > fast."""
    ir = _unitary_ir(
        [GateOp(id="g0", kind="unitary", name="h", targets=[0], time_index=0, metadata={})],
        qubits=1,
    )

    engine = StatevectorEngine()
    teaching = engine.step(ir, _request("teaching_default"))[0].evolution_states
    slow = engine.step(ir, _request("analysis_slow"))[0].evolution_states
    fast = engine.step(ir, _request("presentation_fast"))[0].evolution_states

    assert len(slow) > len(teaching) > len(fast)
