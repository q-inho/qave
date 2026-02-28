#!/usr/bin/env python3
"""Validate camera continuity and replay focus/depth semantics for Processing viewer traces."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_FPS = 60.0
VIEWPORT_W = 1600.0
VIEWPORT_H = 960.0

# Camera constants from viewer/processing_qave/CameraDirector.pde
LOCKED_CONV_POSE = (0.0, -20.0, 0.0, 1.00, 0.0, 0.0)
DRIFT_PRIMARY = (0.22, 0.16, 0.26, 0.010, 0.0032, 0.0022)
DRIFT_SECONDARY = (0.08, 0.06, 0.10, 0.004, 0.0013, 0.0011)
SHOT_PULLBACK_POSE = (40.0, -10.0, 0.0, 3.0, 0.0, 0.0)
SHOT_STACK_POSE = (20.0, -10.0, 0.0, 3.0, 0.0, -0.1)
SHOT_DRIFT_PRIMARY = (0.14, 0.09, 0.08, 0.0035, 0.0011, 0.0007)
SHOT_DRIFT_SECONDARY = (0.05, 0.03, 0.04, 0.0015, 0.0006, 0.0004)
SHOT_STACK_BREATH = (0.20, 0.0, 0.10, 0.012, 0.0012, 0.0010)
SHOT_PROJECT_CAMERA_HOLD_FRACTION = 0.50
SHOT_STACK_EXTRA_FRAMES = 4
OCCUPANCY_MIN_W = 0.42
OCCUPANCY_MAX_W = 0.50
OCCUPANCY_MIN_H = 0.46
OCCUPANCY_MAX_H = 0.56
REPLAY_OCC_PULLBACK_MIN_W = 0.46
REPLAY_OCC_PULLBACK_MAX_W = 0.60
REPLAY_OCC_PULLBACK_MIN_H = 0.34
REPLAY_OCC_PULLBACK_MAX_H = 0.56
REPLAY_OCC_STACK_MIN_W = 0.40
REPLAY_OCC_STACK_MAX_W = 0.52
REPLAY_OCC_STACK_MIN_H = 0.28
REPLAY_OCC_STACK_MAX_H = 0.46
REPLAY_DISTANCE_SOLVE_BIAS = 0.22

# Depth/focus constants from CameraDirector + MatrixEvolutionPane.
SHOT_QUBIT_MIN_HIST_GAP = 14.0
SHOT_QUBIT_HIST_GAP_CUBE_MULT = 0.95
SHOT_REPLAY_LAYER_GAP_SCALE = 10.0
SHOT_QUBIT_CUBE_SIZE_RATIO = 0.64
SHOT_QUBIT_CUBE_MIN_SIZE = 8.0
SHOT_QUBIT_CUBE_MAX_SIZE = 26.0
SHOT_REPLAY_DEPTH_BLEND = 0.30
SHOT_STACK_SOFT_CAP_LINEAR_LAYERS = 24
SHOT_STACK_TAIL_COMPRESS_RATIO = 0.28
SHOT_STACK_DEPTH_BASE_MULT = 0.58
SHOT_STACK_DEPTH_BASE_MIN = 5.0
SHOT_STACK_DEPTH_BASE_MAX = 18.0
STACK_DEPTH_STEP_MULT = 0.62
STACK_DEPTH_STEP_MIN = 12.0
STACK_DEPTH_STEP_MAX = 48.0
STACK_NO_OVERLAP_MULT = 0.96
STACK_NO_OVERLAP_MARGIN = 1.0
LAYER_SCALE_DECAY_PER_AGE = 0.012
CUBE_PITCH_FILL_RATIO = 0.90

ROTATION_SCALE_DEG = 1.0
ZOOM_SCALE = 0.02
PAN_SCALE = 0.01
ROTATION_DAMP = 0.14
ZOOM_DAMP = 0.14
PAN_DAMP = 0.16
FOCUS_TOL = 1e-4
DEPTH_TOL = 1e-3
PROJECTION_LOCK_POSE_TOL = 1e-4
PROJECTION_LOCK_DISTANCE_TOL = 1e-3
PROJECTION_LOCK_ACQUIRE_FRAMES = 24


@dataclass(frozen=True)
class PhaseWindow:
    """Represent PhaseWindow data.

    Attributes:
        phase: Stored value for this data container.
        start_frame: Stored value for this data container.
        end_frame: Stored value for this data container.
    """

    phase: str
    start_frame: int
    end_frame: int


@dataclass(frozen=True)
class StepMetrics:
    """Represent StepMetrics data.

    Attributes:
        rows: Stored value for this data container.
        cols: Stored value for this data container.
        matrix_w: Stored value for this data container.
        matrix_h: Stored value for this data container.
        cube_size: Stored value for this data container.
    """

    rows: int
    cols: int
    matrix_w: float
    matrix_h: float
    cube_size: float


@dataclass(frozen=True)
class FramePose:
    """Represent FramePose data.

    Attributes:
        frame_index: Stored value for this data container.
        phase: Stored value for this data container.
        phase_progress: Stored value for this data container.
        shot_index: Stored value for this data container.
        shot_progress: Stored value for this data container.
        timeline_progress_global: Stored value for this data container.
        shots_total: Stored value for this data container.
        pose: Stored value for this data container.
        focus_z: Stored value for this data container.
        depth_budget: Stored value for this data container.
    """

    frame_index: int
    phase: str
    phase_progress: float
    shot_index: int
    shot_progress: float
    timeline_progress_global: float
    shots_total: int
    pose: tuple[float, float, float, float, float, float]
    focus_z: float
    depth_budget: float


def clamp(value: float, lower: float, upper: float) -> float:
    """Compute clamp.

    Args:
        value: Input value for this computation.
        lower: Input value for this computation.
        upper: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return max(lower, min(upper, value))


def lerp(a: float, b: float, t: float) -> float:
    """Compute lerp.

    Args:
        a: Input value for this computation.
        b: Input value for this computation.
        t: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    alpha = clamp(t, 0.0, 1.0)
    return a + (b - a) * alpha


def add_pose(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    """Compute add pose.

    Args:
        a: Input value for this computation.
        b: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    return tuple(a[idx] + b[idx] for idx in range(len(a)))


