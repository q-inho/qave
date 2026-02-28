"""Tests for public qave option dataclasses."""

from __future__ import annotations

from pathlib import Path

import pytest

from qave.options import ArtifactOptions, RenderOptions, SimulationOptions


def test_simulation_options_defaults_are_stable() -> None:
    """Given default options, when constructed, then baseline defaults are preserved."""
    options = SimulationOptions()
    assert options.algorithm_id == "custom"
    assert options.mode == "preview"
    assert options.measurement_mode == "collapse"
    assert options.shot_count == 100


def test_simulation_options_reject_non_positive_shot_count() -> None:
    """Given invalid shot count, when constructing options, then ValueError is raised."""
    with pytest.raises(ValueError, match="shot_count"):
        SimulationOptions(shot_count=0)


def test_simulation_options_reject_negative_seed() -> None:
    """Given negative seed, when constructing options, then ValueError is raised."""
    with pytest.raises(ValueError, match="seed"):
        SimulationOptions(seed=-1)


def test_simulation_options_reject_branching_measurement_mode() -> None:
    """Given unsupported measurement mode, when constructing options, then ValueError is raised."""
    with pytest.raises(ValueError, match="collapse"):
        SimulationOptions(measurement_mode="branching")  # type: ignore[arg-type]


def test_render_options_reject_too_small_resolution() -> None:
    """Given undersized render dimensions, when constructing options, then ValueError is raised."""
    with pytest.raises(ValueError, match="320x240"):
        RenderOptions(width=200, height=200)


def test_render_options_reject_all_outputs_disabled() -> None:
    """Given all output flags disabled, when constructing options, then ValueError is raised."""
    with pytest.raises(ValueError, match="At least one"):
        RenderOptions(keep_frames=False, emit_mp4=False, emit_gif=False)


def test_render_options_reject_invalid_fps() -> None:
    """Given invalid FPS, when constructing options, then ValueError is raised."""
    with pytest.raises(ValueError, match="fps"):
        RenderOptions(fps=0)


def test_artifact_options_default_and_explicit_paths() -> None:
    """Given artifact options, when built with and without out_dir, then values are preserved."""
    default_options = ArtifactOptions()
    explicit_path = Path("custom_artifacts")
    explicit_options = ArtifactOptions(out_dir=explicit_path)

    assert default_options.out_dir is None
    assert explicit_options.out_dir == explicit_path
