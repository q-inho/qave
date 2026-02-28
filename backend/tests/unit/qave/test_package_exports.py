"""Tests for qave package exports and compatibility shims."""

from __future__ import annotations

import pytest

import qave


def test_contract_version_exports_match() -> None:
    """Given package exports, when reading contract version, then both paths match."""
    assert qave.CONTRACT_VERSION == "0.1.0"
    assert qave.contract_version() == qave.CONTRACT_VERSION


def test_package_exports_include_core_api_symbols() -> None:
    """Given qave package import, when inspecting exports, then core symbols are available."""
    expected = {
        "SimulationOptions",
        "ArtifactOptions",
        "RenderOptions",
        "generate_trace_from_qiskit",
        "generate_trace_from_openqasm",
        "generate_animation_from_qiskit",
        "generate_animation_from_openqasm",
        "simulate_backend_a",
    }
    assert expected.issubset(set(qave.__all__))


def test_qave_root_does_not_reexport_example_builders() -> None:
    """Given qave root module, when checking attributes, then example builders are not exposed."""
    assert not hasattr(qave, "build_bell")
    assert not hasattr(qave, "build_ghz")
    assert not hasattr(qave, "build_qft3")


def test_deprecated_builtins_builder_emits_warning() -> None:
    """Given deprecated builtins shim, when building Bell circuit, then warning is emitted."""
    import qave.builtins as builtins

    with pytest.warns(DeprecationWarning, match=r"qave\.examples"):
        circuit = builtins.build_bell()

    assert circuit.num_qubits == 2
    assert len(circuit.data) == 2