def lerp_pose(
    a: tuple[float, float, float, float, float, float],
    b: tuple[float, float, float, float, float, float],
    t: float,
) -> tuple[float, float, float, float, float, float]:
    """Compute lerp pose.

    Args:
        a: Input value for this computation.
        b: Input value for this computation.
        t: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    alpha = clamp(t, 0.0, 1.0)
    return tuple(a[idx] + (b[idx] - a[idx]) * alpha for idx in range(6))


def ease_in_out_sine01(value: float) -> float:
    """Compute ease in out sine01.

    Args:
        value: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    x = clamp(value, 0.0, 1.0)
    return -(math.cos(math.pi * x) - 1.0) * 0.5


def resolve_shot_project_move_alpha(phase_progress: float) -> float:
    """Resolve shot project move alpha.

    Args:
        phase_progress: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    eased = ease_in_out_sine01(phase_progress)
    if eased <= SHOT_PROJECT_CAMERA_HOLD_FRACTION:
        return 0.0
    denom = max(1e-5, 1.0 - SHOT_PROJECT_CAMERA_HOLD_FRACTION)
    return clamp((eased - SHOT_PROJECT_CAMERA_HOLD_FRACTION) / denom, 0.0, 1.0)


def resolve_gate_pose(
    timeline_progress_global: float,
) -> tuple[float, float, float, float, float, float]:
    """Resolve gate pose.

    Args:
        timeline_progress_global: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    t = clamp(timeline_progress_global, 0.0, 1.0)
    theta = 2.0 * math.pi * t
    primary = math.sin(theta)
    secondary = math.sin(theta * 2.0)
    drift = (
        DRIFT_PRIMARY[0] * primary + DRIFT_SECONDARY[0] * secondary,
        DRIFT_PRIMARY[1] * primary + DRIFT_SECONDARY[1] * secondary,
        DRIFT_PRIMARY[2] * primary + DRIFT_SECONDARY[2] * secondary,
        DRIFT_PRIMARY[3] * primary + DRIFT_SECONDARY[3] * secondary,
        DRIFT_PRIMARY[4] * primary + DRIFT_SECONDARY[4] * secondary,
        DRIFT_PRIMARY[5] * primary + DRIFT_SECONDARY[5] * secondary,
    )
    return add_pose(LOCKED_CONV_POSE, drift)


def resolve_shot_stack_drift(
    timeline_progress_global: float,
) -> tuple[float, float, float, float, float, float]:
    """Resolve shot stack drift.

    Args:
        timeline_progress_global: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    t = clamp(timeline_progress_global, 0.0, 1.0)
    theta = 2.0 * math.pi * t
    primary = math.sin(theta)
    secondary = math.sin(theta * 2.0 + math.pi * 0.25)
    return (
        SHOT_DRIFT_PRIMARY[0] * primary + SHOT_DRIFT_SECONDARY[0] * secondary,
        SHOT_DRIFT_PRIMARY[1] * primary + SHOT_DRIFT_SECONDARY[1] * secondary,
        SHOT_DRIFT_PRIMARY[2] * primary + SHOT_DRIFT_SECONDARY[2] * secondary,
        SHOT_DRIFT_PRIMARY[3] * primary + SHOT_DRIFT_SECONDARY[3] * secondary,
        SHOT_DRIFT_PRIMARY[4] * primary + SHOT_DRIFT_SECONDARY[4] * secondary,
        SHOT_DRIFT_PRIMARY[5] * primary + SHOT_DRIFT_SECONDARY[5] * secondary,
    )


def resolve_shot_stack_breath(
    shot_progress: float,
) -> tuple[float, float, float, float, float, float]:
    """Resolve shot stack breath.

    Args:
        shot_progress: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    pulse = math.sin(math.pi * clamp(shot_progress, 0.0, 1.0))
    return (
        SHOT_STACK_BREATH[0] * pulse,
        SHOT_STACK_BREATH[1] * pulse,
        SHOT_STACK_BREATH[2] * pulse,
        SHOT_STACK_BREATH[3] * pulse,
        SHOT_STACK_BREATH[4] * pulse,
        SHOT_STACK_BREATH[5] * pulse,
    )


def resolve_pose(
    phase: str,
    phase_progress: float,
    timeline_progress_global: float,
    shot_index: int,
    shot_progress: float,
) -> tuple[float, float, float, float, float, float]:
    """Resolve pose.

    Args:
        phase: Input value for this computation.
        phase_progress: Input value for this computation.
        timeline_progress_global: Input value for this computation.
        shot_index: Input value for this computation.
        shot_progress: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    gate_pose = resolve_gate_pose(timeline_progress_global)
    if phase == "shot_camera_pullback":
        return lerp_pose(gate_pose, SHOT_STACK_POSE, ease_in_out_sine01(phase_progress))
    if phase == "shot_stack":
        drifted = add_pose(SHOT_STACK_POSE, resolve_shot_stack_drift(timeline_progress_global))
        return add_pose(drifted, resolve_shot_stack_breath(shot_progress))
    if phase == "shot_histogram_project":
        if shot_index < 0:
            drifted = add_pose(SHOT_STACK_POSE, resolve_shot_stack_drift(timeline_progress_global))
            alpha = resolve_shot_project_move_alpha(phase_progress)
            return lerp_pose(drifted, SHOT_STACK_POSE, alpha)
        return SHOT_STACK_POSE
    return gate_pose


def smooth_pose(
    current: tuple[float, float, float, float, float, float],
    target: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    """Compute smooth pose.

    Args:
        current: Input value for this computation.
        target: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    return (
        lerp(current[0], target[0], ROTATION_DAMP),
        lerp(current[1], target[1], ROTATION_DAMP),
        lerp(current[2], target[2], ROTATION_DAMP),
        lerp(current[3], target[3], ZOOM_DAMP),
        lerp(current[4], target[4], PAN_DAMP),
        lerp(current[5], target[5], PAN_DAMP),
    )


