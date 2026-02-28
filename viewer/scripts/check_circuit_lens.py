#!/usr/bin/env python3
"""Validate deterministic Qiskit-style circuit-lens mapping for viewer traces."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_FPS = 60.0
WINDOW_WIDTH = 1600.0
PANEL_MARGIN = 6.0
CIRCUIT_LENS_INSET_WIDTH_MIN = 260.0
CIRCUIT_LENS_INSET_WIDTH_MAX = 620.0
CIRCUIT_LENS_PADDING = 8.0
CIRCUIT_LENS_LABEL_LANE_SMALL = 30.0
CIRCUIT_LENS_LABEL_LANE_LARGE = 36.0
CIRCUIT_LENS_GATE_PITCH_PX = 36.0
CIRCUIT_LENS_ACTIVE_ANCHOR_RATIO = 0.50
EPS = 1e-6


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
    """

    frame_index: int
    step_index: int
    local_frame: int
    phase: str
    step_progress: float
    phase_progress: float


@dataclass(frozen=True)
class GateSpec:
    """Represent GateSpec data.

    Attributes:
        step_index: Stored value for this data container.
        gate_token: Stored value for this data container.
        raw_gate_name: Stored value for this data container.
        operation_id: Stored value for this data container.
        qubits: Stored value for this data container.
        control_qubits: Stored value for this data container.
        target_qubits: Stored value for this data container.
        render_kind: Stored value for this data container.
    """

    step_index: int
    gate_token: str
    raw_gate_name: str
    operation_id: str
    qubits: tuple[int, ...]
    control_qubits: tuple[int, ...]
    target_qubits: tuple[int, ...]
    render_kind: str


@dataclass(frozen=True)
class LensLayout:
    """Represent LensLayout data.

    Attributes:
        lane_left: Stored value for this data container.
        lane_right: Stored value for this data container.
        lane_width: Stored value for this data container.
        pitch: Stored value for this data container.
        content_span: Stored value for this data container.
        max_offset: Stored value for this data container.
    """

    lane_left: float
    lane_right: float
    lane_width: float
    pitch: float
    content_span: float
    max_offset: float


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
    replay_project_frames = 0
    replay_stack_frames = 0
    if replay is not None:
        timeline = replay.get("timeline", {})
        replay_pullback_frames = max(1, int(timeline.get("camera_pullback_frames", 36)))
        replay_project_frames = max(1, int(timeline.get("histogram_project_frames", 60)))
        replay_stack_frames = max(1, int(replay.get("shots_total", 0))) * max(
            1, int(timeline.get("frames_per_shot", 6))
        )
    total_frames = (
        gate_frame_count
        + reveal_frames
        + replay_pullback_frames
        + replay_project_frames
        + replay_stack_frames
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
                else clamp(
                    reveal_frame / float(max(1, reveal_frames - 1)),
                    0.0,
                    1.0,
                )
            )
            frames.append(
                FrameState(
                    frame_index=frame_index,
                    step_index=max(0, step_count - 1),
                    local_frame=max(0, frames_per_step - 1),
                    phase="measurement_reveal",
                    step_progress=1.0,
                    phase_progress=phase_progress,
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
                    )
                )
                continue

            if local_replay_frame < replay_pullback_frames + replay_project_frames:
                project_frame = local_replay_frame - replay_pullback_frames
                phase_progress = (
                    1.0
                    if replay_project_frames <= 1
                    else clamp(
                        project_frame / float(max(1, replay_project_frames - 1)),
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
                    )
                )
                continue

            timeline = replay.get("timeline", {})
            frames_per_shot_replay = max(1, int(timeline.get("frames_per_shot", 6)))
            stack_frame = local_replay_frame - replay_pullback_frames - replay_project_frames
            shot_local_frame = stack_frame % frames_per_shot_replay
            shot_progress = (
                1.0
                if frames_per_shot_replay <= 1
                else clamp(
                    shot_local_frame / float(max(1, frames_per_shot_replay - 1)),
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
            )
        )
    return frames, step_count


def parse_gate_label(operation_id: str) -> str:
    """Parse gate label.

    Args:
        operation_id: Input value for this computation.

    Returns:
        The computed string value.
    """
    if not operation_id:
        return "GATE"
    parts = operation_id.split("_")
    if not parts:
        return operation_id.upper()
    return parts[-1].upper()


