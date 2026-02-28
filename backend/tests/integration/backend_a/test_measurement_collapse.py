# ruff: noqa: E501
"""Integration tests for collapse-mode measurement semantics in backend A."""

from __future__ import annotations

from qiskit import QuantumCircuit

from qave_backend.contracts.models import GateOp, QuantumCircuitIR, SimulationRequest
from qave_backend.ingest.qiskit_importer import import_qiskit_circuit
from qave_backend.simulator.backend_a import simulate_backend_a


def _request(request_id: str) -> SimulationRequest:
    """Build deterministic preview-mode request fixture for measurement tests."""
    return SimulationRequest(
        contract_version="0.1.0",
        request_id=request_id,
        algorithm_id="bell",
        mode="preview",
        seed=123,
        precision_profile="balanced",
        measurement_mode="collapse",
        animation_profile="teaching_default",
    )


def test_measurement_collapse_sets_selected_outcome_and_projector_matrix() -> None:
    """Given terminal measurement, when simulating collapse mode, then selected outcome labels are emitted."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)
    ir = import_qiskit_circuit(circuit)

    result, trace, _ = simulate_backend_a(ir, _request("measurement_selected"))

    assert result.status == "ok"
    assert trace.measurement_model.mode == "collapse"
    assert trace.measurement_model.selected_outcome is not None

    measurement_steps = [step for step in trace.steps if step.measurement is not None]
    assert measurement_steps
    for step in measurement_steps:
        assert step.measurement is not None
        assert step.measurement.outcome_labels == [trace.measurement_model.selected_outcome]


def test_measurement_collapse_groups_safe_terminal_measurements() -> None:
    """Given independent terminal measurements, when simulating, then backend groups them into one step."""
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.h(1)
    circuit.measure(0, 0)
    circuit.measure(1, 1)
    ir = import_qiskit_circuit(circuit)

    result, trace, _ = simulate_backend_a(ir, _request("measurement_grouped"))

    assert result.status == "ok"
    measurement_steps = [step for step in trace.steps if step.measurement is not None]
    assert len(measurement_steps) == 1

    grouped = measurement_steps[0]
    assert grouped.operation_name == "measure"
    assert grouped.operation_targets == [0, 1]
    assert grouped.operation_qubits == [0, 1]


def test_measurement_collapse_overwrite_uses_latest_classical_writer_probability() -> None:
    """Given overwrite into same classical bit, when simulating, then model probability reflects latest writer."""
    circuit = QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.h(1)
    circuit.measure(0, 0)
    circuit.measure(1, 0)
    ir = import_qiskit_circuit(circuit)

    result, trace, _ = simulate_backend_a(ir, _request("measurement_overwrite_latest"))

    assert result.status == "ok"
    measurement_steps = [step for step in trace.steps if step.measurement is not None]
    assert len(measurement_steps) == 2

    expected = measurement_steps[-1].measurement.outcome_labels[0]  # type: ignore[index,union-attr]
    assert trace.measurement_model.selected_outcome == expected
    assert len(trace.measurement_model.outcomes) == 1
    assert trace.measurement_model.outcomes[0].label == expected
    assert abs(trace.measurement_model.outcomes[0].probability - 0.5) <= 1e-12


def test_measurement_collapse_overwrite_with_correlated_prior_measurement() -> None:
    """Given correlated pre-overwrite measurement, when simulating, then final overwrite probability is 0.5."""
    circuit = QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure(0, 0)
    circuit.measure(1, 0)
    ir = import_qiskit_circuit(circuit)

    result, trace, _ = simulate_backend_a(ir, _request("measurement_overwrite_correlated"))

    assert result.status == "ok"
    assert len(trace.measurement_model.outcomes) == 1
    assert abs(trace.measurement_model.outcomes[0].probability - 0.5) <= 1e-12


def test_measurement_collapse_partial_overwrite_marginalizes_event_probability() -> None:
    """Given partial overwrite across measured bits, when simulating, then final event probability is marginalized."""
    ir = QuantumCircuitIR(
        contract_version="0.1.0",
        circuit_id="partial_overwrite_probability",
        source_format="qiskit_json",
        source_metadata={},
        qubits=3,
        classical_bits=2,
        steps=[
            GateOp(id="op_0_h", kind="unitary", name="h", targets=[0], time_index=0, metadata={}),
            GateOp(id="op_1_h", kind="unitary", name="h", targets=[1], time_index=1, metadata={}),
            GateOp(id="op_2_h", kind="unitary", name="h", targets=[2], time_index=2, metadata={}),
            GateOp(
                id="op_3_measure_pair",
                kind="measurement",
                name="measure",
                targets=[0, 1],
                classical_targets=[0, 1],
                time_index=3,
                metadata={},
            ),
            GateOp(
                id="op_4_measure_overwrite",
                kind="measurement",
                name="measure",
                targets=[2],
                classical_targets=[0],
                time_index=4,
                metadata={},
            ),
        ],
        moments_or_steps_mode="single_gate_steps",
        classical_map=[],
        parameters={},
        metadata={},
    )

    result, trace, _ = simulate_backend_a(ir, _request("measurement_partial_overwrite"))

    assert result.status == "ok"
    assert trace.measurement_model.selected_outcome is not None
    assert len(trace.measurement_model.outcomes) == 1
    assert abs(trace.measurement_model.outcomes[0].probability - 0.25) <= 1e-12
