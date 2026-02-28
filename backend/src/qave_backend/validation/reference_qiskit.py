"""Qiskit reference parity utilities."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qave_backend.contracts.models import QuantumCircuitIR


def build_qiskit_circuit_from_ir(ir: QuantumCircuitIR) -> QuantumCircuit:
    """Build qiskit circuit from ir."""
    qc = QuantumCircuit(ir.qubits)

    for gate in ir.steps:
        if gate.kind != "unitary":
            continue

        name = gate.name.lower()
        if name == "x":
            qc.x(gate.targets[0])
        elif name == "y":
            qc.y(gate.targets[0])
        elif name == "z":
            qc.z(gate.targets[0])
        elif name == "h":
            qc.h(gate.targets[0])
        elif name == "s":
            qc.s(gate.targets[0])
        elif name == "t":
            qc.t(gate.targets[0])
        elif name == "rx":
            qc.rx(gate.params[0], gate.targets[0])
        elif name == "ry":
            qc.ry(gate.params[0], gate.targets[0])
        elif name == "rz":
            qc.rz(gate.params[0], gate.targets[0])
        elif name == "cx":
            qc.cx(gate.controls[0], gate.targets[0])
        elif name == "cz":
            qc.cz(gate.controls[0], gate.targets[0])
        elif name == "swap":
            qc.swap(gate.targets[0], gate.targets[1])
        elif name == "cswap":
            qc.cswap(gate.controls[0], gate.targets[0], gate.targets[1])
        elif name in {"ccx", "toffoli"}:
            qc.ccx(gate.controls[0], gate.controls[1], gate.targets[0])
        else:
            msg = f"Unsupported gate for parity reference: {gate.name!r}"
            raise ValueError(msg)

    return qc


def reference_statevector(ir: QuantumCircuitIR) -> NDArray[np.complex128]:
    """Compute the Qiskit reference statevector for an IR circuit."""
    circuit = build_qiskit_circuit_from_ir(ir)
    state = Statevector.from_instruction(circuit).data
    return np.asarray(state, dtype=np.complex128)


def fidelity(lhs: NDArray[np.complex128], rhs: NDArray[np.complex128]) -> float:
    """Fidelity."""
    lhs_norm = np.linalg.norm(lhs)
    rhs_norm = np.linalg.norm(rhs)
    if lhs_norm == 0.0 or rhs_norm == 0.0:
        return 0.0
    overlap = np.vdot(lhs, rhs)
    return float(np.abs(overlap / (lhs_norm * rhs_norm)) ** 2)


def parity_error(lhs: NDArray[np.complex128], rhs: NDArray[np.complex128]) -> float:
    """Parity error."""
    return 1.0 - fidelity(lhs, rhs)
