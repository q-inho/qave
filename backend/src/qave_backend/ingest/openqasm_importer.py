"""OpenQASM importer."""

from __future__ import annotations

from qiskit import qasm2

from qave_backend.contracts.models import QuantumCircuitIR
from qave_backend.ingest.qiskit_importer import import_qiskit_circuit


def import_openqasm(text: str) -> QuantumCircuitIR:
    """Parse OpenQASM text and convert to project IR."""
    circuit = qasm2.loads(text)
    return import_qiskit_circuit(circuit, source_format="openqasm")
