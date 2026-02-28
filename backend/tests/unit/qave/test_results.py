# ruff: noqa: E501
"""Tests for qave result dataclasses and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from qiskit import QuantumCircuit

from qave import (
    ArtifactOptions,
    InputValidationError,
    SimulationOptions,
    generate_trace_from_qiskit,
)


def test_require_measurement_shot_replay_raises_without_terminal_measurement(
    tmp_path: Path,
) -> None:
    """Given unitary-only circuit, when requiring shot replay, then InputValidationError is raised."""
    circuit = QuantumCircuit(1)
    circuit.h(0)

    result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="custom", shot_count=10, seed=7),
        artifacts=ArtifactOptions(out_dir=tmp_path),
    )

    with pytest.raises(InputValidationError, match="measurement_shot_replay"):
        result.require_measurement_shot_replay()


def test_require_measurement_shot_replay_returns_payload_for_terminal_measurement(
    tmp_path: Path,
) -> None:
    """Given terminal measurement circuit, when requiring shot replay, then payload is returned."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.measure(0, 0)
    shot_count = 10

    result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="custom", shot_count=shot_count, seed=7),
        artifacts=ArtifactOptions(out_dir=tmp_path),
    )

    replay = result.require_measurement_shot_replay()
    assert replay.shots_total == shot_count
    assert len(replay.shot_events) == shot_count
