# ruff: noqa: E501
"""Tests for measurement model construction helpers."""

from __future__ import annotations

import pytest

from qave_backend.contracts.models import (
    EntanglementMetrics,
    MeasurementHistogramEntry,
    MeasurementOutcome,
    ObservableSnapshot,
)
from qave_backend.measurement.model import build_measurement_model


def _snapshot_with_histogram() -> ObservableSnapshot:
    """Build observable snapshot fixture with measurement histogram entries."""
    return ObservableSnapshot(
        snapshot_id="s0",
        step_index=0,
        bloch_vectors=[],
        purity_entropy=[],
        top_k_amplitudes=[],
        reduced_density_blocks=[],
        entanglement_metrics=EntanglementMetrics(),
        measurement_histogram=[
            MeasurementHistogramEntry(outcome="0", probability=0.25),
            MeasurementHistogramEntry(outcome="1", probability=0.75),
        ],
    )


def test_build_measurement_model_uses_selected_outcome_override() -> None:
    """Given explicit selected outcome override, when building model, then override is preserved."""
    model = build_measurement_model(
        mode="collapse",
        snapshots=[],
        outcomes_override=[
            MeasurementOutcome(label="0", probability=0.4),
            MeasurementOutcome(label="1", probability=0.6),
        ],
        selected_outcome="0",
    )

    assert model.mode == "collapse"
    assert model.selected_outcome == "0"


def test_build_measurement_model_derives_outcomes_from_latest_snapshot() -> None:
    """Given observable snapshot histogram, when building model, then outcomes are derived from histogram."""
    model = build_measurement_model(mode="collapse", snapshots=[_snapshot_with_histogram()])

    assert [outcome.label for outcome in model.outcomes] == ["0", "1"]
    assert model.selected_outcome == "1"


def test_build_measurement_model_rejects_branching_mode() -> None:
    """Given unsupported branching mode, when building measurement model, then ValueError is raised."""
    with pytest.raises(ValueError, match="collapse"):
        build_measurement_model(
            mode="branching",
            snapshots=[],
            outcomes_override=[MeasurementOutcome(label="0", probability=1.0)],
        )
