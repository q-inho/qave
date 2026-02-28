"""Example quantum circuits for demos and documentation.

These helpers are intentionally **not** re-exported from the top-level `qave` package.
The API should remain ingestion-first (Qiskit/OpenQASM in -> trace/animation out),
while example circuits live under `qave.examples`.
"""

from __future__ import annotations

import math

from qiskit import QuantumCircuit


def build_bell() -> QuantumCircuit:
    """Build a 2-qubit Bell-state preparation circuit."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    return circuit


def build_ghz(qubits: int = 3, measure: bool = True) -> QuantumCircuit:
    """Build an n-qubit GHZ circuit with optional terminal measurements."""
    if qubits < 2:
        msg = "GHZ circuit requires at least 2 qubits"
        raise ValueError(msg)

    circuit = QuantumCircuit(qubits, qubits if measure else 0)
    circuit.h(0)
    for target in range(1, qubits):
        circuit.cx(0, target)
    if measure:
        circuit.measure(range(qubits), range(qubits))
    return circuit


def _append_controlled_phase_decomposed(
    circuit: QuantumCircuit,
    control: int,
    target: int,
    lam: float,
) -> None:
    """Append a controlled-phase decomposition using only RZ and CX gates."""
    circuit.rz(lam / 2.0, control)
    circuit.cx(control, target)
    circuit.rz(-lam / 2.0, target)
    circuit.cx(control, target)
    circuit.rz(lam / 2.0, target)


def _append_qft_decomposed(circuit: QuantumCircuit, qubits: list[int]) -> None:
    """Append a decomposition-compatible QFT on the provided qubit ordering."""
    total_qubits = len(qubits)
    for target_offset in range(total_qubits):
        target = qubits[total_qubits - 1 - target_offset]
        circuit.h(target)
        for control_offset in range(target_offset + 1, total_qubits):
            control = qubits[total_qubits - 1 - control_offset]
            angle = math.pi / float(2 ** (control_offset - target_offset))
            _append_controlled_phase_decomposed(circuit, control, target, angle)

    for idx in range(total_qubits // 2):
        circuit.swap(qubits[idx], qubits[total_qubits - idx - 1])


def _append_inverse_qft_decomposed(circuit: QuantumCircuit, qubits: list[int]) -> None:
    """Append the inverse of the decomposition-compatible QFT helper."""
    total_qubits = len(qubits)
    for idx in range(total_qubits // 2):
        circuit.swap(qubits[idx], qubits[total_qubits - idx - 1])

    for target_offset, target in enumerate(qubits):
        for control_offset in range(target_offset):
            control = qubits[control_offset]
            angle = -math.pi / float(2 ** (target_offset - control_offset))
            _append_controlled_phase_decomposed(circuit, control, target, angle)
        circuit.h(target)


def build_qft3() -> QuantumCircuit:
    """Build the project's canonical 3-qubit QFT sandwich demo circuit."""
    circuit = QuantumCircuit(3, 3)
    for qubit in range(3):
        circuit.h(qubit)

    phase_prep_angles = [0.17, -0.33, 0.71]
    for qubit, angle in enumerate(phase_prep_angles):
        circuit.rz(angle, qubit)

    logical_qubits = list(range(3))
    _append_qft_decomposed(circuit, logical_qubits)

    _append_controlled_phase_decomposed(circuit, control=0, target=2, lam=math.pi / 3.0)
    _append_controlled_phase_decomposed(circuit, control=1, target=2, lam=-math.pi / 5.0)
    _append_controlled_phase_decomposed(circuit, control=0, target=1, lam=math.pi / 7.0)

    _append_inverse_qft_decomposed(circuit, logical_qubits)
    circuit.measure(range(3), range(3))
    return circuit
