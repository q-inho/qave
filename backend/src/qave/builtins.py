"""Legacy circuit helper module.

`qave` is ingestion-first: callers should pass Qiskit circuits or OpenQASM source into
`qave.generate_trace_*` / `qave.generate_animation_*`.

Example/demo circuits live under `qave.examples`. This module remains as a thin alias for
historical internal references.
"""

from __future__ import annotations

import warnings

from qiskit import QuantumCircuit

import qave.examples as examples


def _warn_deprecated(symbol_name: str) -> None:
    """Emit a deprecation warning for legacy `qave.builtins` symbols."""
    warnings.warn(
        (
            f"`qave.builtins.{symbol_name}` is deprecated and will be removed in a future "
            "release. Use `qave.examples` instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )


def build_bell() -> QuantumCircuit:
    """Build a Bell circuit through the deprecated builtins shim."""
    _warn_deprecated("build_bell")
    return examples.build_bell()


def build_ghz(qubits: int = 3, measure: bool = True) -> QuantumCircuit:
    """Build a GHZ circuit through the deprecated builtins shim."""
    _warn_deprecated("build_ghz")
    return examples.build_ghz(qubits=qubits, measure=measure)


def build_qft3() -> QuantumCircuit:
    """Build a QFT-3 demo circuit through the deprecated builtins shim."""
    _warn_deprecated("build_qft3")
    return examples.build_qft3()


__all__ = ["build_bell", "build_ghz", "build_qft3"]
