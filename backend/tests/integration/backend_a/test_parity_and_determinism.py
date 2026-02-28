# ruff: noqa: E501
"""Integration tests for backend parity and deterministic replay behavior."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from qave_backend.contracts.models import SimulationRequest
from qave_backend.ingest.qiskit_importer import import_qiskit_circuit
from qave_backend.simulator.backend_a import simulate_backend_a


def _request(request_id: str, algorithm_id: str, mode: str = "validation") -> SimulationRequest:
    """Build deterministic simulation request fixture for backend integration tests."""
    return SimulationRequest(
        contract_version="0.1.0",
        request_id=request_id,
        algorithm_id=algorithm_id,  # type: ignore[arg-type]
        mode=mode,  # type: ignore[arg-type]
        seed=42,
        precision_profile="strict" if mode == "validation" else "balanced",
        measurement_mode="collapse",
        animation_profile="teaching_default",
    )


def _qft2_decomposed() -> QuantumCircuit:
    """Build decomposition-compatible 2-qubit QFT circuit fixture."""
    qc = QuantumCircuit(2)
    qc.h(1)

    lam = np.pi / 2
    qc.rz(lam / 2, 1)
    qc.cx(1, 0)
    qc.rz(-lam / 2, 0)
    qc.cx(1, 0)
    qc.rz(lam / 2, 0)

    qc.h(0)
    qc.swap(0, 1)
    return qc


def test_backend_a_parity_for_bell_ghz_and_qft() -> None:
    """Given canonical circuits, when simulating backend A, then parity and normalization checks pass."""
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)

    ghz = QuantumCircuit(3)
    ghz.h(0)
    ghz.cx(0, 1)
    ghz.cx(0, 2)

    cases = [
        ("bell", bell),
        ("ghz", ghz),
        ("qft", _qft2_decomposed()),
    ]

    for idx, (algorithm_id, circuit) in enumerate(cases):
        ir = import_qiskit_circuit(circuit)
        result, trace, report = simulate_backend_a(ir, _request(f"req_{idx}", algorithm_id))
        expected_dim = 2**ir.qubits

        assert result.status == "ok"
        assert set(result.outputs) == {"final_statevector", "num_steps"}
        assert report is not None
        checks = {item.name: item for item in report.checks}
        assert checks["reference_parity_error"].pass_
        assert checks["normalization_error"].pass_
        assert len(trace.steps) == len(ir.steps)

        for step in trace.steps:
            assert step.evolution_samples
            settle_hash = ""
            for sample in step.evolution_samples:
                assert sample.gate_matrix is not None
                assert len(sample.gate_matrix.real) == len(sample.gate_matrix.imag)
                assert len(sample.reduced_density_blocks) == 1
                density = sample.reduced_density_blocks[0]
                assert density.qubits == list(range(ir.qubits))
                assert len(density.real) == expected_dim
                assert len(density.imag) == expected_dim
                if sample.phase == "settle":
                    settle_hash = sample.state_hash
            assert settle_hash == step.boundary_checkpoint.gate_end_hash


def test_backend_a_replay_is_seed_deterministic() -> None:
    """Given identical request and seed, when simulating twice, then checkpoint and sample hashes match."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rz(0.33, 1)
    ir = import_qiskit_circuit(circuit)

    request = _request("deterministic", "bell", mode="preview")
    result_a, trace_a, _ = simulate_backend_a(ir, request)
    result_b, trace_b, _ = simulate_backend_a(ir, request)

    assert [item.state_hash for item in result_a.state_checkpoints] == [
        item.state_hash for item in result_b.state_checkpoints
    ]
    assert [step.boundary_checkpoint.gate_end_hash for step in trace_a.steps] == [
        step.boundary_checkpoint.gate_end_hash for step in trace_b.steps
    ]
    assert [[sample.state_hash for sample in step.evolution_samples] for step in trace_a.steps] == [
        [sample.state_hash for sample in step.evolution_samples] for step in trace_b.steps
    ]