def is_projection_shot_lock_phase(phase: str, shot_index: int) -> bool:
    """Return whether projection shot lock phase.

    Args:
        phase: Input value for this computation.
        shot_index: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    return phase == "shot_histogram_project" and shot_index >= 0


def normalize_phase_windows(
    raw_windows: list[dict[str, Any]], frames_per_step: int
) -> list[PhaseWindow]:
    """Normalize phase windows.

    Args:
        raw_windows: Input value for this computation.
        frames_per_step: Input value for this computation.

    Returns:
        The computed list value.
    """
    windows: list[PhaseWindow] = []
    for item in raw_windows:
        phase = str(item.get("phase", "apply_gate"))
        start_norm = clamp(float(item.get("t_start", 0.0)), 0.0, 1.0)
        end_norm = clamp(float(item.get("t_end", 1.0)), 0.0, 1.0)
        start_frame = int(round(start_norm * frames_per_step))
        end_frame = int(round(end_norm * frames_per_step))
        start_frame = int(clamp(start_frame, 0, frames_per_step))
        end_frame = int(clamp(end_frame, 0, frames_per_step))
        if end_frame <= start_frame:
            end_frame = min(frames_per_step, start_frame + 1)
        windows.append(PhaseWindow(phase, start_frame, end_frame))

    if not windows:
        windows = [PhaseWindow("apply_gate", 0, frames_per_step)]

    windows.sort(key=lambda window: window.start_frame)
    first = windows[0]
    windows[0] = PhaseWindow(first.phase, 0, first.end_frame)
    last = windows[-1]
    windows[-1] = PhaseWindow(last.phase, last.start_frame, frames_per_step)
    return windows


def active_phase_window(local_frame: int, windows: list[PhaseWindow]) -> PhaseWindow:
    """Compute active phase window.

    Args:
        local_frame: Input value for this computation.
        windows: Input value for this computation.

    Returns:
        The computed value.
    """
    for window in windows:
        if local_frame >= window.start_frame and local_frame < window.end_frame:
            return window
    return windows[-1]


def has_measurement_reveal(trace: dict[str, Any]) -> bool:
    """Return whether measurement reveal.

    Args:
        trace: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    measurement_model = trace.get("measurement_model") or {}
    mode = str(measurement_model.get("mode", ""))
    selected = str(measurement_model.get("selected_outcome", ""))
    has_measurement_step = any(
        bool((step.get("measurement") or {}).get("is_measurement", False))
        for step in trace.get("steps", [])
        if isinstance(step, dict)
    )
    return has_measurement_step and mode == "collapse" and len(selected) > 0


def measurement_shot_replay(trace: dict[str, Any]) -> dict[str, Any] | None:
    """Compute measurement shot replay.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    replay = trace.get("measurement_shot_replay")
    if not isinstance(replay, dict):
        return None
    timeline = replay.get("timeline")
    if not isinstance(timeline, dict):
        return None
    shots_total = int(replay.get("shots_total", 0))
    if shots_total <= 0:
        return None
    frames_per_shot = int(timeline.get("frames_per_shot", 0))
    if frames_per_shot <= 0:
        return None
    return replay


def is_rectangular(real: Any, imag: Any) -> bool:
    """Return whether rectangular.

    Args:
        real: Input value for this computation.
        imag: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    if not isinstance(real, list) or not isinstance(imag, list):
        return False
    if not real or not imag or len(real) != len(imag):
        return False
    cols = len(real[0]) if isinstance(real[0], list) else 0
    if cols <= 0:
        return False
    for idx in range(len(real)):
        if not isinstance(real[idx], list) or not isinstance(imag[idx], list):
            return False
        if len(real[idx]) != cols or len(imag[idx]) != cols:
            return False
    return True


def select_preferred_block(blocks: Any) -> dict[str, Any] | None:
    """Select preferred block.

    Args:
        blocks: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    if not isinstance(blocks, list) or not blocks:
        return None
    largest: dict[str, Any] | None = None
    largest_span = -1
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if not is_rectangular(block.get("real"), block.get("imag")):
            continue
        span = len(block.get("qubits") or [])
        if span > largest_span:
            largest_span = span
            largest = block
    return largest


def resolve_step_metrics(trace: dict[str, Any]) -> dict[int, StepMetrics]:
    """Resolve step metrics.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    steps = trace.get("steps")
    metrics_by_step: dict[int, StepMetrics] = {}
    if not isinstance(steps, list):
        return metrics_by_step

    panel_w = VIEWPORT_W - 12.0
    panel_h = max(280.0, VIEWPORT_H - 12.0 - 8.0)

    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        samples = step.get("evolution_samples")
        if not isinstance(samples, list):
            continue
        selected_block = None
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            block = select_preferred_block(sample.get("reduced_density_blocks"))
            if block is not None:
                selected_block = block
                break
        if selected_block is None:
            continue
        real = selected_block.get("real")
        imag = selected_block.get("imag")
        if not is_rectangular(real, imag):
            continue

        rows = max(1, len(real))
        cols = max(1, len(real[0]))
        target_matrix_w = clamp(panel_w * 0.58, panel_w * 0.55, panel_w * 0.62)
        target_matrix_h = clamp(panel_h * 0.34, panel_h * 0.30, panel_h * 0.38)
        pitch_w = target_matrix_w / max(1.0, float(cols))
        pitch_h = target_matrix_h / max(1.0, float(rows))
        pitch = clamp(min(pitch_w, pitch_h), 30.0, 170.0)
        cube_size = max(8.0, pitch * CUBE_PITCH_FILL_RATIO)

        metrics_by_step[idx] = StepMetrics(
            rows=rows,
            cols=cols,
            matrix_w=cols * pitch,
            matrix_h=rows * pitch,
            cube_size=cube_size,
        )

    return metrics_by_step


def resolve_base_stack_depth_step(cube_size: float) -> float:
    """Resolve base stack depth step.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return clamp(cube_size * STACK_DEPTH_STEP_MULT, STACK_DEPTH_STEP_MIN, STACK_DEPTH_STEP_MAX)


def resolve_conservative_no_overlap_gap(cube_size: float) -> float:
    """Resolve conservative no overlap gap.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    side_a = cube_size * max(0.72, 1.0)
    side_b = cube_size * max(0.72, 1.0 - LAYER_SCALE_DECAY_PER_AGE)
    return (side_a + side_b) * 0.5 + STACK_NO_OVERLAP_MARGIN


def resolve_guaranteed_depth_step(cube_size: float) -> float:
    """Resolve guaranteed depth step.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    base_step = resolve_base_stack_depth_step(cube_size)
    no_overlap_step = cube_size * STACK_NO_OVERLAP_MULT + STACK_NO_OVERLAP_MARGIN
    conservative_gap = resolve_conservative_no_overlap_gap(cube_size)
    return max(base_step, no_overlap_step, conservative_gap)


def resolve_stack_depth_budget(
    matrix_w: float, matrix_h: float, cube_size: float, layer_count: int
) -> float:
    """Resolve stack depth budget.

    Args:
        matrix_w: Input value for this computation.
        matrix_h: Input value for this computation.
        cube_size: Input value for this computation.
        layer_count: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    del matrix_w, matrix_h
    depth_step = resolve_guaranteed_depth_step(cube_size)
    depth_span = depth_step * max(0.0, float(layer_count - 1))
    return max(44.0, depth_span + cube_size * 0.9)


