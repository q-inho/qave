# ruff: noqa: E501
"""Integration tests for algorithm-specific trace payload shape expectations."""

from __future__ import annotations

from pathlib import Path

from qave import ArtifactOptions, SimulationOptions, generate_trace_from_qiskit
from qave.examples import build_ghz, build_qft3


def test_qft3_trace_contains_timeline_and_measurement_replay_payload(tmp_path: Path) -> None:
    """Given QFT3 example circuit, when tracing, then timeline and replay payloads are populated."""
    result = generate_trace_from_qiskit(
        build_qft3(),
        options=SimulationOptions(
            algorithm_id="qft",
            mode="preview",
            measurement_mode="collapse",
            seed=42,
            shot_count=32,
        ),
        artifacts=ArtifactOptions(out_dir=tmp_path, write_result_json=False),
    )

    trace = result.trace
    assert trace.steps
    assert trace.timeline.total_steps >= 1
    assert trace.measurement_model.mode == "collapse"
    assert trace.measurement_model.selected_outcome is not None

    replay = trace.measurement_shot_replay
    assert replay is not None
    assert replay.shots_total == 32
    assert len(replay.shot_events) == 32
    assert replay.timeline.camera_pullback_frames == 36
    assert replay.timeline.histogram_project_frames == 60
    assert replay.timeline.frames_per_shot == 6


def test_ghz3_trace_groups_terminal_measurement_with_correct_gate_matrix_shape(
    tmp_path: Path,
) -> None:
    """Given GHZ3 measured circuit, when tracing, then one grouped measurement step is emitted."""
    result = generate_trace_from_qiskit(
        build_ghz(qubits=3, measure=True),
        options=SimulationOptions(
            algorithm_id="ghz",
            mode="preview",
            measurement_mode="collapse",
            seed=42,
        ),
        artifacts=ArtifactOptions(out_dir=tmp_path, write_result_json=False),
    )

    measurement_steps = [
        step
        for step in result.trace.steps
        if step.measurement is not None and step.measurement.is_measurement
    ]
    assert len(measurement_steps) == 1
    grouped_step = measurement_steps[0]
    assert grouped_step.operation_name == "measure"
    assert grouped_step.operation_targets == [0, 1, 2]

    for sample in grouped_step.evolution_samples:
        assert sample.gate_matrix is not None
        assert sample.gate_matrix.gate_name == "measure"
        assert sample.gate_matrix.qubits == [0, 1, 2]
        assert len(sample.gate_matrix.real) == 8
        assert len(sample.gate_matrix.imag) == 8


def test_ghz5_trace_groups_terminal_measurement_with_correct_gate_matrix_shape(
    tmp_path: Path,
) -> None:
    """Given GHZ5 measured circuit, when tracing, then grouped measurement matrix dimensions are 32x32."""
    result = generate_trace_from_qiskit(
        build_ghz(qubits=5, measure=True),
        options=SimulationOptions(
            algorithm_id="ghz",
            mode="preview",
            measurement_mode="collapse",
            seed=42,
        ),
        artifacts=ArtifactOptions(out_dir=tmp_path, write_result_json=False),
    )

    measurement_steps = [
        step
        for step in result.trace.steps
        if step.measurement is not None and step.measurement.is_measurement
    ]
    assert len(measurement_steps) == 1
    grouped_step = measurement_steps[0]
    assert grouped_step.operation_targets == [0, 1, 2, 3, 4]

    for sample in grouped_step.evolution_samples:
        assert sample.gate_matrix is not None
        assert sample.gate_matrix.gate_name == "measure"
        assert sample.gate_matrix.qubits == [0, 1, 2, 3, 4]
        assert len(sample.gate_matrix.real) == 32
        assert len(sample.gate_matrix.imag) == 32
