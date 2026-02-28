# ruff: noqa: E501
"""Tests for qiskit reference parity helper utilities."""

from __future__ import annotations

import numpy as np
import pytest

from qave_backend.contracts.models import GateOp, QuantumCircuitIR
from qave_backend.validation.reference_qiskit import (
    build_qiskit_circuit_from_ir,
    fidelity,
    parity_error,
    reference_statevector,
)


def _ir(steps: list[GateOp], qubits: int) -> QuantumCircuitIR:
    """Build deterministic IR fixture for reference-parity tests."""
    return QuantumCircuitIR(
        contract_version="0.1.0",
        circuit_id="ref_ir",
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


def test_build_qiskit_circuit_from_ir_maps_supported_gates() -> None:
    """Given supported IR gates, when rebuilding Qiskit circuit, then operation names are preserved."""
    ir = _ir(
        [
            GateOp(id="g0", kind="unitary", name="h", targets=[0], time_index=0, metadata={}),
            GateOp(
                id="g1",
                kind="unitary",
                name="cx",
                controls=[0],
                targets=[1],
                time_index=1,
                metadata={},
            ),
            GateOp(id="g2", kind="unitary", name="swap", targets=[0, 1], time_index=2, metadata={}),
        ],
        qubits=2,
    )

    circuit = build_qiskit_circuit_from_ir(ir)
    assert [instruction.operation.name for instruction in circuit.data] == ["h", "cx", "swap"]


def test_build_qiskit_circuit_from_ir_rejects_unsupported_gate() -> None:
    """Given unsupported gate name, when rebuilding Qiskit circuit, then ValueError is raised."""
    ir = _ir(
        [GateOp(id="g0", kind="unitary", name="u", targets=[0], time_index=0, metadata={})],
        qubits=1,
    )

    with pytest.raises(ValueError, match="Unsupported gate"):
        build_qiskit_circuit_from_ir(ir)


def test_reference_statevector_matches_expected_dimension() -> None:
    """Given two-qubit Bell IR, when computing reference statevector, then output dimension is 2**qubits."""
    ir = _ir(
        [
            GateOp(id="g0", kind="unitary", name="h", targets=[0], time_index=0, metadata={}),
            GateOp(
                id="g1",
                kind="unitary",
                name="cx",
                controls=[0],
                targets=[1],
                time_index=1,
                metadata={},
            ),
        ],
        qubits=2,
    )

    state = reference_statevector(ir)
    assert state.shape == (4,)
    assert np.isclose(np.linalg.norm(state), 1.0)


def test_fidelity_and_parity_error_cover_edge_cases() -> None:
    """Given equivalent and zero-norm vectors, when computing parity metrics, then edge behaviors are correct."""
    lhs = np.array([1.0 + 0.0j, 0.0 + 0.0j])
    rhs = np.array([1.0 + 0.0j, 0.0 + 0.0j])
    zero = np.array([0.0 + 0.0j, 0.0 + 0.0j])

    assert np.isclose(fidelity(lhs, rhs), 1.0)
    assert np.isclose(parity_error(lhs, rhs), 0.0)
    assert np.isclose(fidelity(lhs, zero), 0.0)
    assert np.isclose(parity_error(lhs, zero), 1.0)