def shot_replay_matrix_front_z(metrics: StepMetrics) -> float:
    """Compute shot replay matrix front z.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return 1.10 + metrics.cube_size * 0.92


def shot_replay_layer_gap(metrics: StepMetrics) -> float:
    """Compute shot replay layer gap.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    base_gap = max(SHOT_QUBIT_MIN_HIST_GAP, metrics.cube_size * SHOT_QUBIT_HIST_GAP_CUBE_MULT)
    return base_gap * SHOT_REPLAY_LAYER_GAP_SCALE


def shot_replay_qubit_front_z(metrics: StepMetrics) -> float:
    """Compute shot replay qubit front z.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return shot_replay_matrix_front_z(metrics) + shot_replay_layer_gap(metrics)


def shot_replay_histogram_front_z(metrics: StepMetrics) -> float:
    """Compute shot replay histogram front z.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return shot_replay_qubit_front_z(metrics) + shot_replay_layer_gap(metrics)


def shot_replay_depth_base_step(metrics: StepMetrics) -> float:
    """Compute shot replay depth base step.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return clamp(
        metrics.cube_size * SHOT_STACK_DEPTH_BASE_MULT,
        SHOT_STACK_DEPTH_BASE_MIN,
        SHOT_STACK_DEPTH_BASE_MAX,
    )


def shot_replay_depth_offset(metrics: StepMetrics, age: float) -> float:
    """Compute shot replay depth offset.

    Args:
        metrics: Input value for this computation.
        age: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    safe_age = max(0.0, age)
    base_step = shot_replay_depth_base_step(metrics)
    linear_age = min(float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS), safe_age)
    tail_age = max(0.0, safe_age - float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS))
    return linear_age * base_step + tail_age * base_step * SHOT_STACK_TAIL_COMPRESS_RATIO


def shot_replay_qubit_cube_side(metrics: StepMetrics) -> float:
    """Compute shot replay qubit cube side.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return clamp(
        metrics.cube_size * SHOT_QUBIT_CUBE_SIZE_RATIO,
        SHOT_QUBIT_CUBE_MIN_SIZE,
        SHOT_QUBIT_CUBE_MAX_SIZE,
    )


def shot_replay_base_cube_depth(metrics: StepMetrics) -> float:
    """Compute shot replay base cube depth.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    cube_side = shot_replay_qubit_cube_side(metrics)
    return clamp(
        cube_side * 0.92,
        SHOT_QUBIT_CUBE_MIN_SIZE * 0.85,
        SHOT_QUBIT_CUBE_MAX_SIZE * 0.96,
    )


def shot_replay_density_rendered_front_z(metrics: StepMetrics) -> float:
    """Compute shot replay density rendered front z.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return 1.10 + metrics.cube_size + 0.35


def shot_replay_spawn_front_gap(metrics: StepMetrics) -> float:
    """Compute shot replay spawn front gap.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    cube_side = shot_replay_qubit_cube_side(metrics)
    return clamp(cube_side * 0.16, 2.4, 7.0)


def shot_replay_front_safe_max_depth_offset(metrics: StepMetrics) -> float:
    """Compute shot replay front safe max depth offset.

    Args:
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    qubit_front_z = shot_replay_qubit_front_z(metrics)
    density_front_z = shot_replay_density_rendered_front_z(metrics)
    spawn_gap = shot_replay_spawn_front_gap(metrics)
    min_layer_center_z = density_front_z + spawn_gap + shot_replay_base_cube_depth(metrics) * 0.5
    return max(0.0, qubit_front_z - min_layer_center_z)


def shot_replay_effective_max_depth_offset(metrics: StepMetrics, shots_total: int) -> float:
    """Compute shot replay effective max depth offset.

    Args:
        metrics: Input value for this computation.
        shots_total: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    raw_max = shot_replay_depth_offset(metrics, max(0.0, float(shots_total - 1)))
    front_safe_max = shot_replay_front_safe_max_depth_offset(metrics)
    return min(raw_max, front_safe_max)


def resolve_focus_z(frame: FramePose, metrics: StepMetrics) -> float:
    """Resolve focus z.

    Args:
        frame: Input value for this computation.
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    qubit_focus_z = shot_replay_qubit_front_z(metrics)
    histogram_focus_z = shot_replay_histogram_front_z(metrics)
    if frame.phase == "shot_camera_pullback":
        return lerp(0.0, qubit_focus_z, ease_in_out_sine01(frame.phase_progress))
    if frame.phase == "shot_stack":
        return qubit_focus_z
    if frame.phase == "shot_histogram_project":
        if frame.shot_index < 0:
            alpha = resolve_shot_project_move_alpha(frame.phase_progress)
            return lerp(qubit_focus_z, histogram_focus_z, alpha)
        return histogram_focus_z
    return 0.0


def resolve_replay_depth_budget(frame: FramePose, metrics: StepMetrics) -> float:
    """Resolve replay depth budget.

    Args:
        frame: Input value for this computation.
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    matrix_front_z = shot_replay_matrix_front_z(metrics)
    qubit_front_z = shot_replay_qubit_front_z(metrics)
    histogram_front_z = shot_replay_histogram_front_z(metrics)
    stack_back_offset = shot_replay_effective_max_depth_offset(metrics, frame.shots_total)
    stack_back_z = qubit_front_z - stack_back_offset

    margin = max(12.0, metrics.cube_size * 0.90)
    replay_min_z = min(0.0, min(matrix_front_z - margin, stack_back_z - margin))
    replay_max_z = max(histogram_front_z + margin, qubit_front_z + margin)
    replay_span = max(1.0, replay_max_z - replay_min_z)
    extent_from_focus = max(abs(frame.focus_z - replay_min_z), abs(replay_max_z - frame.focus_z))
    symmetric_span = max(1.0, extent_from_focus * 2.0)
    blended_span = replay_span + (symmetric_span - replay_span) * SHOT_REPLAY_DEPTH_BLEND
    replay_depth = blended_span + margin
    return max(1.0, replay_depth)