def first_gate_matrix(step: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first gate matrix.

    Args:
        step: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    for sample in step.get("evolution_samples", []):
        gate_matrix = sample.get("gate_matrix")
        if isinstance(gate_matrix, dict):
            return gate_matrix
    return None


def unique_ordered_qubits(values: list[Any] | tuple[Any, ...] | None) -> tuple[int, ...]:
    """Return unique ordered qubits.

    Args:
        values: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    if not values:
        return tuple()
    out: list[int] = []
    for item in values:
        try:
            qubit = int(item)
        except (TypeError, ValueError):
            continue
        if qubit < 0:
            continue
        if qubit not in out:
            out.append(qubit)
    return tuple(out)


def merge_qubit_lists(
    primary: tuple[int, ...],
    secondary: tuple[int, ...],
) -> tuple[int, ...]:
    """Merge qubit lists.

    Args:
        primary: Input value for this computation.
        secondary: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    merged: list[int] = []
    for source in (primary, secondary):
        for qubit in source:
            if qubit < 0:
                continue
            if qubit not in merged:
                merged.append(qubit)
    return tuple(merged)


def compact_gate_token(raw_gate_name: str, operation_id: str) -> str:
    """Compact gate token.

    Args:
        raw_gate_name: Input value for this computation.
        operation_id: Input value for this computation.

    Returns:
        The computed string value.
    """
    source = raw_gate_name if raw_gate_name else operation_id
    if not source:
        return "U"
    normalized = "".join(ch if ch.isalnum() else " " for ch in source.upper()).strip()
    if not normalized:
        return "U"
    token = normalized.split()[0]
    return token[:4] if token else "U"


def normalize_gate_name(name: str) -> str:
    """Normalize gate name.

    Args:
        name: Input value for this computation.

    Returns:
        The computed string value.
    """
    if not name:
        return ""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def is_measure_gate(name: str) -> bool:
    """Return whether measure gate.

    Args:
        name: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    return name in {"measure", "m"}


def is_reset_gate(name: str) -> bool:
    """Return whether reset gate.

    Args:
        name: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    return name == "reset"


def is_single_control_pair_gate(name: str) -> bool:
    """Return whether single control pair gate.

    Args:
        name: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    if not name:
        return False
    if name in {"cx", "cy", "cz", "ch", "cp", "crx", "cry", "crz", "cnot"}:
        return True
    return name.startswith("cu")


def infer_gate_spec(step_index: int, step: dict[str, Any]) -> GateSpec:
    """Infer gate spec.

    Args:
        step_index: Input value for this computation.
        step: Input value for this computation.

    Returns:
        The computed value.
    """
    operation_id = str(step.get("operation_id", f"step_{step_index}"))
    gate_label = parse_gate_label(operation_id)
    operation_name = str(step.get("operation_name", ""))
    operation_qubits = unique_ordered_qubits(step.get("operation_qubits"))
    operation_controls = unique_ordered_qubits(step.get("operation_controls"))
    operation_targets = unique_ordered_qubits(step.get("operation_targets"))
    gate_matrix = first_gate_matrix(step)
    raw_gate_name = ""
    qubits: tuple[int, ...] = tuple()
    if gate_matrix is not None:
        raw_gate_name = str(gate_matrix.get("gate_name", ""))
        qubits = unique_ordered_qubits(gate_matrix.get("qubits"))

    if not raw_gate_name and operation_name:
        raw_gate_name = operation_name
    if not raw_gate_name:
        raw_gate_name = gate_label or operation_id

    if not qubits:
        qubits = (
            operation_qubits
            if operation_qubits
            else merge_qubit_lists(operation_controls, operation_targets)
        )

    normalized = normalize_gate_name(raw_gate_name)
    gate_token = compact_gate_token(raw_gate_name, operation_id)

    render_kind = "idle_unknown"
    controls: tuple[int, ...] = tuple()
    targets: tuple[int, ...] = tuple()

    if is_measure_gate(normalized) or is_reset_gate(normalized):
        render_kind = "measure"
        targets = operation_targets if operation_targets else qubits
    elif not qubits:
        render_kind = "idle_unknown"
    elif normalized in {"cswap", "fredkin"}:
        if len(qubits) >= 3:
            render_kind = "swap"
            controls = (qubits[0],)
            targets = (qubits[1], qubits[2])
        elif len(qubits) >= 2:
            render_kind = "swap"
            targets = (qubits[0], qubits[1])
        else:
            render_kind = "single"
            targets = qubits
    elif normalized == "swap":
        if len(qubits) >= 2:
            render_kind = "swap"
            targets = (qubits[0], qubits[1])
        else:
            render_kind = "single"
            targets = qubits
    elif normalized == "ccx":
        if len(qubits) >= 3:
            render_kind = "control_target"
            controls = (qubits[0], qubits[1])
            targets = (qubits[-1],)
        else:
            render_kind = "generic_multi"
            targets = qubits
    elif is_single_control_pair_gate(normalized):
        if len(qubits) >= 2:
            render_kind = "control_target"
            controls = (qubits[0],)
            targets = (qubits[1],)
        else:
            render_kind = "generic_multi"
            targets = qubits
    elif len(qubits) == 1:
        render_kind = "single"
        targets = qubits
    else:
        render_kind = "generic_multi"
        targets = qubits

    return GateSpec(
        step_index=step_index,
        gate_token=gate_token,
        raw_gate_name=raw_gate_name,
        operation_id=operation_id,
        qubits=qubits,
        control_qubits=controls,
        target_qubits=targets,
        render_kind=render_kind,
    )


def build_gate_specs(trace: dict[str, Any]) -> list[GateSpec]:
    """Build gate specs.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed list value.
    """
    steps = trace.get("steps", [])
    return [infer_gate_spec(index, step) for index, step in enumerate(steps)]


def infer_qubit_count(trace: dict[str, Any], specs: list[GateSpec]) -> int:
    """Infer qubit count.

    Args:
        trace: Input value for this computation.
        specs: Input value for this computation.

    Returns:
        The computed integer value.
    """
    max_qubit = -1
    for spec in specs:
        for qubit in spec.qubits:
            max_qubit = max(max_qubit, qubit)

    if max_qubit >= 0:
        return max(1, max_qubit + 1)

    steps = trace.get("steps", [])
    best_span = -1
    best_max_qubit = -1
    for step in steps:
        for sample in step.get("evolution_samples", []):
            for block in sample.get("reduced_density_blocks", []):
                qubits = unique_ordered_qubits(block.get("qubits"))
                if not qubits:
                    continue
                span = len(qubits)
                qmax = max(qubits)
                if span > best_span:
                    best_span = span
                    best_max_qubit = qmax
                elif span == best_span:
                    best_max_qubit = max(best_max_qubit, qmax)
    if best_max_qubit < 0:
        return 1
    return max(1, best_max_qubit + 1)


def build_lens_layout(step_count: int, qubit_count: int) -> LensLayout:
    """Build lens layout.

    Args:
        step_count: Input value for this computation.
        qubit_count: Input value for this computation.

    Returns:
        The computed value.
    """
    panel_w = WINDOW_WIDTH - PANEL_MARGIN * 2.0
    panel_x = PANEL_MARGIN
    inset_x = panel_x + 14.0
    inset_w = clamp(panel_w * 0.30, CIRCUIT_LENS_INSET_WIDTH_MIN, CIRCUIT_LENS_INSET_WIDTH_MAX)
    label_lane_w = (
        CIRCUIT_LENS_LABEL_LANE_LARGE if qubit_count >= 10 else CIRCUIT_LENS_LABEL_LANE_SMALL
    )
    lane_left = inset_x + CIRCUIT_LENS_PADDING + label_lane_w
    lane_right = inset_x + inset_w - CIRCUIT_LENS_PADDING
    lane_width = max(1.0, lane_right - lane_left)
    pitch = CIRCUIT_LENS_GATE_PITCH_PX
    content_span = max(0.0, float(max(0, step_count - 1)) * pitch)
    max_offset = max(0.0, content_span - lane_width)
    return LensLayout(
        lane_left=lane_left,
        lane_right=lane_right,
        lane_width=lane_width,
        pitch=pitch,
        content_span=content_span,
        max_offset=max_offset,
    )


def resolve_scroll_offset(layout: LensLayout, active_index: int) -> tuple[float, float, float]:
    """Resolve scroll offset.

    Args:
        layout: Input value for this computation.
        active_index: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    anchor_x = layout.lane_width * CIRCUIT_LENS_ACTIVE_ANCHOR_RATIO
    target_offset = active_index * layout.pitch - anchor_x
    scroll_offset = clamp(target_offset, 0.0, layout.max_offset)
    active_x = layout.lane_left + active_index * layout.pitch - scroll_offset
    return target_offset, scroll_offset, active_x


def validate_layout_policy(
    trace: dict[str, Any],
    frames: list[FrameState],
    step_count: int,
    specs: list[GateSpec],
) -> list[str]:
    """Validate layout policy.

    Args:
        trace: Input value for this computation.
        frames: Input value for this computation.
        step_count: Input value for this computation.
        specs: Input value for this computation.

    Returns:
        The computed list value.
    """
    failures: list[str] = []
    qubit_count = infer_qubit_count(trace, specs)
    layout = build_lens_layout(step_count, qubit_count)

    if abs(layout.pitch - CIRCUIT_LENS_GATE_PITCH_PX) > EPS:
        failures.append(
            f"layout pitch drifted from fixed value: got {layout.pitch:.6f}, expected {CIRCUIT_LENS_GATE_PITCH_PX:.6f}"
        )

    if step_count > 1:
        expected_span = float(step_count - 1) * CIRCUIT_LENS_GATE_PITCH_PX
        if abs(layout.content_span - expected_span) > EPS:
            failures.append(
                f"content span mismatch: got {layout.content_span:.6f}, expected {expected_span:.6f}"
            )

    expected_center_x = layout.lane_left + layout.lane_width * CIRCUIT_LENS_ACTIVE_ANCHOR_RATIO
    last_scroll_offset = -1.0
    offsets_by_step: dict[int, float] = {}

    for frame in frames:
        active_index = int(clamp(frame.step_index, 0, max(0, step_count - 1)))
        target_offset, scroll_offset, active_x = resolve_scroll_offset(layout, active_index)

        if scroll_offset < -EPS or scroll_offset > layout.max_offset + EPS:
            failures.append(
                f"frame {frame.frame_index}: scroll_offset {scroll_offset:.6f} out of [0,{layout.max_offset:.6f}]"
            )

        if last_scroll_offset >= 0.0 and scroll_offset + EPS < last_scroll_offset:
            failures.append(
                f"frame {frame.frame_index}: scroll_offset decreased from {last_scroll_offset:.6f} to {scroll_offset:.6f}"
            )
        last_scroll_offset = scroll_offset

        prior = offsets_by_step.get(active_index)
        if prior is None:
            offsets_by_step[active_index] = scroll_offset
        elif abs(prior - scroll_offset) > EPS:
            failures.append(
                f"frame {frame.frame_index}: step {active_index} offset changed across frames ({prior:.6f} vs {scroll_offset:.6f})"
            )

        edge_clamped = scroll_offset <= EPS or scroll_offset >= layout.max_offset - EPS
        if layout.max_offset > EPS and not edge_clamped:
            if abs(active_x - expected_center_x) > 1e-3:
                failures.append(
                    f"frame {frame.frame_index}: active gate not centered in overflow window "
                    f"(x={active_x:.6f}, expected={expected_center_x:.6f}, target_offset={target_offset:.6f})"
                )

        if active_x < layout.lane_left - EPS or active_x > layout.lane_right + EPS:
            failures.append(
                f"frame {frame.frame_index}: active gate x={active_x:.6f} outside lane [{layout.lane_left:.6f},{layout.lane_right:.6f}]"
            )

    return failures


def phase_color_name(phase: str) -> str:
    """Resolve phase color name.

    Args:
        phase: Input value for this computation.

    Returns:
        The computed string value.
    """
    if phase == "pre_gate":
        return "pre"
    if phase == "apply_gate":
        return "apply"
    if phase == "settle":
        return "settle"
    if phase == "measurement_reveal":
        return "reveal"
    if phase == "shot_camera_pullback":
        return "shot_pullback"
    if phase == "shot_histogram_project":
        return "shot_project"
    if phase == "shot_stack":
        return "shot_stack"
    return "other"


def build_frame_signature(frame: FrameState, step_count: int, active_spec: GateSpec) -> str:
    """Build frame signature.

    Args:
        frame: Input value for this computation.
        step_count: Input value for this computation.
        active_spec: Input value for this computation.

    Returns:
        The computed string value.
    """
    active_index = int(clamp(frame.step_index, 0, max(0, step_count - 1)))
    progress = clamp(frame.phase_progress, 0.0, 1.0)
    return (
        f"{frame.frame_index}:"
        f"step={active_index}:"
        f"phase={phase_color_name(frame.phase)}:"
        f"progress={progress:.6f}:"
        f"kind={active_spec.render_kind}:"
        f"token={active_spec.gate_token}"
    )


def validate_gate_specs(step_count: int, specs: list[GateSpec]) -> list[str]:
    """Validate gate specs.

    Args:
        step_count: Input value for this computation.
        specs: Input value for this computation.

    Returns:
        The computed list value.
    """
    failures: list[str] = []
    if len(specs) != step_count:
        failures.append(f"gate-spec count mismatch: specs={len(specs)} steps={step_count}")
    for index, spec in enumerate(specs):
        if spec.step_index != index:
            failures.append(
                f"gate-spec index mismatch: list_index={index} spec.step_index={spec.step_index}"
            )
    return failures


def validate_inference_sanity(specs: list[GateSpec]) -> list[str]:
    """Validate inference sanity.

    Args:
        specs: Input value for this computation.

    Returns:
        The computed list value.
    """
    failures: list[str] = []

    cx_specs = [spec for spec in specs if normalize_gate_name(spec.raw_gate_name) == "cx"]
    for spec in cx_specs:
        if not (
            spec.render_kind == "control_target"
            and len(spec.control_qubits) == 1
            and len(spec.target_qubits) == 1
        ):
            failures.append(
                f"step {spec.step_index}: cx inference expected 1 control + 1 target, got "
                f"kind={spec.render_kind} controls={spec.control_qubits} targets={spec.target_qubits}"
            )

    cswap_specs = [
        spec for spec in specs if normalize_gate_name(spec.raw_gate_name) in {"cswap", "fredkin"}
    ]
    for spec in cswap_specs:
        if not (
            spec.render_kind == "swap"
            and len(spec.control_qubits) == 1
            and len(spec.target_qubits) == 2
        ):
            failures.append(
                f"step {spec.step_index}: cswap/fredkin inference expected 1 control + 2 swap targets, got "
                f"kind={spec.render_kind} controls={spec.control_qubits} targets={spec.target_qubits}"
            )

    return failures


def validate_measurement_target_mapping(
    steps: list[dict[str, Any]],
    specs: list[GateSpec],
) -> list[str]:
    """Validate measurement target mapping.

    Args:
        steps: Input value for this computation.
        specs: Input value for this computation.

    Returns:
        The computed list value.
    """
    failures: list[str] = []
    for step_index, (step, spec) in enumerate(zip(steps, specs, strict=False)):
        operation_name = normalize_gate_name(str(step.get("operation_name", "")))
        operation_targets = unique_ordered_qubits(step.get("operation_targets"))
        if (
            (is_measure_gate(operation_name) or is_reset_gate(operation_name))
            and operation_targets
            and spec.render_kind == "measure"
            and not spec.target_qubits
        ):
            failures.append(
                f"step {step_index}: measurement/reset spec lost target mapping "
                f"(operation_targets={operation_targets})"
            )
    return failures


def validate_circuit_lens(trace: dict[str, Any]) -> tuple[list[str], list[str], int]:
    """Validate circuit lens.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["trace.steps must be a non-empty list"], [], 0

    frames, step_count = collect_frame_states(trace)
    specs = build_gate_specs(trace)
    failures: list[str] = []
    signatures: list[str] = []

    failures.extend(validate_gate_specs(step_count, specs))
    failures.extend(validate_inference_sanity(specs))
    failures.extend(validate_measurement_target_mapping(steps, specs))
    failures.extend(validate_layout_policy(trace, frames, step_count, specs))

    for frame in frames:
        active_index = int(clamp(frame.step_index, 0, max(0, step_count - 1)))
        if active_index != frame.step_index:
            failures.append(
                f"frame {frame.frame_index}: active index {active_index} differs from step_index {frame.step_index}"
            )

        if not (0.0 <= frame.phase_progress <= 1.0):
            failures.append(
                f"frame {frame.frame_index}: phase_progress {frame.phase_progress:.6f} outside [0,1]"
            )

        if frame.phase not in {
            "pre_gate",
            "apply_gate",
            "settle",
            "measurement_reveal",
            "shot_camera_pullback",
            "shot_histogram_project",
            "shot_stack",
        }:
            failures.append(f"frame {frame.frame_index}: unexpected phase '{frame.phase}'")

        if active_index < 0 or active_index >= len(specs):
            failures.append(
                f"frame {frame.frame_index}: active index {active_index} has no gate spec"
            )
            continue

        active_specs = [spec for spec in specs if spec.step_index == active_index]
        if len(active_specs) != 1:
            failures.append(
                f"frame {frame.frame_index}: expected exactly one active gate column for step {active_index}, got {len(active_specs)}"
            )
            continue

        signatures.append(build_frame_signature(frame, step_count, active_specs[0]))

    return failures, signatures, len(frames)


def main() -> int:
    """Run the script entry point.

    Returns:
        The computed integer value.
    """
    parser = argparse.ArgumentParser(
        description="Validate deterministic circuit-lens mapping from trace JSON."
    )
    parser.add_argument("--trace", default="viewer/processing_qave/data/trace.json")
    args = parser.parse_args()

    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))

    failures_a, signatures_a, frame_count = validate_circuit_lens(trace)
    failures_b, signatures_b, _ = validate_circuit_lens(trace)
    failures = list(failures_a)

    if failures_b:
        failures.append("second validation pass produced failures")
        failures.extend(f"second pass: {item}" for item in failures_b[:10])
    if signatures_a != signatures_b:
        failures.append(
            "determinism failure: circuit-lens signatures differ across repeated reconstruction runs"
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
