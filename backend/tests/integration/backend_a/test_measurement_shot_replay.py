# ruff: noqa: E501
"""Integration tests for deterministic measurement-shot replay payloads."""

from __future__ import annotations

from qiskit import QuantumCircuit

from qave_backend.contracts.models import SimulationRequest
from qave_backend.ingest.qiskit_importer import import_qiskit_circuit
from qave_backend.simulator.backend_a import simulate_backend_a


def _request(request_id: str, seed: int, shot_count: int) -> SimulationRequest:
    """Build deterministic request fixture for shot-replay checks."""
    return SimulationRequest(
        contract_version="0.1.0",
        request_id=request_id,
        algorithm_id="bell",
        mode="preview",
        seed=seed,
        precision_profile="balanced",
        measurement_mode="collapse",
        animation_profile="teaching_default",
        shot_count=shot_count,
    )


def test_shot_replay_is_emitted_for_terminal_measurement() -> None:
    """Given terminal two-qubit measurement, when simulating, then shot replay payload is emitted."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    ir = import_qiskit_circuit(circuit)

    result, trace, _ = simulate_backend_a(ir, _request("shot_replay", seed=11, shot_count=12))

    assert result.status == "ok"
    assert trace.measurement_shot_replay is not None
    replay = trace.measurement_shot_replay
    assert replay.source_step_index == len(trace.steps) - 1
    assert replay.measured_qubits == [0, 1]
    assert replay.shots_total == 12
    assert len(replay.shot_events) == 12
    assert len(replay.outcomes) == 4


def test_shot_replay_is_absent_without_terminal_measurement() -> None:
    """Given unitary-only circuit, when simulating, then measurement shot replay is omitted."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    ir = import_qiskit_circuit(circuit)

    result, trace, _ = simulate_backend_a(ir, _request("shot_replay_absent", seed=5, shot_count=8))
    assert result.status == "ok"
    assert trace.measurement_shot_replay is None


def test_shot_replay_is_seed_deterministic() -> None:
    """Given fixed seed and request, when simulating twice, then replay events are identical."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    ir = import_qiskit_circuit(circuit)

    request = _request("shot_replay_deterministic", seed=21, shot_count=20)
    _, trace_a, _ = simulate_backend_a(ir, request)
    _, trace_b, _ = simulate_backend_a(ir, request)

    assert trace_a.measurement_shot_replay is not None
    assert trace_b.measurement_shot_replay is not None
    assert [event.outcome_label for event in trace_a.measurement_shot_replay.shot_events] == [
        event.outcome_label for event in trace_b.measurement_shot_replay.shot_events
    ]
    assert [event.state_hash for event in trace_a.measurement_shot_replay.shot_events] == [
        event.state_hash for event in trace_b.measurement_shot_replay.shot_events
    ]


def test_shot_replay_materializes_only_sampled_outcomes() -> None:
    """Given one-shot sampling over many outcomes, when simulating, then only sampled outcome state is materialized."""
    circuit = QuantumCircuit(4, 4)
    for qubit in range(4):
        circuit.h(qubit)
    circuit.measure([0, 1, 2, 3], [0, 1, 2, 3])
    ir = import_qiskit_circuit(circuit)

    result, trace, _ = simulate_backend_a(
        ir, _request("shot_replay_sampled_only", seed=31, shot_count=1)
    )

    assert result.status == "ok"
    assert trace.measurement_shot_replay is not None
    replay = trace.measurement_shot_replay
    assert len(replay.outcomes) == 16
    assert len(replay.shot_events) == 1
    assert len(replay.outcome_states) == 1
    assert replay.outcome_states[0].state_hash == replay.shot_events[0].state_hash
    assert replay.outcome_states[0].label == replay.shot_events[0].outcome_label
