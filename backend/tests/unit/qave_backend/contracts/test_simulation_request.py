# ruff: noqa: E501
"""Tests for `SimulationRequest` contract validation behavior."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qave_backend.contracts.models import SimulationRequest


def test_simulation_request_valid_payload_parses() -> None:
    """Given valid request payload, when model is parsed, then fields are preserved."""
    request = SimulationRequest(
        contract_version="0.1.0",
        request_id="req_1",
        algorithm_id="bell",
        mode="validation",
        seed=10,
        precision_profile="strict",
        measurement_mode="collapse",
        animation_profile="teaching_default",
    )
    assert request.request_id == "req_1"


def test_simulation_request_rejects_branching_measurement_mode() -> None:
    """Given unsupported measurement mode, when request is parsed, then validation fails."""
    with pytest.raises(ValueError):
        SimulationRequest.model_validate(
            {
                "contract_version": "0.1.0",
                "request_id": "req_branching",
                "algorithm_id": "bell",
                "mode": "preview",
                "seed": 10,
                "precision_profile": "balanced",
                "measurement_mode": "branching",
                "animation_profile": "teaching_default",
            }
        )


def test_simulation_request_accepts_custom_algorithm_id() -> None:
    """Given custom algorithm_id, when request is parsed, then model accepts the payload."""
    request = SimulationRequest(
        contract_version="0.1.0",
        request_id="req_custom",
        algorithm_id="custom",
        mode="preview",
        seed=10,
        precision_profile="balanced",
        measurement_mode="collapse",
        animation_profile="teaching_default",
    )
    assert request.algorithm_id == "custom"


def test_simulation_request_rejects_unknown_algorithm_id() -> None:
    """Given unknown algorithm ID, when request is parsed, then pydantic ValidationError is raised."""
    with pytest.raises(ValidationError):
        SimulationRequest(
            contract_version="0.1.0",
            request_id="req_removed_algorithm",
            algorithm_id="removed_algorithm",  # type: ignore[arg-type]
            mode="preview",
            seed=10,
            precision_profile="balanced",
            measurement_mode="collapse",
            animation_profile="teaching_default",
        )


def test_simulation_request_rejects_non_positive_shot_count() -> None:
    """Given non-positive shot count, when request is parsed, then validation fails."""
    with pytest.raises(ValueError):
        SimulationRequest(
            contract_version="0.1.0",
            request_id="req_shot_invalid",
            algorithm_id="bell",
            mode="preview",
            seed=10,
            precision_profile="balanced",
            measurement_mode="collapse",
            animation_profile="teaching_default",
            shot_count=0,
        )
