"""Tests for qave example-circuit builders."""

from __future__ import annotations

from qave.examples import build_bell, build_ghz, build_qft3


def test_build_bell_emits_expected_gate_sequence() -> None:
    """Given Bell builder, when constructing circuit, then the gate order matches expectation."""
    circuit = build_bell()
    assert circuit.num_qubits == 2
    assert [item.operation.name for item in circuit.data] == ["h", "cx"]


def test_build_ghz_without_measurement_has_no_clbits() -> None:
    """Given GHZ builder without measurement, when constructing, then no measure ops are present."""
    circuit = build_ghz(4, measure=False)
    assert circuit.num_qubits == 4
    assert circuit.num_clbits == 0
    assert all(item.operation.name != "measure" for item in circuit.data)


def test_build_qft3_contains_measurement_operations() -> None:
    """Given QFT3 builder, when constructing, then circuit includes terminal measurement."""
    circuit = build_qft3()
    assert circuit.num_qubits == 3
    assert any(item.operation.name == "measure" for item in circuit.data)
