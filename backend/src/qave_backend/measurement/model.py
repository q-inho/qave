"""Measurement contract helpers."""

from __future__ import annotations

from qave_backend.contracts.models import (
    MeasurementModel,
    MeasurementOutcome,
    ObservableSnapshot,
)


def build_measurement_model(
    mode: str,
    snapshots: list[ObservableSnapshot],
    outcomes_override: list[MeasurementOutcome] | None = None,
    selected_outcome: str | None = None,
) -> MeasurementModel:
    """Create contract-compliant measurement objects."""
    if mode != "collapse":
        msg = "measurement_mode must be 'collapse'; branching is no longer supported"
        raise ValueError(msg)

    if outcomes_override is not None:
        outcomes = outcomes_override
    elif snapshots:
        outcomes = [
            MeasurementOutcome(label=item.outcome, probability=item.probability)
            for item in snapshots[-1].measurement_histogram
        ]
    else:
        outcomes = [MeasurementOutcome(label="0", probability=1.0)]

    if not outcomes:
        outcomes = [MeasurementOutcome(label="0", probability=1.0)]

    selected = selected_outcome
    if selected is None:
        selected = max(outcomes, key=lambda item: item.probability).label

    return MeasurementModel(
        mode="collapse",
        outcomes=outcomes,
        selected_outcome=selected,
    )
