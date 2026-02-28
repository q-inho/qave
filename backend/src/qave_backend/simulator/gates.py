"""Gate definitions and statevector application utilities."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from qave_backend.contracts.models import GateOp


class UnsupportedGateError(ValueError):
    """Raised when a gate is outside Backend A scope."""


I2 = np.eye(2, dtype=np.complex128)
X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
S = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
T = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=np.complex128)
CX = np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ],
    dtype=np.complex128,
)
CZ = np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, -1],
    ],
    dtype=np.complex128,
)
SWAP = np.array(
    [
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
    ],
    dtype=np.complex128,
)
CSWAP = np.array(
    [
        [1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1],
    ],
    dtype=np.complex128,
)
CCX = np.array(
    [
        [1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 1, 0],
    ],
    dtype=np.complex128,
)


def _rx(theta: float) -> NDArray[np.complex128]:
    """Build the single-qubit RX rotation matrix."""
    c = math.cos(theta / 2)
    s = -1j * math.sin(theta / 2)
    return np.array([[c, s], [s, c]], dtype=np.complex128)


def _ry(theta: float) -> NDArray[np.complex128]:
    """Build the single-qubit RY rotation matrix."""
    c = math.cos(theta / 2)
    s = math.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=np.complex128)


def _rz(theta: float) -> NDArray[np.complex128]:
    """Build the single-qubit RZ rotation matrix."""
    return np.array(
        [[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]],
        dtype=np.complex128,
    )


def matrix_for_gate(gate: GateOp) -> tuple[NDArray[np.complex128], list[int]]:
    """Return (unitary_matrix, qubit_order) for a supported gate."""
    name = gate.name.lower()

    if gate.kind != "unitary":
        msg = f"Gate kind {gate.kind!r} is non-unitary in Backend A"
        raise UnsupportedGateError(msg)

    single_gates = {
        "x": X,
        "y": Y,
        "z": Z,
        "h": H,
        "s": S,
        "t": T,
    }

    if name in single_gates:
        if gate.controls:
            msg = f"Controlled variant for {gate.name!r} is unsupported in Backend A"
            raise UnsupportedGateError(msg)
        if len(gate.targets) != 1:
            msg = f"Single-qubit gate {gate.name!r} requires exactly one target"
            raise UnsupportedGateError(msg)
        return single_gates[name], [gate.targets[0]]

    if name in {"rx", "ry", "rz"}:
        if gate.controls:
            msg = f"Controlled rotation {gate.name!r} is unsupported in Backend A"
            raise UnsupportedGateError(msg)
        if len(gate.targets) != 1 or len(gate.params) != 1:
            msg = f"{gate.name!r} requires one target and one parameter"
            raise UnsupportedGateError(msg)
        theta = gate.params[0]
        matrix = {"rx": _rx(theta), "ry": _ry(theta), "rz": _rz(theta)}[name]
        return matrix, [gate.targets[0]]

    if name in {"cx", "cz"}:
        if len(gate.controls) != 1 or len(gate.targets) != 1:
            msg = f"{gate.name!r} requires one control and one target"
            raise UnsupportedGateError(msg)
        matrix = CX if name == "cx" else CZ
        return matrix, [gate.controls[0], gate.targets[0]]

    if name in {"ccx", "toffoli"}:
        if len(gate.controls) != 2 or len(gate.targets) != 1:
            msg = f"{gate.name!r} requires two controls and one target"
            raise UnsupportedGateError(msg)
        return CCX, [gate.controls[0], gate.controls[1], gate.targets[0]]

    if name == "cswap":
        if len(gate.controls) != 1 or len(gate.targets) != 2:
            msg = "cswap requires one control and two targets"
            raise UnsupportedGateError(msg)
        return CSWAP, [gate.controls[0], gate.targets[0], gate.targets[1]]

    if name == "swap":
        if gate.controls:
            msg = "SWAP with controls is unsupported"
            raise UnsupportedGateError(msg)
        if len(gate.targets) != 2:
            msg = "SWAP requires two targets"
            raise UnsupportedGateError(msg)
        return SWAP, [gate.targets[0], gate.targets[1]]

    msg = f"Unsupported gate {gate.name!r}"
    raise UnsupportedGateError(msg)


def fractional_unitary(unitary: NDArray[np.complex128], tau: float) -> NDArray[np.complex128]:
    """Compute a fractional power U^tau using principal-branch eigen phases."""
    if unitary.ndim != 2 or unitary.shape[0] != unitary.shape[1]:
        msg = "fractional_unitary expects a square matrix"
        raise UnsupportedGateError(msg)

    dim = unitary.shape[0]
    tau_clamped = float(np.clip(tau, 0.0, 1.0))

    if np.isclose(tau_clamped, 0.0):
        return np.eye(dim, dtype=np.complex128)
    if np.isclose(tau_clamped, 1.0):
        return unitary.astype(np.complex128, copy=True)

    eigenvalues, eigenvectors = np.linalg.eig(unitary)
    magnitudes = np.abs(eigenvalues)
    safe = np.where(magnitudes > 1e-15, eigenvalues / magnitudes, 1.0 + 0.0j)
    phases = np.angle(safe)
    powered = np.exp(1j * tau_clamped * phases)

    inv = np.linalg.inv(eigenvectors)
    result = eigenvectors @ np.diag(powered) @ inv
    return result.astype(np.complex128)


def apply_unitary(
    state: NDArray[np.complex128],
    unitary: NDArray[np.complex128],
    qubits: list[int],
    num_qubits: int,
) -> NDArray[np.complex128]:
    """Apply a k-qubit unitary using little-endian qubit indexing."""
    if not qubits:
        return state.copy()

    k = len(qubits)
    axes = [num_qubits - 1 - qubit for qubit in qubits]
    if len(set(axes)) != len(axes):
        msg = "Gate qubits must be unique"
        raise UnsupportedGateError(msg)

    tensor = state.reshape((2,) * num_qubits)
    remaining_axes = [axis for axis in range(num_qubits) if axis not in axes]
    permutation = axes + remaining_axes
    inverse_permutation = np.argsort(permutation)

    transposed = np.transpose(tensor, permutation).reshape(2**k, 2 ** (num_qubits - k))
    updated = unitary @ transposed
    restored = np.transpose(updated.reshape((2,) * num_qubits), inverse_permutation)
    return restored.reshape(2**num_qubits)
