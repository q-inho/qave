"""Tests for high-level algorithm-trace contract models."""

from __future__ import annotations

import pytest

from qave_backend.contracts.models import (
    AlgorithmTrace,
    AnimationPhaseRatio,
    AnimationTimelineSpec,
    ApproximationPolicy,
    BasisProbability,
    BoundaryCheckpoint,
    EntanglementMetrics,
    MeasurementModel,
    MeasurementOutcome,
    ObservableSnapshot,
    PhaseWindow,
    ScalabilityPolicy,
    StateSummary,
    TraceStep,
)


def _scalability_policy() -> ScalabilityPolicy:
    """Build a minimal scalability policy fixture for contract tests."""
    return ScalabilityPolicy(
        small_n_max=8,
        medium_n_max=16,
        small_mode_features=["a"],
        medium_mode_features=["b"],
        large_mode_features=["c"],
        approximation_policy=ApproximationPolicy(
            allow_approx_backends=True,
            fallback_backend_order=["statevector"],
        ),
    )


def _measurement_model() -> MeasurementModel:
    """Build deterministic collapse measurement fixture."""
    return MeasurementModel(
        mode="collapse",
        outcomes=[MeasurementOutcome(label="00", probability=1.0)],
        selected_outcome="00",
    )


def _observable() -> ObservableSnapshot:
    """Build minimal observable snapshot fixture."""
    return ObservableSnapshot(
        snapshot_id="snap_0",
        step_index=0,
        bloch_vectors=[],
        purity_entropy=[],
        top_k_amplitudes=[],
        reduced_density_blocks=[],
        entanglement_metrics=EntanglementMetrics(),
        measurement_histogram=[],
    )


def test_measurement_model_requires_selected_outcome() -> None:
    """Given collapse mode without selected outcome, when parsing model, then validation fails."""
    with pytest.raises(ValueError):
        MeasurementModel.model_validate(
            {
                "mode": "collapse",
                "outcomes": [{"label": "0", "probability": 1.0}],
            }
        )


def test_algorithm_trace_accepts_minimum_contract_shape() -> None:
    """Given minimally valid trace payload, when parsed, then required fields are retained."""
    trace = AlgorithmTrace(
        contract_version="0.1.0",
        algorithm_id="bell",
        steps=[
            TraceStep(
                step_index=0,
                operation_id="g0",
                operation_name="h",
                operation_qubits=[0],
                operation_controls=[],
                operation_targets=[0],
                state_summary=StateSummary(norm=1.0),
                probabilities=[BasisProbability(basis="0", p=1.0)],
                phase_windows=[
                    PhaseWindow(phase="pre_gate", t_start=0.0, t_end=0.2),
                    PhaseWindow(phase="apply_gate", t_start=0.2, t_end=0.75),
                    PhaseWindow(phase="settle", t_start=0.75, t_end=1.0),
                ],
                boundary_checkpoint=BoundaryCheckpoint(gate_start_hash="a", gate_end_hash="b"),
            )
        ],
        measurement_model=_measurement_model(),
        observable_snapshots=[_observable()],
        scalability_policy=_scalability_policy(),
        timeline=AnimationTimelineSpec(
            contract_version="0.1.0",
            timeline_id="t0",
            total_steps=1,
            default_step_duration_ms=800,
            phase_ratio=AnimationPhaseRatio(pre_gate=0.2, apply_gate=0.55, settle=0.25),
            keyframes=[],
            sync_fence_ids=["step_0"],
        ),
        view_sync_groups=["circuit", "amplitude", "probability"],
    )

    assert trace.algorithm_id == "bell"
    assert trace.view_sync_groups == ["circuit", "amplitude", "probability"]
