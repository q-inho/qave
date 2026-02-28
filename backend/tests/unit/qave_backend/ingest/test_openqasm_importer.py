"""Tests for OpenQASM ingestion into project IR."""

from __future__ import annotations

import pytest
from qiskit.qasm2.exceptions import QASM2ParseError

from qave_backend.ingest.openqasm_importer import import_openqasm


def test_import_openqasm_builds_bell_ir() -> None:
    """Given Bell OpenQASM text, when importing, then ordered IR operations are preserved."""
    qasm = """
    OPENQASM 2.0;
    include \"qelib1.inc\";
    qreg q[2];
    h q[0];
    cx q[0],q[1];
    """

    ir = import_openqasm(qasm)
    assert ir.source_format == "openqasm"
    assert ir.qubits == 2
    assert [step.name for step in ir.steps] == ["h", "cx"]


def test_import_openqasm_rejects_invalid_payload() -> None:
    """Given malformed OpenQASM text, when importing, then parser raises an exception."""
    with pytest.raises(QASM2ParseError):
        import_openqasm("OPENQASM bad payload")