def resolve_occupancy_envelope(frame: FramePose) -> tuple[float, float, float, float]:
    """Resolve occupancy envelope.

    Args:
        frame: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    if frame.phase == "shot_camera_pullback":
        return (
            REPLAY_OCC_PULLBACK_MIN_W,
            REPLAY_OCC_PULLBACK_MAX_W,
            REPLAY_OCC_PULLBACK_MIN_H,
            REPLAY_OCC_PULLBACK_MAX_H,
        )
    if frame.phase == "shot_histogram_project":
        if is_projection_shot_lock_phase(frame.phase, frame.shot_index):
            return (
                REPLAY_OCC_STACK_MIN_W,
                REPLAY_OCC_STACK_MAX_W,
                REPLAY_OCC_STACK_MIN_H,
                REPLAY_OCC_STACK_MAX_H,
            )
        alpha = resolve_shot_project_move_alpha(frame.phase_progress)
        return (
            lerp(REPLAY_OCC_PULLBACK_MIN_W, REPLAY_OCC_STACK_MIN_W, alpha),
            lerp(REPLAY_OCC_PULLBACK_MAX_W, REPLAY_OCC_STACK_MAX_W, alpha),
            lerp(REPLAY_OCC_PULLBACK_MIN_H, REPLAY_OCC_STACK_MIN_H, alpha),
            lerp(REPLAY_OCC_PULLBACK_MAX_H, REPLAY_OCC_STACK_MAX_H, alpha),
        )
    if frame.phase == "shot_stack":
        return (
            REPLAY_OCC_STACK_MIN_W,
            REPLAY_OCC_STACK_MAX_W,
            REPLAY_OCC_STACK_MIN_H,
            REPLAY_OCC_STACK_MAX_H,
        )
    return (OCCUPANCY_MIN_W, OCCUPANCY_MAX_W, OCCUPANCY_MIN_H, OCCUPANCY_MAX_H)


def resolve_projected_span(
    metrics: StepMetrics,
    pose: tuple[float, float, float, float, float, float],
    depth_budget: float,
) -> tuple[float, float, float]:
    """Resolve projected span.

    Args:
        metrics: Input value for this computation.
        pose: Input value for this computation.
        depth_budget: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    rx = math.radians(pose[0])
    ry = math.radians(pose[1])
    rz = math.radians(pose[2])
    cos_x = math.cos(rx)
    sin_x = math.sin(rx)
    cos_y = math.cos(ry)
    sin_y = math.sin(ry)
    cos_z = math.cos(rz)
    sin_z = math.sin(rz)
    half_w = metrics.matrix_w * 0.5
    half_h = metrics.matrix_h * 0.5
    half_d = max(1.0, depth_budget * 0.5)

    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")
    min_z = float("inf")
    max_z = float("-inf")
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                x = sx * half_w
                y = sy * half_h
                z = sz * half_d

                xx = x
                yx = y * cos_x - z * sin_x
                zx = y * sin_x + z * cos_x

                xy = xx * cos_y + zx * sin_y
                yy = yx
                zy = -xx * sin_y + zx * cos_y

                xz = xy * cos_z - yy * sin_z
                yz = xy * sin_z + yy * cos_z

                min_x = min(min_x, xz)
                max_x = max(max_x, xz)
                min_y = min(min_y, yz)
                max_y = max(max_y, yz)
                min_z = min(min_z, zy)
                max_z = max(max_z, zy)

    return (max(12.0, max_x - min_x), max(12.0, max_y - min_y), max(2.0, max_z - min_z))


def resolve_solved_distance(frame: FramePose, metrics: StepMetrics) -> float:
    """Resolve solved distance.

    Args:
        frame: Input value for this computation.
        metrics: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    projected_span = resolve_projected_span(metrics, frame.pose, frame.depth_budget)
    aspect = max(0.1, VIEWPORT_W / max(1.0, VIEWPORT_H))
    v_fov = math.pi / 3.0
    h_fov = 2.0 * math.atan(math.tan(v_fov * 0.5) * aspect)
    tan_h_fov = max(1e-4, math.tan(h_fov * 0.5))
    tan_v_fov = max(1e-4, math.tan(v_fov * 0.5))
    occupancy = resolve_occupancy_envelope(frame)

    depth_safety = projected_span[2] * 0.08
    half_w = max(6.0, projected_span[0] * 0.5 + depth_safety)
    half_h = max(6.0, projected_span[1] * 0.5 + depth_safety)

    lower_w = half_w / max(1e-4, occupancy[1] * tan_h_fov)
    upper_w = half_w / max(1e-4, occupancy[0] * tan_h_fov)
    lower_h = half_h / max(1e-4, occupancy[3] * tan_v_fov)
    upper_h = half_h / max(1e-4, occupancy[2] * tan_v_fov)

    lower = max(lower_w, lower_h)
    upper = min(upper_w, upper_h)
    replay_phase = frame.phase in {"shot_camera_pullback", "shot_histogram_project", "shot_stack"}
    solve_bias = REPLAY_DISTANCE_SOLVE_BIAS if replay_phase else 0.5
    solved_distance = lerp(lower, upper, solve_bias) if lower <= upper else lower
    safe_zoom = max(0.6, frame.pose[3])
    adjusted_distance = solved_distance / safe_zoom
    return clamp(adjusted_distance, 180.0, 12000.0)


def pose_delta(
    a: tuple[float, float, float, float, float, float],
    b: tuple[float, float, float, float, float, float],
) -> float:
    """Compute pose delta.

    Args:
        a: Input value for this computation.
        b: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    delta_rot_x = (b[0] - a[0]) / ROTATION_SCALE_DEG
    delta_rot_y = (b[1] - a[1]) / ROTATION_SCALE_DEG
    delta_rot_z = (b[2] - a[2]) / ROTATION_SCALE_DEG
    delta_zoom = (b[3] - a[3]) / ZOOM_SCALE
    delta_pan_x = (b[4] - a[4]) / PAN_SCALE
    delta_pan_y = (b[5] - a[5]) / PAN_SCALE
    return math.sqrt(
        delta_rot_x * delta_rot_x
        + delta_rot_y * delta_rot_y
        + delta_rot_z * delta_rot_z
        + delta_zoom * delta_zoom
        + delta_pan_x * delta_pan_x
        + delta_pan_y * delta_pan_y
    )


