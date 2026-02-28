"""Integration tests for basis-ordering and convention checks."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from qave_backend.contracts.models import SimulationRequest
from qave_backend.ingest.qiskit_importer import import_qiskit_circuit
from qave_backend.simulator.backend_a import simulate_backend_a


def _to_complex_vector(encoded: list[list[float]]) -> np.ndarray:
    """Decode `[re, im]` statevector payload rows into complex NumPy vector."""
    return np.array([re + 1j * im for re, im in encoded], dtype=np.complex128)


def test_basis_ordering_is_consistent_with_little_endian_project_convention() -> None:
    """Given X on q0, when simulating, then argmax index is 1 and convention checks pass."""
    circuit = QuantumCircuit(2)
    circuit.x(0)

    ir = import_qiskit_circuit(circuit)
    request = SimulationRequest(
        contract_version="0.1.0",
        request_id="basis_ordering",
        algorithm_id="bell",
        mode="validation",
        seed=1,
        precision_profile="strict",
        measurement_mode="collapse",
        animation_profile="teaching_default",
    )

    result, _, report = simulate_backend_a(ir, request)
    state = _to_complex_vector(result.outputs["final_statevector"])

    assert int(np.argmax(np.abs(state) ** 2)) == 1
    assert report is not None
    assert all(check.pass_ for check in report.convention_checks)
