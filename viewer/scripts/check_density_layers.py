#!/usr/bin/env python3
"""Validate layered density-stack mapping for Processing viewer traces.

Note: shot-replay qubit fixed-slot stacking is validated in replay-specific checks.
This checker validates density-layer ordering, including projection-prep hold on the
final stacked measured shot state.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_FPS = 60.0
VIEWPORT_W = 1600.0
VIEWPORT_H = 960.0
PANEL_MARGIN = 6.0
HUD_RESERVED_BOTTOM = 8.0
RAW_DETAIL_MAX_DIM = 8

RENDER_MODE_RAW = "raw"
INIT_LAYER_STEP_INDEX = -1
INIT_LAYER_PHASE = "pre_gate"
SYNTHETIC_GROUND_HASH = "synthetic_ground"
STACK_DEPTH_STEP_MULT = 0.62
STACK_DEPTH_STEP_MIN = 12.0
STACK_DEPTH_STEP_MAX = 48.0
STACK_NO_OVERLAP_MULT = 0.96
STACK_NO_OVERLAP_MARGIN = 1.0
LAYER_SCALE_DECAY_PER_AGE = 0.012
CUBE_PITCH_FILL_RATIO = 0.90
NON_OVERLAP_EPS = 1e-6


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
class FrameState:
    """Represent FrameState data.

    Attributes:
        frame_index: Stored value for this data container.
        step_index: Stored value for this data container.
        local_frame: Stored value for this data container.
        phase: Stored value for this data container.
        step_progress: Stored value for this data container.
        phase_progress: Stored value for this data container.
        shot_index: Stored value for this data container.
        shot_progress: Stored value for this data container.
    """

    frame_index: int
    step_index: int
    local_frame: int
    phase: str
    step_progress: float
    phase_progress: float
    shot_index: int
    shot_progress: float


@dataclass(frozen=True)
class LayerFrame:
    """Represent LayerFrame data.

    Attributes:
        step_index: Stored value for this data container.
        age: Stored value for this data container.
        is_active: Stored value for this data container.
        state_hash: Stored value for this data container.
    """

    step_index: int
    age: int
    is_active: bool
    state_hash: str


@dataclass(frozen=True)
class StepSettle:
    """Represent StepSettle data.

    Attributes:
        state_hash: Stored value for this data container.
        block: Stored value for this data container.
    """

    state_hash: str
    block: dict[str, Any] | None


@dataclass(frozen=True)
class ViewGeometry:
    """Represent ViewGeometry data.

    Attributes:
        rows: Stored value for this data container.
        cols: Stored value for this data container.
        pitch: Stored value for this data container.
        cube_size: Stored value for this data container.
    """

    rows: int
    cols: int
    pitch: float
    cube_size: float


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


def resolve_density_render_mode(full_dim: int) -> str:
    """Resolve density render mode.

    Args:
        full_dim: Input value for this computation.

    Returns:
        The computed string value.
    """
    _ = full_dim
    return RENDER_MODE_RAW


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

    windows.sort(key=lambda item: item.start_frame)
    first = windows[0]
    windows[0] = PhaseWindow(first.phase, 0, first.end_frame)
    last = windows[-1]
    windows[-1] = PhaseWindow(last.phase, last.start_frame, frames_per_step)

    fixed: list[PhaseWindow] = [windows[0]]
    for window in windows[1:]:
        prev = fixed[-1]
        start_frame = max(window.start_frame, prev.start_frame)
        end_frame = window.end_frame
        if end_frame <= start_frame:
            end_frame = min(frames_per_step, start_frame + 1)
        fixed.append(PhaseWindow(window.phase, start_frame, end_frame))

    return fixed


def phase_at_frame(local_frame: int, windows: list[PhaseWindow]) -> str:
    """Resolve phase at frame.

    Args:
        local_frame: Input value for this computation.
        windows: Input value for this computation.

    Returns:
        The computed string value.
    """
    for window in windows:
        if local_frame >= window.start_frame and local_frame < window.end_frame:
            return window.phase
    if not windows:
        return "apply_gate"
    return windows[-1].phase


def active_phase_window(local_frame: int, windows: list[PhaseWindow]) -> PhaseWindow | None:
    """Compute active phase window.

    Args:
        local_frame: Input value for this computation.
        windows: Input value for this computation.

    Returns:
        The computed value.
    """
    if not windows:
        return None
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


def collect_frame_states(trace: dict[str, Any]) -> tuple[list[FrameState], int]:
    """Collect frame states.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    steps = trace.get("steps", [])
    step_count = len(steps)
    default_step_duration_ms = float(
        trace.get("timeline", {}).get("default_step_duration_ms", 800.0)
    )
    frame_duration_ms = 1000.0 / TARGET_FPS
    frames_per_step = max(1, int(round(default_step_duration_ms / frame_duration_ms)))
    gate_frame_count = max(1, step_count * frames_per_step)
    reveal_frames = 48 if has_measurement_reveal(trace) else 0
    replay = measurement_shot_replay(trace)
    replay_pullback_frames = 0
    replay_stack_frames = 0
    replay_project_transition_frames = 0
    replay_project_frames = 0
    replay_shots_total = 0
    replay_frames_per_shot = 0
    if replay is not None:
        timeline = replay.get("timeline", {})
        replay_shots_total = max(1, int(replay.get("shots_total", 0)))
        base_frames_per_shot = max(1, int(timeline.get("frames_per_shot", 6)))
        replay_frames_per_shot = base_frames_per_shot + 2
        replay_pullback_frames = max(1, int(timeline.get("camera_pullback_frames", 36)))
        replay_stack_frames = replay_shots_total * replay_frames_per_shot
        replay_project_transition_frames = max(1, int(timeline.get("histogram_project_frames", 60)))
        replay_project_frames = replay_shots_total * replay_frames_per_shot
    total_frames = (
        gate_frame_count
        + reveal_frames
        + replay_pullback_frames
        + replay_stack_frames
        + replay_project_transition_frames
        + replay_project_frames
    )

    frames: list[FrameState] = []
    for frame_index in range(total_frames):
        if (
            reveal_frames > 0
            and frame_index >= gate_frame_count
            and frame_index < gate_frame_count + reveal_frames
        ):
            reveal_frame = frame_index - gate_frame_count
            phase_progress = (
                1.0
                if reveal_frames <= 1
                else clamp(reveal_frame / float(max(1, reveal_frames - 1)), 0.0, 1.0)
            )
            frames.append(
                FrameState(
                    frame_index=frame_index,
                    step_index=max(0, step_count - 1),
                    local_frame=max(0, frames_per_step - 1),
                    phase="measurement_reveal",
                    step_progress=1.0,
                    phase_progress=phase_progress,
                    shot_index=-1,
                    shot_progress=0.0,
                )
            )
            continue
        replay_start = gate_frame_count + reveal_frames
        if replay is not None and frame_index >= replay_start:
            local_replay_frame = frame_index - replay_start
            if local_replay_frame < replay_pullback_frames:
                phase_progress = (
                    1.0
                    if replay_pullback_frames <= 1
                    else clamp(
                        local_replay_frame / float(max(1, replay_pullback_frames - 1)),
                        0.0,
                        1.0,
                    )
                )
                frames.append(
                    FrameState(
                        frame_index=frame_index,
                        step_index=max(0, step_count - 1),
                        local_frame=max(0, frames_per_step - 1),
                        phase="shot_camera_pullback",
                        step_progress=1.0,
                        phase_progress=phase_progress,
                        shot_index=-1,
                        shot_progress=0.0,
                    )
                )
                continue

            if local_replay_frame < replay_pullback_frames + replay_stack_frames:
                stack_frame = local_replay_frame - replay_pullback_frames
                shot_index = min(
                    max(0, replay_shots_total - 1), stack_frame // replay_frames_per_shot
                )
                shot_local_frame = stack_frame - shot_index * replay_frames_per_shot
                shot_progress = (
                    1.0
                    if replay_frames_per_shot <= 1
                    else clamp(
                        shot_local_frame / float(max(1, replay_frames_per_shot - 1)),
                        0.0,
                        1.0,
                    )
                )
                frames.append(
                    FrameState(
                        frame_index=frame_index,
                        step_index=max(0, step_count - 1),
                        local_frame=max(0, frames_per_step - 1),
                        phase="shot_stack",
                        step_progress=1.0,
                        phase_progress=shot_progress,
                        shot_index=shot_index,
                        shot_progress=shot_progress,
                    )
                )
                continue

            if (
                local_replay_frame
                < replay_pullback_frames + replay_stack_frames + replay_project_transition_frames
            ):
                transition_frame = local_replay_frame - replay_pullback_frames - replay_stack_frames
                phase_progress = (
                    1.0
                    if replay_project_transition_frames <= 1
                    else clamp(
                        transition_frame / float(max(1, replay_project_transition_frames - 1)),
                        0.0,
                        1.0,
                    )
                )
                frames.append(
                    FrameState(
                        frame_index=frame_index,
                        step_index=max(0, step_count - 1),
                        local_frame=max(0, frames_per_step - 1),
                        phase="shot_histogram_project",
                        step_progress=1.0,
                        phase_progress=phase_progress,
                        shot_index=-1,
                        shot_progress=0.0,
                    )
                )
                continue

            project_frame = (
                local_replay_frame
                - replay_pullback_frames
                - replay_stack_frames
                - replay_project_transition_frames
            )
            shot_index = min(
                max(0, replay_shots_total - 1), project_frame // replay_frames_per_shot
            )
            shot_local_frame = project_frame - shot_index * replay_frames_per_shot
            shot_progress = (
                1.0
                if replay_frames_per_shot <= 1
                else clamp(
                    shot_local_frame / float(max(1, replay_frames_per_shot - 1)),
                    0.0,
                    1.0,
                )
            )
            frames.append(
                FrameState(
                    frame_index=frame_index,
                    step_index=max(0, step_count - 1),
                    local_frame=max(0, frames_per_step - 1),
                    phase="shot_histogram_project",
                    step_progress=1.0,
                    phase_progress=shot_progress,
                    shot_index=shot_index,
                    shot_progress=shot_progress,
                )
            )
            continue

        gate_frame = min(max(0, frame_index), max(0, gate_frame_count - 1))
        step_index = min(max(0, step_count - 1), gate_frame // frames_per_step)
        local_frame = gate_frame - step_index * frames_per_step
        step = steps[step_index]
        windows = normalize_phase_windows(step.get("phase_windows", []), frames_per_step)
        phase = phase_at_frame(local_frame, windows)
        active_window = active_phase_window(local_frame, windows)

        step_progress = 0.0
        if frames_per_step > 1:
            step_progress = clamp(local_frame / float(frames_per_step - 1), 0.0, 1.0)

        phase_progress = step_progress
        if active_window is not None:
            phase_frames = max(0, active_window.end_frame - active_window.start_frame)
            if phase_frames <= 1:
                phase_progress = 1.0
            else:
                phase_progress = clamp(
                    (local_frame - active_window.start_frame) / float(max(1, phase_frames - 1)),
                    0.0,
                    1.0,
                )

        frames.append(
            FrameState(
                frame_index=frame_index,
                step_index=step_index,
                local_frame=local_frame,
                phase=phase,
                step_progress=step_progress,
                phase_progress=phase_progress,
                shot_index=-1,
                shot_progress=0.0,
            )
        )

    return frames, step_count


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
    for row in range(len(real)):
        if not isinstance(real[row], list) or not isinstance(imag[row], list):
            return False
        if len(real[row]) != cols or len(imag[row]) != cols:
            return False
    return True


def block_qubit_key(block: dict[str, Any]) -> str:
    """Compute block qubit key.

    Args:
        block: Input value for this computation.

    Returns:
        The computed string value.
    """
    qubits = block.get("qubits") or []
    if not isinstance(qubits, list):
        return ""
    return ",".join(str(item) for item in qubits)


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
        qubits = block.get("qubits") or []
        span = len(qubits) if isinstance(qubits, list) else 0
        if span > largest_span:
            largest_span = span
            largest = block
    if largest is not None:
        return largest

    for block in blocks:
        if isinstance(block, dict) and block_qubit_key(block) == "0,1":
            return block
    for block in blocks:
        if isinstance(block, dict) and block_qubit_key(block) == "0":
            return block
    return blocks[0] if isinstance(blocks[0], dict) else None


def resolve_nearest_evolution_sample(
    step: dict[str, Any], t_normalized: float, phase: str
) -> dict[str, Any] | None:
    """Resolve nearest evolution sample.

    Args:
        step: Input value for this computation.
        t_normalized: Input value for this computation.
        phase: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    samples = step.get("evolution_samples") or []
    if not isinstance(samples, list) or not samples:
        return None

    best = None
    best_score = float("inf")
    for candidate in samples:
        if not isinstance(candidate, dict):
            continue
        candidate_phase = str(candidate.get("phase", ""))
        phase_penalty = 0.0 if candidate_phase == phase else 1.0
        candidate_t = float(candidate.get("t_normalized", 0.0))
        score = phase_penalty * 2.0 + abs(candidate_t - t_normalized)
        if best is None or score < best_score:
            best = candidate
            best_score = score

    return best


def resolve_settle_sample(step: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve settle sample.

    Args:
        step: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    samples = step.get("evolution_samples") or []
    if not isinstance(samples, list) or not samples:
        return None
    latest_settle = None
    for sample in samples:
        if isinstance(sample, dict) and str(sample.get("phase", "")) == "settle":
            latest_settle = sample
    if latest_settle is not None:
        return latest_settle
    for sample in reversed(samples):
        if isinstance(sample, dict):
            return sample
    return None


def resolve_layer_window_cap(active_block: dict[str, Any] | None) -> int:
    """Resolve layer window cap.

    Args:
        active_block: Input value for this computation.

    Returns:
        The computed integer value.
    """
    if active_block is None:
        return 0
    real = active_block.get("real")
    imag = active_block.get("imag")
    if not is_rectangular(real, imag):
        return 0
    return 2**31 - 1


def resolve_display_dims(rows: int, cols: int) -> tuple[int, int, str, int]:
    """Resolve display dims.

    Args:
        rows: Input value for this computation.
        cols: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    full_dim = max(rows, cols)
    return rows, cols, resolve_density_render_mode(full_dim), full_dim


def resolve_view_geometry(rows: int, cols: int) -> ViewGeometry:
    """Resolve view geometry.

    Args:
        rows: Input value for this computation.
        cols: Input value for this computation.

    Returns:
        The computed value.
    """
    panel_w = VIEWPORT_W - PANEL_MARGIN * 2.0
    panel_h = max(280.0, VIEWPORT_H - PANEL_MARGIN * 2.0 - HUD_RESERVED_BOTTOM)

    target_matrix_w = clamp(panel_w * 0.58, panel_w * 0.55, panel_w * 0.62)
    target_matrix_h = clamp(panel_h * 0.34, panel_h * 0.30, panel_h * 0.38)
    pad_w = max(18.0, panel_w * 0.03)
    pad_h = max(14.0, panel_h * 0.04)

    max_stage_w = max(32.0, panel_w - pad_w * 2.0)
    max_stage_h = max(32.0, panel_h - pad_h * 2.0)
    desired_w = min(target_matrix_w, max_stage_w)
    desired_h = min(target_matrix_h, max_stage_h)

    pitch_w = desired_w / max(1.0, float(cols))
    pitch_h = desired_h / max(1.0, float(rows))
    pitch = clamp(min(pitch_w, pitch_h), 30.0, 170.0)
    cube_size = max(8.0, pitch * CUBE_PITCH_FILL_RATIO)
    return ViewGeometry(rows=rows, cols=cols, pitch=pitch, cube_size=cube_size)


def resolve_stack_depth_budget(geometry: ViewGeometry, layer_count: int) -> float:
    """Resolve stack depth budget.

    Args:
        geometry: Input value for this computation.
        layer_count: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    depth_step = resolve_guaranteed_depth_step(geometry.cube_size)
    depth_span = depth_step * max(0.0, float(layer_count - 1))
    return max(44.0, depth_span + geometry.cube_size * 0.9)


def resolve_base_stack_depth_step(cube_size: float) -> float:
    """Resolve base stack depth step.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    safe_cube = max(0.0, cube_size)
    return clamp(safe_cube * STACK_DEPTH_STEP_MULT, STACK_DEPTH_STEP_MIN, STACK_DEPTH_STEP_MAX)


def resolve_conservative_no_overlap_gap(cube_size: float) -> float:
    """Resolve conservative no overlap gap.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    safe_cube = max(0.0, cube_size)
    side_a = safe_cube * max(0.72, 1.0 - 0.0 * LAYER_SCALE_DECAY_PER_AGE)
    side_b = safe_cube * max(0.72, 1.0 - 1.0 * LAYER_SCALE_DECAY_PER_AGE)
    return (side_a + side_b) * 0.5 + STACK_NO_OVERLAP_MARGIN


def resolve_guaranteed_depth_step(cube_size: float) -> float:
    """Resolve guaranteed depth step.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    safe_cube = max(0.0, cube_size)
    base_step = resolve_base_stack_depth_step(safe_cube)
    no_overlap_step = safe_cube * STACK_NO_OVERLAP_MULT + STACK_NO_OVERLAP_MARGIN
    conservative_gap = resolve_conservative_no_overlap_gap(safe_cube)
    return max(base_step, no_overlap_step, conservative_gap)


def resolve_stage_visibility(
    layers: list[LayerFrame], geometry: ViewGeometry
) -> tuple[float, float]:
    """Resolve stage visibility.

    Args:
        layers: Input value for this computation.
        geometry: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    if not layers:
        return -0.18, float("inf")

    depth_step = resolve_guaranteed_depth_step(geometry.cube_size)
    min_back_z = float("inf")
    for layer in layers:
        age = max(0, layer.age)
        attenuation = clamp(1.0 - age * LAYER_SCALE_DECAY_PER_AGE, 0.72, 1.0)
        cube_side = geometry.cube_size * 0.92 * attenuation
        center_z = 1.10 + cube_side * 0.5 - age * depth_step
        back_z = center_z - cube_side * 0.5 - 2.0
        min_back_z = min(min_back_z, back_z)

    if min_back_z == float("inf"):
        return -0.18, min_back_z
    plane_z = min(-0.18, min_back_z - 1.5)
    return plane_z, min_back_z


def build_settle_map(steps: list[dict[str, Any]]) -> dict[int, StepSettle]:
    """Build settle map.

    Args:
        steps: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    settle_map: dict[int, StepSettle] = {}
    for index, step in enumerate(steps):
        settle = resolve_settle_sample(step)
        block = (
            select_preferred_block(settle.get("reduced_density_blocks"))
            if settle is not None
            else None
        )
        state_hash = str(settle.get("state_hash", "")) if settle is not None else ""
        settle_map[index] = StepSettle(state_hash=state_hash, block=block)
    return settle_map


def resolve_initial_layer_state_hash(steps: list[dict[str, Any]]) -> str:
    """Resolve initial layer state hash.

    Args:
        steps: Input value for this computation.

    Returns:
        The computed string value.
    """
    if not steps:
        return SYNTHETIC_GROUND_HASH
    first = steps[0]
    boundary = (
        first.get("boundary_checkpoint")
        if isinstance(first.get("boundary_checkpoint"), dict)
        else {}
    )
    gate_start_hash = str(boundary.get("gate_start_hash", ""))
    if gate_start_hash:
        return gate_start_hash

    samples = first.get("evolution_samples") or []
    if isinstance(samples, list):
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            state_hash = str(sample.get("state_hash", ""))
            if state_hash:
                return state_hash

    gate_end_hash = str(boundary.get("gate_end_hash", ""))
    if gate_end_hash:
        return gate_end_hash
    return SYNTHETIC_GROUND_HASH


def can_build_synthetic_ground_block(active_block: dict[str, Any]) -> bool:
    """Return whether build synthetic ground block.

    Args:
        active_block: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    real = active_block.get("real")
    imag = active_block.get("imag")
    return is_rectangular(real, imag)


def should_render_active_gate_layer(frame: FrameState) -> bool:
    """Return whether render active gate layer.

    Args:
        frame: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    return not (frame.step_index == 0 and frame.phase == "pre_gate")


def resolve_replay_hold_sample(
    steps: list[dict[str, Any]],
    replay: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Resolve replay hold sample.

    Args:
        steps: Input value for this computation.
        replay: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    if not steps:
        return None
    if replay is None:
        return resolve_settle_sample(steps[-1])
    source_step_index = int(replay.get("source_step_index", len(steps) - 1))
    source_step_index = max(0, min(len(steps) - 1, source_step_index))
    return resolve_settle_sample(steps[source_step_index])


def resolve_replay_state_for_event(
    replay: dict[str, Any] | None,
    shot_index: int,
) -> tuple[dict[str, Any] | None, str]:
    """Resolve replay state for event.

    Args:
        replay: Input value for this computation.
        shot_index: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    if replay is None or shot_index < 0:
        return None, ""

    events = replay.get("shot_events")
    if not isinstance(events, list) or not events:
        return None, ""
    event_idx = max(0, min(len(events) - 1, shot_index))
    event = events[event_idx] if isinstance(events[event_idx], dict) else None
    if event is None:
        return None, ""

    event_hash = str(event.get("state_hash", ""))
    event_label = str(event.get("outcome_label", ""))
    outcome_states = replay.get("outcome_states")
    if not isinstance(outcome_states, list):
        return None, event_hash

    fallback_match = None
    for state in outcome_states:
        if not isinstance(state, dict):
            continue
        state_hash = str(state.get("state_hash", ""))
        state_label = str(state.get("label", ""))
        if event_hash and state_hash == event_hash:
            block = select_preferred_block(state.get("reduced_density_blocks"))
            return block, state_hash
        if fallback_match is None and event_label and state_label == event_label:
            fallback_match = state

    if isinstance(fallback_match, dict):
        block = select_preferred_block(fallback_match.get("reduced_density_blocks"))
        return block, str(fallback_match.get("state_hash", event_hash))
    return None, event_hash


def resolve_layers_for_frame(
    steps: list[dict[str, Any]],
    frame: FrameState,
    settle_map: dict[int, StepSettle],
    init_state_hash: str,
    replay: dict[str, Any] | None,
) -> tuple[list[LayerFrame], int, int, str, ViewGeometry | None, str, int]:
    """Resolve layers for frame.

    Args:
        steps: Input value for this computation.
        frame: Input value for this computation.
        settle_map: Input value for this computation.
        init_state_hash: Input value for this computation.
        replay: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    step = steps[frame.step_index]

    active_sample = None
    active_block = None
    active_hash = ""
    if frame.phase == "measurement_reveal":
        active_sample = resolve_settle_sample(step)
        active_block = (
            select_preferred_block(active_sample.get("reduced_density_blocks"))
            if active_sample is not None
            else None
        )
        active_hash = str(active_sample.get("state_hash", "")) if active_sample is not None else ""
    elif frame.phase in {"shot_camera_pullback", "shot_histogram_project", "shot_stack"}:
        hold_sample = resolve_replay_hold_sample(steps, replay)
        if hold_sample is not None:
            active_sample = hold_sample
            active_block = select_preferred_block(hold_sample.get("reduced_density_blocks"))
            active_hash = str(hold_sample.get("state_hash", ""))
        replay_shot_index = -1
        if frame.phase == "shot_stack" or (
            frame.phase == "shot_histogram_project" and frame.shot_index >= 0
        ):
            replay_shot_index = frame.shot_index
        elif frame.phase == "shot_histogram_project":
            replay_shot_index = int((replay or {}).get("shots_total", 0)) - 1
        if replay_shot_index >= 0:
            replay_block, replay_hash = resolve_replay_state_for_event(replay, replay_shot_index)
            if replay_block is not None:
                active_block = replay_block
            if replay_hash:
                active_hash = replay_hash
    else:
        active_sample = resolve_nearest_evolution_sample(step, frame.step_progress, frame.phase)
        active_block = (
            select_preferred_block(active_sample.get("reduced_density_blocks"))
            if active_sample is not None
            else None
        )
        active_hash = str(active_sample.get("state_hash", "")) if active_sample is not None else ""

    show_active = should_render_active_gate_layer(frame)
    available_layers = frame.step_index + (2 if show_active else 1)
    if active_block is None:
        return [], 0, available_layers, active_hash, None, RENDER_MODE_RAW, 0

    real = active_block.get("real")
    imag = active_block.get("imag")
    if not is_rectangular(real, imag):
        return [], 0, available_layers, active_hash, None, RENDER_MODE_RAW, 0

    rows = len(real)
    cols = len(real[0])
    display_rows, display_cols, render_mode, full_dim = resolve_display_dims(rows, cols)
    geometry = resolve_view_geometry(display_rows, display_cols)
    layer_cap = available_layers
    start_step = 0
    layers: list[LayerFrame] = []
    if can_build_synthetic_ground_block(active_block):
        init_age = max(0, frame.step_index - INIT_LAYER_STEP_INDEX - (0 if show_active else 1))
        layers.append(
            LayerFrame(
                step_index=INIT_LAYER_STEP_INDEX,
                age=init_age,
                is_active=False,
                state_hash=init_state_hash,
            )
        )
    for step_index in range(start_step, frame.step_index + 1):
        age = frame.step_index - step_index
        is_active = step_index == frame.step_index
        if is_active:
            if not show_active:
                continue
            layers.append(
                LayerFrame(
                    step_index=step_index,
                    age=age,
                    is_active=True,
                    state_hash=active_hash,
                )
            )
            continue

        settled = settle_map.get(step_index)
        if settled is None or settled.block is None:
            continue
        settled_real = settled.block.get("real")
        settled_imag = settled.block.get("imag")
        if not is_rectangular(settled_real, settled_imag):
            continue
        if len(settled_real) != rows or len(settled_real[0]) != cols:
            continue
        layers.append(
            LayerFrame(
                step_index=step_index,
                age=age,
                is_active=False,
                state_hash=settled.state_hash,
            )
        )

    return layers, layer_cap, available_layers, active_hash, geometry, render_mode, full_dim


def frame_signature(layers: list[LayerFrame]) -> str:
    """Build the frame signature.

    Args:
        layers: Input value for this computation.

    Returns:
        The computed string value.
    """
    return "|".join(
        f"{layer.step_index}:{1 if layer.is_active else 0}:{layer.state_hash}" for layer in layers
    )


def validate_layers(trace: dict[str, Any]) -> tuple[list[str], list[str], int]:
    """Validate layers.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["trace.steps must be a non-empty list"], [], 0

    frames, _ = collect_frame_states(trace)
    settle_map = build_settle_map(steps)
    init_state_hash = resolve_initial_layer_state_hash(steps)
    replay = measurement_shot_replay(trace)
    failures: list[str] = []
    signatures: list[str] = []

    for frame in frames:
        (
            layers,
            layer_cap,
            available_layers,
            active_hash,
            geometry,
            render_mode,
            full_dim,
        ) = resolve_layers_for_frame(steps, frame, settle_map, init_state_hash, replay)
        signatures.append(frame_signature(layers))

        show_active = should_render_active_gate_layer(frame)
        expected_available = frame.step_index + (2 if show_active else 1)
        if available_layers != expected_available:
            failures.append(
                f"frame {frame.frame_index}: available layer count mismatch ({available_layers} != {expected_available})"
            )
        if layer_cap != expected_available:
            failures.append(
                f"frame {frame.frame_index}: full-history layer cap mirror mismatch ({layer_cap} != {expected_available})"
            )
        if render_mode != RENDER_MODE_RAW:
            failures.append(
                f"frame {frame.frame_index}: render mode expected {RENDER_MODE_RAW}, got {render_mode}"
            )

        if geometry is not None:
            expected_history_steps: list[int] = []
            for step_index in range(0, frame.step_index):
                settled = settle_map.get(step_index)
                if settled is None or settled.block is None:
                    continue
                settled_real = settled.block.get("real")
                settled_imag = settled.block.get("imag")
                if not is_rectangular(settled_real, settled_imag):
                    continue
                if len(settled_real) != geometry.rows or len(settled_real[0]) != geometry.cols:
                    continue
                expected_history_steps.append(step_index)

            actual_history_steps = [
                layer.step_index
                for layer in layers
                if not layer.is_active and layer.step_index != INIT_LAYER_STEP_INDEX
            ]
            if actual_history_steps != expected_history_steps:
                failures.append(
                    "frame "
                    + f"{frame.frame_index}: historical step list mismatch "
                    + f"(actual={actual_history_steps}, expected={expected_history_steps})"
                )

            expected_visible_count = 1 + len(expected_history_steps) + (1 if show_active else 0)
            if len(layers) != expected_visible_count:
                failures.append(
                    "frame "
                    + f"{frame.frame_index}: visible layer count {len(layers)} "
                    + f"!= expected full-history count {expected_visible_count}"
                )

        active_layers = [layer for layer in layers if layer.is_active]
        if show_active:
            if len(active_layers) != 1:
                failures.append(
                    f"frame {frame.frame_index}: expected exactly one active layer, found {len(active_layers)}"
                )
                continue
            active_layer = active_layers[0]
            if active_layer.step_index != frame.step_index:
                failures.append(
                    f"frame {frame.frame_index}: active layer step {active_layer.step_index} != playback step {frame.step_index}"
                )
            if active_hash and active_layer.state_hash != active_hash:
                failures.append(
                    f"frame {frame.frame_index}: active layer hash {active_layer.state_hash} != expected {active_hash}"
                )
        elif active_layers:
            failures.append(
                f"frame {frame.frame_index}: expected no active layer in init-only phase, found {len(active_layers)}"
            )

        init_layers = [layer for layer in layers if layer.step_index == INIT_LAYER_STEP_INDEX]
        if len(init_layers) != 1:
            failures.append(
                f"frame {frame.frame_index}: expected one init layer at step {INIT_LAYER_STEP_INDEX}, found {len(init_layers)}"
            )
        else:
            init_layer = init_layers[0]
            if init_layer.is_active:
                failures.append(f"frame {frame.frame_index}: init layer must never be active")
            expected_init_age = max(
                0,
                frame.step_index - INIT_LAYER_STEP_INDEX - (0 if show_active else 1),
            )
            if init_layer.age != expected_init_age:
                failures.append(
                    f"frame {frame.frame_index}: init layer age {init_layer.age} != expected {expected_init_age}"
                )
            if init_state_hash and init_layer.state_hash != init_state_hash:
                failures.append(
                    f"frame {frame.frame_index}: init layer hash {init_layer.state_hash} != expected {init_state_hash}"
                )

        prev_index = INIT_LAYER_STEP_INDEX - 1
        for layer in layers:
            if layer.step_index <= prev_index:
                failures.append(
                    f"frame {frame.frame_index}: layer step indices are not strictly increasing"
                )
                break
            prev_index = layer.step_index

        if show_active and layers and layers[-1].step_index != frame.step_index:
            failures.append(
                f"frame {frame.frame_index}: final layer step {layers[-1].step_index} != active step {frame.step_index}"
            )

        for layer in layers:
            if layer.step_index == INIT_LAYER_STEP_INDEX:
                expected_age = max(
                    0,
                    frame.step_index - INIT_LAYER_STEP_INDEX - (0 if show_active else 1),
                )
            else:
                expected_age = frame.step_index - layer.step_index
            if layer.age != expected_age:
                failures.append(
                    f"frame {frame.frame_index}: layer step {layer.step_index} age {layer.age} != expected {expected_age}"
                )
            if layer.is_active:
                continue
            if layer.step_index == INIT_LAYER_STEP_INDEX:
                continue
            expected_settle_hash = (
                settle_map.get(layer.step_index).state_hash
                if layer.step_index in settle_map
                else ""
            )
            if expected_settle_hash and layer.state_hash != expected_settle_hash:
                failures.append(
                    "frame "
                    + f"{frame.frame_index}: historical layer step {layer.step_index} hash {layer.state_hash} "
                    + f"!= settle hash {expected_settle_hash}"
                )

        if geometry is not None and len(layers) > 1:
            plane_z, min_back_z = resolve_stage_visibility(layers, geometry)
            if min_back_z != float("inf") and plane_z >= min_back_z:
                failures.append(
                    "frame "
                    + f"{frame.frame_index}: stage plane occludes historical layer "
                    + f"(planeZ={plane_z:.4f} >= minBackZ={min_back_z:.4f})"
                )

            depth_step = resolve_guaranteed_depth_step(geometry.cube_size)
            age_ordered = sorted(layers, key=lambda layer: max(0, layer.age))
            for i in range(1, len(age_ordered)):
                prev_layer = age_ordered[i - 1]
                next_layer = age_ordered[i]
                prev_age = max(0, prev_layer.age)
                next_age = max(0, next_layer.age)

                prev_side = geometry.cube_size * max(
                    0.72, 1.0 - prev_age * LAYER_SCALE_DECAY_PER_AGE
                )
                next_side = geometry.cube_size * max(
                    0.72, 1.0 - next_age * LAYER_SCALE_DECAY_PER_AGE
                )
                required_gap = (prev_side + next_side) * 0.5 + NON_OVERLAP_EPS

                if depth_step + 1e-6 < required_gap:
                    failures.append(
                        "frame "
                        + f"{frame.frame_index}: non-overlap invariant failed for adjacent ages "
                        + f"{prev_age}->{next_age} "
                        + f"(depthStep={depth_step:.4f}, required={required_gap:.4f})"
                    )
                    break

    return failures, signatures, len(frames)


def main() -> int:
    """Run the script entry point.

    Returns:
        The computed integer value.
    """
    parser = argparse.ArgumentParser(
        description="Validate layered density mapping from trace JSON."
    )
    parser.add_argument("--trace", default="viewer/processing_qave/data/trace.json")
    args = parser.parse_args()

    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))

    failures_a, signatures_a, frame_count = validate_layers(trace)
    failures_b, signatures_b, _ = validate_layers(trace)
    failures = list(failures_a)
    if failures_b:
        failures.append("second validation pass produced failures")
        failures.extend(f"second pass: {item}" for item in failures_b[:10])
    if signatures_a != signatures_b:
        failures.append(
            "determinism failure: layer signatures differ across repeated reconstruction runs"
        )

    print(f"trace={trace_path}")
    print(f"frames_checked={frame_count}")
    print(f"signature_count={len(signatures_a)}")

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