def reconstruct_frame_poses(trace: dict[str, Any]) -> list[FramePose]:
    """Reconstruct frame poses.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed list value.
    """
    steps = trace.get("steps", [])
    step_count = len(steps)
    if step_count <= 0:
        return []

    default_step_duration_ms = float(
        trace.get("timeline", {}).get("default_step_duration_ms", 800.0)
    )
    frame_duration_ms = 1000.0 / TARGET_FPS
    frames_per_step = max(1, int(round(default_step_duration_ms / frame_duration_ms)))
    gate_frame_count = max(1, step_count * frames_per_step)
    reveal_frames = 48 if has_measurement_reveal(trace) else 0

    replay = measurement_shot_replay(trace)
    pullback_frames = 0
    stack_frames_total = 0
    project_transition_frames = 0
    project_frames_total = 0
    shots_total = 0
    extended_per_shot = 0
    if replay is not None:
        timeline = replay.get("timeline", {})
        shots_total = max(1, int(replay.get("shots_total", 0)))
        pullback_frames = max(1, int(timeline.get("camera_pullback_frames", 36)))
        base_per_shot = max(1, int(timeline.get("frames_per_shot", 6)))
        extended_per_shot = base_per_shot + SHOT_STACK_EXTRA_FRAMES
        stack_frames_total = shots_total * extended_per_shot
        project_transition_frames = max(1, int(timeline.get("histogram_project_frames", 60)))
        project_frames_total = shots_total * extended_per_shot

    total_frames = (
        gate_frame_count
        + reveal_frames
        + pullback_frames
        + stack_frames_total
        + project_transition_frames
        + project_frames_total
    )

    metrics_by_step = resolve_step_metrics(trace)
    fallback_metrics = StepMetrics(rows=4, cols=4, matrix_w=320.0, matrix_h=320.0, cube_size=52.0)

    def metrics_for_step(step_index: int) -> StepMetrics:
        """Compute metrics for step.

        Args:
            step_index: Input value for this computation.

        Returns:
            The computed value.
        """
        return metrics_by_step.get(step_index, fallback_metrics)

    frames: list[FramePose] = []
    smoothed_pose: tuple[float, float, float, float, float, float] | None = None

    def camera_pose_for_target(
        target_pose: tuple[float, float, float, float, float, float],
        force_anchor: bool = False,
    ) -> tuple[float, float, float, float, float, float]:
        """Compute camera pose for target.

        Args:
            target_pose: Input value for this computation.
            force_anchor: Input value for this computation.

        Returns:
            The computed tuple value.
        """
        nonlocal smoothed_pose
        if smoothed_pose is None or force_anchor:
            smoothed_pose = target_pose
        else:
            smoothed_pose = smooth_pose(smoothed_pose, target_pose)
        return smoothed_pose

    for frame_index in range(total_frames):
        timeline_progress_global = (
            1.0
            if total_frames <= 1
            else clamp(frame_index / float(max(1, total_frames - 1)), 0.0, 1.0)
        )

        if reveal_frames > 0 and gate_frame_count <= frame_index < gate_frame_count + reveal_frames:
            reveal_frame = frame_index - gate_frame_count
            phase_progress = (
                1.0
                if reveal_frames <= 1
                else clamp(
                    reveal_frame / float(max(1, reveal_frames - 1)),
                    0.0,
                    1.0,
                )
            )
            phase = "measurement_reveal"
            target_pose = resolve_pose(phase, phase_progress, timeline_progress_global, -1, 0.0)
            pose = camera_pose_for_target(target_pose)
            metrics = metrics_for_step(max(0, step_count - 1))
            stack_depth = resolve_stack_depth_budget(
                metrics.matrix_w, metrics.matrix_h, metrics.cube_size, step_count + 1
            )
            frames.append(
                FramePose(
                    frame_index=frame_index,
                    phase=phase,
                    phase_progress=phase_progress,
                    shot_index=-1,
                    shot_progress=0.0,
                    timeline_progress_global=timeline_progress_global,
                    shots_total=shots_total,
                    pose=pose,
                    focus_z=0.0,
                    depth_budget=stack_depth,
                )
            )
            continue

        replay_start = gate_frame_count + reveal_frames
        if replay is not None and frame_index >= replay_start:
            local_replay_frame = frame_index - replay_start
            metrics = metrics_for_step(max(0, step_count - 1))
            stack_depth = resolve_stack_depth_budget(
                metrics.matrix_w, metrics.matrix_h, metrics.cube_size, step_count + 1
            )

            if local_replay_frame < pullback_frames:
                phase_progress = (
                    1.0
                    if pullback_frames <= 1
                    else clamp(
                        local_replay_frame / float(max(1, pullback_frames - 1)),
                        0.0,
                        1.0,
                    )
                )
                phase = "shot_camera_pullback"
                shot_index = -1
                shot_progress = 0.0
            elif local_replay_frame < pullback_frames + stack_frames_total:
                stack_frame = local_replay_frame - pullback_frames
                phase = "shot_stack"
                shot_index = min(shots_total - 1, stack_frame // extended_per_shot)
                shot_local = stack_frame - shot_index * extended_per_shot
                shot_progress = (
                    1.0
                    if extended_per_shot <= 1
                    else clamp(
                        shot_local / float(max(1, extended_per_shot - 1)),
                        0.0,
                        1.0,
                    )
                )
                phase_progress = shot_progress
            elif (
                local_replay_frame
                < pullback_frames + stack_frames_total + project_transition_frames
            ):
                transition_frame = local_replay_frame - pullback_frames - stack_frames_total
                phase = "shot_histogram_project"
                shot_index = -1
                shot_progress = 0.0
                phase_progress = (
                    1.0
                    if project_transition_frames <= 1
                    else clamp(
                        transition_frame / float(max(1, project_transition_frames - 1)),
                        0.0,
                        1.0,
                    )
                )
            else:
                project_frame = (
                    local_replay_frame
                    - pullback_frames
                    - stack_frames_total
                    - project_transition_frames
                )
                phase = "shot_histogram_project"
                shot_index = min(shots_total - 1, project_frame // extended_per_shot)
                shot_local = project_frame - shot_index * extended_per_shot
                shot_progress = (
                    1.0
                    if extended_per_shot <= 1
                    else clamp(
                        shot_local / float(max(1, extended_per_shot - 1)),
                        0.0,
                        1.0,
                    )
                )
                phase_progress = shot_progress

            target_pose = resolve_pose(
                phase, phase_progress, timeline_progress_global, shot_index, shot_progress
            )
            pose = camera_pose_for_target(target_pose)
            provisional = FramePose(
                frame_index=frame_index,
                phase=phase,
                phase_progress=phase_progress,
                shot_index=shot_index,
                shot_progress=shot_progress,
                timeline_progress_global=timeline_progress_global,
                shots_total=shots_total,
                pose=pose,
                focus_z=0.0,
                depth_budget=0.0,
            )
            focus_z = resolve_focus_z(provisional, metrics)
            depth_frame = FramePose(
                frame_index=frame_index,
                phase=phase,
                phase_progress=phase_progress,
                shot_index=shot_index,
                shot_progress=shot_progress,
                timeline_progress_global=timeline_progress_global,
                shots_total=shots_total,
                pose=pose,
                focus_z=focus_z,
                depth_budget=0.0,
            )
            frames.append(
                FramePose(
                    frame_index=frame_index,
                    phase=phase,
                    phase_progress=phase_progress,
                    shot_index=shot_index,
                    shot_progress=shot_progress,
                    timeline_progress_global=timeline_progress_global,
                    shots_total=shots_total,
                    pose=pose,
                    focus_z=focus_z,
                    depth_budget=max(
                        stack_depth, resolve_replay_depth_budget(depth_frame, metrics)
                    ),
                )
            )
            continue

        gate_frame = min(max(0, frame_index), max(0, gate_frame_count - 1))
        step_index = min(max(0, step_count - 1), gate_frame // frames_per_step)
        local_frame = gate_frame - step_index * frames_per_step
        step = steps[step_index]
        windows = normalize_phase_windows(step.get("phase_windows", []), frames_per_step)
        active_window = active_phase_window(local_frame, windows)
        phase = active_window.phase
        phase_frames = max(1, active_window.end_frame - active_window.start_frame)
        phase_progress = (
            1.0
            if phase_frames <= 1
            else clamp(
                (local_frame - active_window.start_frame) / float(max(1, phase_frames - 1)),
                0.0,
                1.0,
            )
        )
        target_pose = resolve_pose(phase, phase_progress, timeline_progress_global, -1, 0.0)
        pose = camera_pose_for_target(target_pose)
        metrics = metrics_for_step(step_index)
        stack_depth = resolve_stack_depth_budget(
            metrics.matrix_w, metrics.matrix_h, metrics.cube_size, step_index + 2
        )
        frames.append(
            FramePose(
                frame_index=frame_index,
                phase=phase,
                phase_progress=phase_progress,
                shot_index=-1,
                shot_progress=0.0,
                timeline_progress_global=timeline_progress_global,
                shots_total=shots_total,
                pose=pose,
                focus_z=0.0,
                depth_budget=stack_depth,
            )
        )

    return frames


def max_transition_jump(frames: list[FramePose], from_phase: str, to_phase: str) -> float:
    """Return the maximum transition jump.

    Args:
        frames: Input value for this computation.
        from_phase: Input value for this computation.
        to_phase: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    max_jump = 0.0
    for idx in range(1, len(frames)):
        prev = frames[idx - 1]
        cur = frames[idx]
        if prev.phase != from_phase or cur.phase != to_phase:
            continue
        max_jump = max(max_jump, pose_delta(prev.pose, cur.pose))
    return max_jump


def max_projection_lock_entry_seam_jump(frames: list[FramePose]) -> float:
    """Return the maximum projection lock entry seam jump.

    Args:
        frames: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    max_jump = 0.0
    for idx in range(1, len(frames)):
        prev = frames[idx - 1]
        cur = frames[idx]
        if (
            prev.phase == "shot_histogram_project"
            and prev.shot_index < 0
            and cur.phase == "shot_histogram_project"
            and cur.shot_index >= 0
        ):
            max_jump = max(max_jump, pose_delta(prev.pose, cur.pose))
    return max_jump


def validate_replay_focus_and_depth(frames: list[FramePose], trace: dict[str, Any]) -> list[str]:
    """Validate replay focus and depth.

    Args:
        frames: Input value for this computation.
        trace: Input value for this computation.

    Returns:
        The computed list value.
    """
    failures: list[str] = []
    metrics_by_step = resolve_step_metrics(trace)
    fallback = StepMetrics(rows=4, cols=4, matrix_w=320.0, matrix_h=320.0, cube_size=52.0)

    prev_project_distance: float | None = None
    stack_depth_reference: float | None = None
    prev_projection_lock_pose: tuple[float, float, float, float, float, float] | None = None
    prev_projection_lock_distance: float | None = None
    projection_lock_streak = 0
    for frame in frames:
        if frame.phase not in {"shot_camera_pullback", "shot_stack", "shot_histogram_project"}:
            continue
        metrics = metrics_by_step.get(max(0, len(trace.get("steps", [])) - 1), fallback)

        expected_focus = resolve_focus_z(frame, metrics)
        if abs(frame.focus_z - expected_focus) > FOCUS_TOL:
            failures.append(
                f"frame {frame.frame_index}: focus_z mismatch {frame.focus_z:.6f} != expected {expected_focus:.6f}"
            )

        expected_depth = max(
            resolve_stack_depth_budget(
                metrics.matrix_w,
                metrics.matrix_h,
                metrics.cube_size,
                max(1, len(trace.get("steps", [])) + 1),
            ),
            resolve_replay_depth_budget(frame, metrics),
        )
        if abs(frame.depth_budget - expected_depth) > max(DEPTH_TOL, expected_depth * 1e-4):
            failures.append(
                f"frame {frame.frame_index}: depth_budget mismatch {frame.depth_budget:.6f} != expected {expected_depth:.6f}"
            )

        if frame.phase == "shot_stack":
            if stack_depth_reference is None:
                stack_depth_reference = expected_depth
            elif abs(expected_depth - stack_depth_reference) > max(
                DEPTH_TOL, expected_depth * 1e-4
            ):
                failures.append(
                    "frame "
                    f"{frame.frame_index}: shot_stack depth budget changed with stack head "
                    f"({expected_depth:.6f} != {stack_depth_reference:.6f})"
                )

        if frame.phase == "shot_histogram_project" and frame.shot_index < 0:
            hist_focus = shot_replay_histogram_front_z(metrics)
            dist_to_hist = abs(hist_focus - frame.focus_z)
            if (
                prev_project_distance is not None
                and dist_to_hist > prev_project_distance + FOCUS_TOL
            ):
                failures.append(
                    f"frame {frame.frame_index}: project transition focus regressed away from histogram"
                )
            prev_project_distance = dist_to_hist
        else:
            prev_project_distance = None

        if is_projection_shot_lock_phase(frame.phase, frame.shot_index):
            solved_distance = resolve_solved_distance(frame, metrics)
            projection_lock_streak += 1
            lock_settled = projection_lock_streak > PROJECTION_LOCK_ACQUIRE_FRAMES
            if lock_settled and prev_projection_lock_pose is not None:
                delta_pose = pose_delta(prev_projection_lock_pose, frame.pose)
                if delta_pose > PROJECTION_LOCK_POSE_TOL:
                    failures.append(
                        "frame "
                        f"{frame.frame_index}: projection-shot lock pose drifted "
                        f"({delta_pose:.6f} > {PROJECTION_LOCK_POSE_TOL:.6f})"
                    )
            if lock_settled and prev_projection_lock_distance is not None:
                delta_distance = abs(solved_distance - prev_projection_lock_distance)
                if delta_distance > PROJECTION_LOCK_DISTANCE_TOL:
                    failures.append(
                        "frame "
                        f"{frame.frame_index}: projection-shot solved distance drifted "
                        f"({delta_distance:.6f} > {PROJECTION_LOCK_DISTANCE_TOL:.6f})"
                    )
            prev_projection_lock_pose = frame.pose
            prev_projection_lock_distance = solved_distance
        else:
            prev_projection_lock_pose = None
            prev_projection_lock_distance = None
            projection_lock_streak = 0

    return failures


def main() -> int:
    """Run the script entry point.

    Returns:
        The computed integer value.
    """
    parser = argparse.ArgumentParser(
        description="Validate camera continuity for Processing viewer traces."
    )
    parser.add_argument("--trace", default="viewer/processing_qave/data/trace.json")
    parser.add_argument("--max-pre-apply", type=float, default=0.08)
    parser.add_argument("--max-apply-settle", type=float, default=0.08)
    parser.add_argument("--max-step-boundary", type=float, default=0.08)
    parser.add_argument("--min-step-start-delta", type=float, default=0.00)
    parser.add_argument("--max-step-start-delta", type=float, default=1.20)
    parser.add_argument("--max-adjacent-jump", type=float, default=4.50)
    parser.add_argument("--max-seam-jump", type=float, default=0.005)
    parser.add_argument("--max-reveal-pullback", type=float, default=0.20)
    parser.add_argument("--max-pullback-project", type=float, default=2.50)
    parser.add_argument("--max-project-stack", type=float, default=0.20)
    parser.add_argument("--min-rotate-x", type=float, default=-0.35)
    parser.add_argument("--max-rotate-x", type=float, default=0.35)
    parser.add_argument("--min-rotate-z", type=float, default=-0.40)
    parser.add_argument("--max-rotate-z", type=float, default=0.40)
    parser.add_argument("--min-occupancy-w", type=float, default=0.30)
    parser.add_argument("--max-occupancy-w", type=float, default=0.34)
    parser.add_argument("--min-occupancy-h", type=float, default=0.479)
    parser.add_argument("--max-occupancy-h", type=float, default=0.56)
    args = parser.parse_args()

    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    frames = reconstruct_frame_poses(trace)

    failures: list[str] = []
    if not frames:
        failures.append("no frames reconstructed")

    # Core replay transition jumps for the new order.
    reveal_pullback = max_transition_jump(frames, "measurement_reveal", "shot_camera_pullback")
    pullback_stack = max_transition_jump(frames, "shot_camera_pullback", "shot_stack")
    stack_project = max_transition_jump(frames, "shot_stack", "shot_histogram_project")
    projection_lock_entry_seam = max_projection_lock_entry_seam_jump(frames)
    max_adjacent = max(
        (pose_delta(frames[idx - 1].pose, frames[idx].pose) for idx in range(1, len(frames))),
        default=0.0,
    )

    if reveal_pullback > args.max_reveal_pullback:
        failures.append(
            f"measurement_reveal->shot_camera_pullback jump {reveal_pullback:.6f} > {args.max_reveal_pullback:.6f}"
        )
    if pullback_stack > args.max_pullback_project:
        failures.append(
            f"shot_camera_pullback->shot_stack jump {pullback_stack:.6f} > {args.max_pullback_project:.6f}"
        )
    if stack_project > args.max_project_stack:
        failures.append(
            f"shot_stack->shot_histogram_project jump {stack_project:.6f} > {args.max_project_stack:.6f}"
        )
    if projection_lock_entry_seam > args.max_seam_jump:
        failures.append(
            "shot_histogram_project lock-entry seam jump "
            f"{projection_lock_entry_seam:.6f} > {args.max_seam_jump:.6f}"
        )
    if max_adjacent > args.max_adjacent_jump:
        failures.append(f"max adjacent jump {max_adjacent:.6f} > {args.max_adjacent_jump:.6f}")

    focus_depth_failures = validate_replay_focus_and_depth(frames, trace)
    failures.extend(focus_depth_failures)

    gate_frames = [frame for frame in frames if frame.phase in {"pre_gate", "apply_gate", "settle"}]
    pose_source = gate_frames if gate_frames else frames
    rotate_x_values = [frame.pose[0] for frame in pose_source]
    rotate_z_values = [frame.pose[2] for frame in pose_source]
    min_rx = min(rotate_x_values) if rotate_x_values else 0.0
    max_rx = max(rotate_x_values) if rotate_x_values else 0.0
    min_rz = min(rotate_z_values) if rotate_z_values else 0.0
    max_rz = max(rotate_z_values) if rotate_z_values else 0.0

    if min_rx < args.min_rotate_x or max_rx > args.max_rotate_x:
        failures.append(
            f"rotateX range [{min_rx:.6f}, {max_rx:.6f}] outside [{args.min_rotate_x:.6f}, {args.max_rotate_x:.6f}]"
        )
    if min_rz < args.min_rotate_z or max_rz > args.max_rotate_z:
        failures.append(
            f"rotateZ range [{min_rz:.6f}, {max_rz:.6f}] outside [{args.min_rotate_z:.6f}, {args.max_rotate_z:.6f}]"
        )

    print(f"trace={trace_path}")
    print(f"frames_reconstructed={len(frames)}")
    print(
        f"max_jump measurement_reveal->shot_camera_pullback: {reveal_pullback:.6f} (threshold {args.max_reveal_pullback:.6f})"
    )
    print(
        f"max_jump shot_camera_pullback->shot_stack: {pullback_stack:.6f} (threshold {args.max_pullback_project:.6f})"
    )
    print(
        f"max_jump shot_stack->shot_histogram_project: {stack_project:.6f} (threshold {args.max_project_stack:.6f})"
    )
    print(
        "max_jump shot_histogram_project lock-entry seam: "
        f"{projection_lock_entry_seam:.6f} (threshold {args.max_seam_jump:.6f})"
    )
    print(f"max_adjacent_frame_jump: {max_adjacent:.6f} (threshold {args.max_adjacent_jump:.6f})")
    print(f"gate pose rotateX range: min={min_rx:.6f}, max={max_rx:.6f}")
    print(f"gate pose rotateZ range: min={min_rz:.6f}, max={max_rz:.6f}")
    print(f"replay_focus_depth_failures: {len(focus_depth_failures)}")

    if failures:
        print(f"FAILED checks={len(failures)}")
        for item in failures[:20]:
            print(f"- {item}")
        if len(failures) > 20:
            print(f"- ... {len(failures) - 20} more")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
