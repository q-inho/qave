# ruff: noqa: E501
"""Tests for Qiskit circuit and JSON ingestion behavior."""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

from qave_backend.ingest.qiskit_importer import import_qiskit_circuit, import_qiskit_json


def test_import_qiskit_circuit_preserves_instruction_order_and_time_index() -> None:
    """Given three-gate circuit, when importing, then operation order and indices remain deterministic."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rz(0.2, 1)

    ir = import_qiskit_circuit(circuit)
    assert [gate.name for gate in ir.steps] == ["h", "cx", "rz"]
    assert [gate.time_index for gate in ir.steps] == [0, 1, 2]


def test_import_qiskit_circuit_parses_cswap_controls_and_targets() -> None:
    """Given CSWAP instruction, when importing, then control and targets are split correctly."""
    circuit = QuantumCircuit(3)
    circuit.cswap(0, 1, 2)

    ir = import_qiskit_circuit(circuit)
    gate = ir.steps[0]
    assert gate.name == "cswap"
    assert gate.controls == [0]
    assert gate.targets == [1, 2]


def test_import_qiskit_json_rejects_unsupported_payload_shape() -> None:
    """Given unsupported JSON payload, when importing, then ValueError is raised."""
    with pytest.raises(ValueError, match="Unsupported qiskit JSON payload"):
        import_qiskit_json({"unsupported": []})


def test_import_qiskit_circuit_rejects_symbolic_parameters() -> None:
    """Given symbolic circuit parameter, when importing, then ValueError requests binding first."""
    theta = Parameter("theta")
    circuit = QuantumCircuit(1)
    circuit.rz(theta, 0)

    with pytest.raises(ValueError, match="Unsupported symbolic parameter"):
        import_qiskit_circuit(circuit)
