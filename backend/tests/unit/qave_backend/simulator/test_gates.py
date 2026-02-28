# ruff: noqa: E501
"""Tests for gate-matrix construction and low-level gate utilities."""

from __future__ import annotations

import numpy as np
import pytest

from qave_backend.contracts.models import GateOp
from qave_backend.simulator.gates import (
    UnsupportedGateError,
    apply_unitary,
    fractional_unitary,
    matrix_for_gate,
)


def _gate(
    name: str,
    targets: list[int],
    controls: list[int] | None = None,
    params: list[float] | None = None,
) -> GateOp:
    """Build unitary GateOp fixture for gate-level tests."""
    return GateOp(
        id=f"g_{name}",
        kind="unitary",
        name=name,
        targets=targets,
        controls=controls or [],
        params=params or [],
        time_index=0,
        metadata={},
    )


def test_matrix_for_gate_supports_core_single_and_controlled_gates() -> None:
    """Given supported gate names, when requesting matrices, then dimensions and qubits are correct."""
    cases = [
        (_gate("x", [0]), 2, [0]),
        (_gate("h", [1]), 2, [1]),
        (_gate("rx", [1], params=[0.3]), 2, [1]),
        (_gate("cx", [1], controls=[0]), 4, [0, 1]),
        (_gate("cz", [1], controls=[0]), 4, [0, 1]),
        (_gate("swap", [0, 1]), 4, [0, 1]),
        (_gate("cswap", [1, 2], controls=[0]), 8, [0, 1, 2]),
        (_gate("ccx", [2], controls=[0, 1]), 8, [0, 1, 2]),
        (_gate("toffoli", [2], controls=[0, 1]), 8, [0, 1, 2]),
    ]

    for gate, dim, qubits in cases:
        matrix, gate_qubits = matrix_for_gate(gate)
        assert matrix.shape == (dim, dim)
        assert gate_qubits == qubits


@pytest.mark.parametrize(
    "gate",
    [
        _gate("h", [0], controls=[1]),
        _gate("h", [0, 1]),
        _gate("rx", [0], controls=[1], params=[0.5]),
        _gate("rx", [0], params=[]),
        _gate("cx", [1], controls=[]),
        _gate("ccx", [2], controls=[0]),
        _gate("cswap", [1], controls=[0]),
        _gate("swap", [0], controls=[]),
        _gate("unknown", [0]),
    ],
)
def test_matrix_for_gate_rejects_invalid_gate_shapes(gate: GateOp) -> None:
    """Given unsupported gate signature, when requesting matrix, then UnsupportedGateError is raised."""
    with pytest.raises(UnsupportedGateError):
        matrix_for_gate(gate)


def test_fractional_unitary_endpoints_match_identity_and_full_unitary() -> None:
    """Given supported unitary matrix, when tau is 0 or 1, then endpoint behavior is exact."""
    matrix, _ = matrix_for_gate(_gate("h", [0]))
    assert np.allclose(fractional_unitary(matrix, 0.0), np.eye(2, dtype=np.complex128))
    assert np.allclose(fractional_unitary(matrix, 1.0), matrix)


def test_fractional_unitary_requires_square_matrix() -> None:
    """Given non-square matrix, when computing fractional power, then UnsupportedGateError is raised."""
    with pytest.raises(UnsupportedGateError, match="square matrix"):
        fractional_unitary(np.ones((2, 3), dtype=np.complex128), 0.5)


def test_apply_unitary_rejects_duplicate_qubits() -> None:
    """Given duplicate qubit indices, when applying unitary, then UnsupportedGateError is raised."""
    state = np.array([1.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128)
    with pytest.raises(UnsupportedGateError, match="unique"):
        apply_unitary(state, np.eye(2, dtype=np.complex128), [0, 0], 1)
