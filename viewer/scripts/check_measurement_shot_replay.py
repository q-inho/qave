#!/usr/bin/env python3
"""Validate deterministic measurement shot replay reconstruction from trace JSON.

Replay model validated here:
- shot_camera_pullback (camera move while density holds collapse state)
- shot_stack (physical qubit layers accumulate while density shows per-shot measured state)
- shot_histogram_project transition (camera move while density holds final stacked shot state)
- shot_histogram_project projection shots (histogram accumulates chronologically)
- deterministic per-shot responsible source-cell mapping
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_FPS = 60.0
EPS = 1e-6
COUNT_TOL = 1e-5
DEPTH_TOL = 1e-6
RELAY_FRONT_COMPLETE_MIN = 0.95
EMISSION_TRAVEL_START_MAX = 0.12
EMISSION_TRAVEL_COMPLETE_MIN = 0.95

# Hybrid soft-cap stack spacing (must match viewer runtime constants).
SHOT_STACK_SOFT_CAP_LINEAR_LAYERS = 24
SHOT_STACK_TAIL_COMPRESS_RATIO = 0.28
SHOT_STACK_DEPTH_BASE_MULT = 0.58
SHOT_STACK_DEPTH_BASE_MIN = 5.0
SHOT_STACK_DEPTH_BASE_MAX = 18.0
SHOT_QUBIT_CUBE_SIZE_RATIO = 0.64
SHOT_QUBIT_CUBE_MIN_SIZE = 8.0
SHOT_QUBIT_CUBE_MAX_SIZE = 26.0
SHOT_QUBIT_CUBOID_MIN_DEPTH = 2.0
SHOT_QUBIT_CUBOID_DEPTH_BLEND = 1.0
SHOT_QUBIT_STACK_DEPTH_MULTIPLIER = 1.5
SHOT_QUBIT_MIN_HIST_GAP = 14.0
SHOT_QUBIT_HIST_GAP_CUBE_MULT = 0.95
SHOT_REPLAY_LAYER_GAP_SCALE = 10.0
SHOT_EMISSION_MIN_PROBABILITY = 1e-6
SHOT_STACK_EXTRA_FRAMES = 4
SHOT_STACK_BEAT_LOCK_FRACTION = 0.15
SHOT_STACK_BEAT_EMIT_FRACTION = 0.35
SHOT_STACK_BEAT_COLLAPSE_FRACTION = 0.30
SHOT_STACK_BEAT_SETTLE_FRACTION = 0.20


@dataclass(frozen=True)
class ReplayFrame:
    """Represent ReplayFrame data.

    Attributes:
        frame_index: Stored value for this data container.
        phase: Stored value for this data container.
        phase_progress: Stored value for this data container.
        shot_index: Stored value for this data container.
        shot_progress: Stored value for this data container.
        shot_beat: Stored value for this data container.
        shot_beat_progress: Stored value for this data container.
        outcome_label: Stored value for this data container.
        state_hash: Stored value for this data container.
    """

    frame_index: int
    phase: str
    phase_progress: float
    shot_index: int
    shot_progress: float
    shot_beat: str
    shot_beat_progress: float
    outcome_label: str
    state_hash: str


@dataclass(frozen=True)
class ReplayBuild:
    """Represent ReplayBuild data.

    Attributes:
        frames: Stored value for this data container.
        shots_total: Stored value for this data container.
        pullback_frames: Stored value for this data container.
        base_frames_per_shot: Stored value for this data container.
        extended_frames_per_shot: Stored value for this data container.
        stack_frames_total: Stored value for this data container.
        project_transition_frames: Stored value for this data container.
        project_frames_total: Stored value for this data container.
        replay_start_frame: Stored value for this data container.
        hold_hash: Stored value for this data container.
        visual_source_hash: Stored value for this data container.
        shot_state_hash_by_shot: Stored value for this data container.
    """

    frames: list[ReplayFrame]
    shots_total: int
    pullback_frames: int
    base_frames_per_shot: int
    extended_frames_per_shot: int
    stack_frames_total: int
    project_transition_frames: int
    project_frames_total: int
    replay_start_frame: int
    hold_hash: str
    visual_source_hash: str
    shot_state_hash_by_shot: dict[int, str]


@dataclass(frozen=True)
class StepMetrics:
    """Represent StepMetrics data.

    Attributes:
        rows: Stored value for this data container.
        cols: Stored value for this data container.
        cube_size: Stored value for this data container.
    """

    rows: int
    cols: int
    cube_size: float


@dataclass(frozen=True)
class ShotSourceCellSignature:
    """Represent deterministic per-shot source-cell identity.

    Attributes:
        row: Stored value for this data container.
        col: Stored value for this data container.
        basis_index: Stored value for this data container.
        basis_label: Stored value for this data container.
        weight: Stored value for this data container.
        state_hash: Stored value for this data container.
        outcome_label: Stored value for this data container.
        block_key: Stored value for this data container.
    """

    row: int
    col: int
    basis_index: int
    basis_label: str
    weight: float
    state_hash: str
    outcome_label: str
    block_key: str


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


def ease_in_out_circ01(value: float) -> float:
    """Compute ease in out circ01.

    Args:
        value: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    x = clamp(value, 0.0, 1.0)
    if x < 0.5:
        return (1.0 - math.sqrt(max(0.0, 1.0 - (2.0 * x) ** 2))) * 0.5
    return (math.sqrt(max(0.0, 1.0 - (-2.0 * x + 2.0) ** 2)) + 1.0) * 0.5


def has_terminal_measurement(trace: dict[str, Any]) -> bool:
    """Return whether terminal measurement.

    Args:
        trace: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        return False
    last = steps[-1]
    measurement = last.get("measurement") if isinstance(last, dict) else None
    return isinstance(measurement, dict) and bool(measurement.get("is_measurement", False))


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


def resolve_settle_state_hash(step: dict[str, Any] | None) -> str:
    """Resolve settle state hash.

    Args:
        step: Input value for this computation.

    Returns:
        The computed string value.
    """
    if not isinstance(step, dict):
        return ""
    samples = step.get("evolution_samples")
    if isinstance(samples, list):
        settle_hash = ""
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            if str(sample.get("phase", "")) == "settle":
                settle_hash = str(sample.get("state_hash", ""))
        if settle_hash:
            return settle_hash
        for sample in reversed(samples):
            if isinstance(sample, dict):
                state_hash = str(sample.get("state_hash", ""))
                if state_hash:
                    return state_hash
    boundary = step.get("boundary_checkpoint")
    if isinstance(boundary, dict):
        return str(boundary.get("gate_end_hash", ""))
    return ""


def is_measurement_like_step(step: dict[str, Any] | None) -> bool:
    """Return whether a step is measurement-like.

    Args:
        step: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    if not isinstance(step, dict):
        return False
    measurement = step.get("measurement")
    if isinstance(measurement, dict) and bool(measurement.get("is_measurement", False)):
        return True
    op_name = str(step.get("operation_name", "")).lower()
    if op_name in {"measure", "measurement"}:
        return True
    op_id = str(step.get("operation_id", "")).lower()
    return "measure" in op_id


def resolve_visual_source_step_index(steps: list[dict[str, Any]], source_step_index: int) -> int:
    """Resolve visual replay source step index.

    Args:
        steps: Input value for this computation.
        source_step_index: Input value for this computation.

    Returns:
        The computed integer value.
    """
    if not steps:
        return -1
    clamped = max(0, min(len(steps) - 1, source_step_index))
    source_step = steps[clamped]
    if is_measurement_like_step(source_step) and clamped > 0:
        return clamped - 1
    return clamped


def resolve_visual_source_state_hash(
    steps: list[dict[str, Any]], source_step_index: int, hold_hash: str
) -> str:
    """Resolve visual replay source state hash.

    Args:
        steps: Input value for this computation.
        source_step_index: Input value for this computation.
        hold_hash: Input value for this computation.

    Returns:
        The computed string value.
    """
    visual_source_index = resolve_visual_source_step_index(steps, source_step_index)
    if visual_source_index < 0 or visual_source_index >= len(steps):
        return hold_hash
    visual_hash = resolve_settle_state_hash(steps[visual_source_index])
    return visual_hash if visual_hash else hold_hash


def resolve_outcome_state_for_event(
    replay: dict[str, Any], event: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Resolve replay outcome state object for an event.

    Args:
        replay: Input value for this computation.
        event: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    if not isinstance(event, dict):
        return None
    outcome_states = replay.get("outcome_states")
    if not isinstance(outcome_states, list) or not outcome_states:
        return None

    event_hash = str(event.get("state_hash", ""))
    if event_hash:
        for item in outcome_states:
            if not isinstance(item, dict):
                continue
            if str(item.get("state_hash", "")) == event_hash:
                return item

    event_label = str(event.get("outcome_label", ""))
    if event_label:
        for item in outcome_states:
            if not isinstance(item, dict):
                continue
            if str(item.get("label", "")) == event_label:
                return item
    return None


def resolve_event_state_hash(
    replay: dict[str, Any], event: dict[str, Any] | None, fallback_hash: str
) -> str:
    """Resolve runtime-equivalent event state hash.

    Args:
        replay: Input value for this computation.
        event: Input value for this computation.
        fallback_hash: Input value for this computation.

    Returns:
        The computed string value.
    """
    outcome_state = resolve_outcome_state_for_event(replay, event)
    if isinstance(outcome_state, dict):
        resolved_hash = str(outcome_state.get("state_hash", ""))
        if resolved_hash:
            return resolved_hash
    return fallback_hash


def resolve_outcome_state_for_hash(
    replay: dict[str, Any], state_hash: str
) -> dict[str, Any] | None:
    """Resolve replay outcome state object for a state hash.

    Args:
        replay: Input value for this computation.
        state_hash: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    outcome_states = replay.get("outcome_states")
    if not isinstance(outcome_states, list) or not outcome_states:
        return None
    safe_hash = str(state_hash or "")
    if not safe_hash:
        return None
    for item in outcome_states:
        if not isinstance(item, dict):
            continue
        if str(item.get("state_hash", "")) == safe_hash:
            return item
    return None


def resolve_outcome_state_for_label(
    replay: dict[str, Any], outcome_label: str
) -> dict[str, Any] | None:
    """Resolve replay outcome state object for an outcome label.

    Args:
        replay: Input value for this computation.
        outcome_label: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    outcome_states = replay.get("outcome_states")
    if not isinstance(outcome_states, list) or not outcome_states:
        return None
    safe_label = str(outcome_label or "")
    if not safe_label:
        return None
    for item in outcome_states:
        if not isinstance(item, dict):
            continue
        if str(item.get("label", "")) == safe_label:
            return item
    return None


def resolve_outcome_state_hash_for_label(replay: dict[str, Any], outcome_label: str) -> str:
    """Resolve configured outcome state hash for an outcome label.

    Args:
        replay: Input value for this computation.
        outcome_label: Input value for this computation.

    Returns:
        The computed string value.
    """
    safe_label = str(outcome_label or "")
    if not safe_label:
        return ""
    outcomes = replay.get("outcomes")
    if not isinstance(outcomes, list):
        return ""
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            continue
        if str(outcome.get("label", "")) == safe_label:
            return str(outcome.get("state_hash", ""))
    return ""


def resolve_preferred_outcome_block_for_label(
    replay: dict[str, Any], outcome_label: str
) -> dict[str, Any] | None:
    """Resolve preferred replay block for an outcome label using hash-first lookup.

    Args:
        replay: Input value for this computation.
        outcome_label: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    outcome_hash = resolve_outcome_state_hash_for_label(replay, outcome_label)
    replay_state = resolve_outcome_state_for_hash(replay, outcome_hash)
    if replay_state is None:
        replay_state = resolve_outcome_state_for_label(replay, outcome_label)
    if not isinstance(replay_state, dict):
        return None
    return select_preferred_block(replay_state.get("reduced_density_blocks"))


def density_block_signature(block: dict[str, Any] | None) -> tuple[int, int, str] | None:
    """Build deterministic block shape signature.

    Args:
        block: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    if not isinstance(block, dict):
        return None
    real = block.get("real")
    imag = block.get("imag")
    if not is_rectangular(real, imag):
        return None
    rows = len(real)
    cols = len(real[0]) if rows > 0 and isinstance(real[0], list) else 0
    if rows <= 0 or cols <= 0:
        return None
    return rows, cols, block_qubit_key(block)


def build_cumulative_counts_for_shot_index(
    replay: dict[str, Any],
    events: list[dict[str, Any]],
    shot_index: int,
) -> dict[str, int]:
    """Build cumulative outcome counts up to the given shot index.

    Args:
        replay: Input value for this computation.
        events: Input value for this computation.
        shot_index: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    counts: dict[str, int] = {}
    outcomes = replay.get("outcomes")
    if isinstance(outcomes, list):
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            label = str(outcome.get("label", ""))
            if label:
                counts[label] = 0
    if not events:
        return counts

    clamped = max(0, min(len(events) - 1, shot_index))
    for idx in range(clamped + 1):
        event = events[idx]
        if not isinstance(event, dict):
            continue
        label = str(event.get("outcome_label", ""))
        if not label:
            continue
        counts[label] = int(counts.get(label, 0)) + 1
    return counts


def build_cumulative_state_hash(shot_index: int, counts: dict[str, int]) -> str:
    """Build runtime-equivalent deterministic cumulative replay state hash.

    Args:
        shot_index: Input value for this computation.
        counts: Input value for this computation.

    Returns:
        The computed string value.
    """
    safe_shot = max(0, int(shot_index))
    if not counts:
        return f"shot_replay_cumulative:k={safe_shot}:empty"

    labels = sorted(str(label) for label in counts.keys())
    body = "|".join(f"{label}={max(0, int(counts.get(label, 0)))}" for label in labels)
    return f"shot_replay_cumulative:k={safe_shot}:{body}"


def resolve_cumulative_state_hash_for_shot(
    replay: dict[str, Any],
    events: list[dict[str, Any]],
    shot_index: int,
    fallback_hash: str,
) -> str:
    """Resolve runtime-equivalent cumulative replay state hash for shot index.

    Args:
        replay: Input value for this computation.
        events: Input value for this computation.
        shot_index: Input value for this computation.
        fallback_hash: Input value for this computation.

    Returns:
        The computed string value.
    """
    if not events:
        return fallback_hash
    clamped = max(0, min(len(events) - 1, int(shot_index)))
    counts = build_cumulative_counts_for_shot_index(replay, events, clamped)

    template_signature: tuple[int, int, str] | None = None
    has_weighted_block = False
    for label, count in counts.items():
        if int(count) <= 0:
            continue
        block = resolve_preferred_outcome_block_for_label(replay, label)
        signature = density_block_signature(block)
        if signature is None:
            event = events[clamped] if 0 <= clamped < len(events) else None
            return resolve_event_state_hash(replay, event, fallback_hash)
        if template_signature is None:
            template_signature = signature
        elif signature != template_signature:
            event = events[clamped] if 0 <= clamped < len(events) else None
            return resolve_event_state_hash(replay, event, fallback_hash)
        has_weighted_block = True

    if not has_weighted_block:
        event = events[clamped] if 0 <= clamped < len(events) else None
        return resolve_event_state_hash(replay, event, fallback_hash)
    return build_cumulative_state_hash(clamped, counts)


def format_basis_label(basis_index: int, width: int) -> str:
    """Format basis label string.

    Args:
        basis_index: Input value for this computation.
        width: Input value for this computation.

    Returns:
        The computed string value.
    """
    safe_width = max(1, width)
    safe_basis = max(0, basis_index)
    raw = format(safe_basis, "b")
    if len(raw) > safe_width:
        raw = raw[-safe_width:]
    return f"|{raw.zfill(safe_width)}>"


def block_qubit_key(block: dict[str, Any]) -> str:
    """Resolve deterministic block key for a reduced-density block.

    Args:
        block: Input value for this computation.

    Returns:
        The computed string value.
    """
    qubits = block.get("qubits") if isinstance(block, dict) else None
    if not isinstance(qubits, list) or not qubits:
        return ""
    values: list[str] = []
    for item in qubits:
        try:
            values.append(str(int(item)))
        except (TypeError, ValueError):
            values.append(str(item))
    return ",".join(values)


def resolve_diagonal_cell_coordinates(
    layout_rows: int,
    layout_cols: int,
    dim: int,
    basis_index: int,
) -> tuple[int, int]:
    """Resolve diagonal basis-cell coordinates under viewer mapping rules.

    Args:
        layout_rows: Input value for this computation.
        layout_cols: Input value for this computation.
        dim: Input value for this computation.
        basis_index: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    safe_rows = max(1, layout_rows)
    safe_cols = max(1, layout_cols)
    safe_dim = max(1, dim)
    safe_basis = max(0, min(safe_dim - 1, basis_index))
    if safe_dim == safe_rows and safe_dim == safe_cols:
        return safe_basis, safe_basis

    normalized = 0.0 if safe_dim <= 1 else safe_basis / float(max(1, safe_dim - 1))
    row = max(0, min(safe_rows - 1, int(round(normalized * max(0, safe_rows - 1)))))
    col = max(0, min(safe_cols - 1, int(round(normalized * max(0, safe_cols - 1)))))
    return row, col


def resolve_replay_responsible_source_cell_signature(
    replay: dict[str, Any],
    event: dict[str, Any] | None,
    layout_rows: int,
    layout_cols: int,
) -> ShotSourceCellSignature | None:
    """Resolve deterministic per-shot responsible source-cell signature.

    Args:
        replay: Input value for this computation.
        event: Input value for this computation.
        layout_rows: Input value for this computation.
        layout_cols: Input value for this computation.

    Returns:
        The computed value.
    """
    if not isinstance(event, dict):
        return None
    replay_state = resolve_outcome_state_for_event(replay, event)
    if not isinstance(replay_state, dict):
        return None

    block = select_preferred_block(replay_state.get("reduced_density_blocks"))
    if block is None:
        return None
    real = block.get("real")
    imag = block.get("imag")
    if not is_rectangular(real, imag):
        return None

    rows = len(real)
    cols = len(real[0]) if rows > 0 and isinstance(real[0], list) else 0
    dim = min(rows, cols)
    if dim <= 0:
        return None

    best_basis = -1
    best_weight = -1.0
    tie_eps = 1e-7
    for basis in range(dim):
        diagonal = max(0.0, float(real[basis][basis]))
        if diagonal > best_weight + tie_eps:
            best_basis = basis
            best_weight = diagonal
            continue
        if abs(diagonal - best_weight) <= tie_eps and (best_basis < 0 or basis < best_basis):
            best_basis = basis
            best_weight = diagonal
    if best_basis < 0:
        return None

    qubits = block.get("qubits")
    if isinstance(qubits, list) and qubits:
        width = len(qubits)
    else:
        width = max(1, int(round(math.log(max(1, dim), 2))))
    row, col = resolve_diagonal_cell_coordinates(layout_rows, layout_cols, dim, best_basis)
    state_hash = str(replay_state.get("state_hash", "")) or str(event.get("state_hash", ""))
    outcome_label = str(event.get("outcome_label", "")) or str(replay_state.get("label", ""))
    return ShotSourceCellSignature(
        row=row,
        col=col,
        basis_index=best_basis,
        basis_label=format_basis_label(best_basis, width),
        weight=max(SHOT_EMISSION_MIN_PROBABILITY, best_weight),
        state_hash=state_hash,
        outcome_label=outcome_label,
        block_key=block_qubit_key(block),
    )


def parse_replay(trace: dict[str, Any]) -> dict[str, Any] | None:
    """Parse replay.

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
    pullback = int(timeline.get("camera_pullback_frames", 0))
    project_transition = int(timeline.get("histogram_project_frames", 0))
    base_frames_per_shot = int(timeline.get("frames_per_shot", 0))
    events = replay.get("shot_events")
    outcomes = replay.get("outcomes")
    outcome_states = replay.get("outcome_states")
    if shots_total <= 0 or pullback <= 0 or project_transition <= 0 or base_frames_per_shot <= 0:
        return None
    if (
        not isinstance(events, list)
        or not isinstance(outcomes, list)
        or not isinstance(outcome_states, list)
    ):
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
        real = block.get("real")
        imag = block.get("imag")
        if not is_rectangular(real, imag):
            continue
        span = len(block.get("qubits") or [])
        if span > largest_span:
            largest = block
            largest_span = span
    return largest


def resolve_replay_step_metrics(trace: dict[str, Any], replay: dict[str, Any]) -> StepMetrics:
    """Resolve replay step metrics.

    Args:
        trace: Input value for this computation.
        replay: Input value for this computation.

    Returns:
        The computed value.
    """
    fallback = StepMetrics(rows=4, cols=4, cube_size=52.0)
    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        return fallback

    source_step_index = int(replay.get("source_step_index", len(steps) - 1))
    source_step_index = resolve_visual_source_step_index(steps, source_step_index)
    if source_step_index < 0 or source_step_index >= len(steps):
        return fallback
    step = steps[source_step_index]
    if not isinstance(step, dict):
        return fallback

    samples = step.get("evolution_samples")
    if not isinstance(samples, list):
        return fallback

    for sample in samples:
        if not isinstance(sample, dict):
            continue
        block = select_preferred_block(sample.get("reduced_density_blocks"))
        if block is None:
            continue
        real = block.get("real")
        imag = block.get("imag")
        if not is_rectangular(real, imag):
            continue
        rows = max(1, len(real))
        cols = max(1, len(real[0]))
        # Matches current Processing matrix cube-size path in checks.
        panel_w = 1600.0 - 12.0
        panel_h = max(280.0, 960.0 - 12.0 - 8.0)
        target_matrix_w = clamp(panel_w * 0.58, panel_w * 0.55, panel_w * 0.62)
        target_matrix_h = clamp(panel_h * 0.34, panel_h * 0.30, panel_h * 0.38)
        pitch_w = target_matrix_w / max(1.0, float(cols))
        pitch_h = target_matrix_h / max(1.0, float(rows))
        pitch = clamp(min(pitch_w, pitch_h), 30.0, 170.0)
        cube_size = max(8.0, pitch * 0.90)
        return StepMetrics(rows=rows, cols=cols, cube_size=cube_size)

    return fallback


def resolve_depth_base_step(cube_size: float) -> float:
    """Resolve depth base step.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return clamp(
        cube_size * SHOT_STACK_DEPTH_BASE_MULT, SHOT_STACK_DEPTH_BASE_MIN, SHOT_STACK_DEPTH_BASE_MAX
    )


def resolve_depth_offset_for_age(cube_size: float, age: float) -> float:
    """Resolve depth offset for age.

    Args:
        cube_size: Input value for this computation.
        age: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    safe_age = max(0.0, age)
    base_step = resolve_depth_base_step(cube_size)
    linear_age = min(float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS), safe_age)
    tail_age = max(0.0, safe_age - float(SHOT_STACK_SOFT_CAP_LINEAR_LAYERS))
    return linear_age * base_step + tail_age * base_step * SHOT_STACK_TAIL_COMPRESS_RATIO


def resolve_max_depth_offset(cube_size: float, shots_total: int) -> float:
    """Resolve max depth offset.

    Args:
        cube_size: Input value for this computation.
        shots_total: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return resolve_depth_offset_for_age(cube_size, float(max(0, shots_total - 1)))


def resolve_matrix_front_z(cube_size: float) -> float:
    """Resolve matrix front z.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return 1.10 + cube_size * 0.92


def resolve_layer_gap(cube_size: float) -> float:
    """Resolve layer gap.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    base_gap = max(SHOT_QUBIT_MIN_HIST_GAP, cube_size * SHOT_QUBIT_HIST_GAP_CUBE_MULT)
    return base_gap * SHOT_REPLAY_LAYER_GAP_SCALE


def resolve_qubit_front_z(cube_size: float) -> float:
    """Resolve qubit front z.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return resolve_matrix_front_z(cube_size) + resolve_layer_gap(cube_size)


def resolve_slot_depth_offset(cube_size: float, shots_total: int, shot_layer_index: int) -> float:
    """Resolve slot depth offset.

    Args:
        cube_size: Input value for this computation.
        shots_total: Input value for this computation.
        shot_layer_index: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    if shots_total <= 1:
        return 0.0
    clamped_shot = max(0, min(max(0, shots_total - 1), shot_layer_index))
    slot_from_front = max(0, shots_total - 1 - clamped_shot)
    base_cube_depth = resolve_base_cube_depth(cube_size)
    max_stack_cuboid_depth = resolve_max_stack_cuboid_depth(base_cube_depth)
    max_offset = resolve_effective_max_depth_offset(cube_size, shots_total, max_stack_cuboid_depth)
    slot_ratio = slot_from_front / float(max(1, shots_total - 1))
    return max_offset * slot_ratio


def resolve_base_cube_depth(cube_size: float) -> float:
    """Resolve base cube depth.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    cube_side = clamp(
        cube_size * SHOT_QUBIT_CUBE_SIZE_RATIO,
        SHOT_QUBIT_CUBE_MIN_SIZE,
        SHOT_QUBIT_CUBE_MAX_SIZE,
    )
    return clamp(
        cube_side * 0.92,
        SHOT_QUBIT_CUBE_MIN_SIZE * 0.85,
        SHOT_QUBIT_CUBE_MAX_SIZE * 0.96,
    )


def resolve_max_stack_cuboid_depth(base_cube_depth: float) -> float:
    """Resolve max stack cuboid depth.

    Args:
        base_cube_depth: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    safe_base_depth = max(0.0, base_cube_depth)
    max_stack_depth = safe_base_depth * SHOT_QUBIT_STACK_DEPTH_MULTIPLIER
    return max(SHOT_QUBIT_CUBOID_MIN_DEPTH, max_stack_depth)


def resolve_density_rendered_front_z(cube_size: float) -> float:
    """Resolve density rendered front z.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return 1.10 + cube_size + 0.35


def resolve_spawn_front_gap(cube_size: float) -> float:
    """Resolve spawn front gap.

    Args:
        cube_size: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    cube_side = clamp(
        cube_size * SHOT_QUBIT_CUBE_SIZE_RATIO,
        SHOT_QUBIT_CUBE_MIN_SIZE,
        SHOT_QUBIT_CUBE_MAX_SIZE,
    )
    return clamp(cube_side * 0.16, 2.4, 7.0)


def resolve_spawn_center_z(cube_size: float, cuboid_depth: float) -> float:
    """Resolve spawn center z.

    Args:
        cube_size: Input value for this computation.
        cuboid_depth: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    density_front_z = resolve_density_rendered_front_z(cube_size)
    spawn_gap = resolve_spawn_front_gap(cube_size)
    return density_front_z + spawn_gap + max(0.0, cuboid_depth) * 0.5


def resolve_front_safe_max_depth_offset(
    cube_size: float,
    clearance_depth: float,
) -> float:
    """Resolve front safe max depth offset.

    Args:
        cube_size: Input value for this computation.
        clearance_depth: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    qubit_front_z = resolve_qubit_front_z(cube_size)
    density_front_z = resolve_density_rendered_front_z(cube_size)
    spawn_gap = resolve_spawn_front_gap(cube_size)
    min_layer_center_z = density_front_z + spawn_gap + max(0.0, clearance_depth) * 0.5
    return max(0.0, qubit_front_z - min_layer_center_z)


def resolve_effective_max_depth_offset(
    cube_size: float,
    shots_total: int,
    clearance_depth: float,
) -> float:
    """Resolve effective max depth offset.

    Args:
        cube_size: Input value for this computation.
        shots_total: Input value for this computation.
        clearance_depth: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    raw_max = resolve_max_depth_offset(cube_size, shots_total)
    front_safe_max = resolve_front_safe_max_depth_offset(cube_size, clearance_depth)
    return min(raw_max, front_safe_max)


def resolve_shot_cuboid_depth(cube_size: float, shots_total: int) -> float:
    """Resolve shot cuboid depth.

    Args:
        cube_size: Input value for this computation.
        shots_total: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    safe_shots = max(1, shots_total)
    base_cube_depth = resolve_base_cube_depth(cube_size)
    max_stack_cuboid_depth = resolve_max_stack_cuboid_depth(base_cube_depth)
    effective_max = resolve_effective_max_depth_offset(
        cube_size, safe_shots, max_stack_cuboid_depth
    )
    pillar_depth = max(base_cube_depth, effective_max + base_cube_depth)
    scaled_depth = pillar_depth / float(safe_shots)
    blended_depth = base_cube_depth + (scaled_depth - base_cube_depth) * clamp(
        SHOT_QUBIT_CUBOID_DEPTH_BLEND,
        0.0,
        1.0,
    )
    elongated_depth = blended_depth * SHOT_QUBIT_STACK_DEPTH_MULTIPLIER
    return clamp(elongated_depth, SHOT_QUBIT_CUBOID_MIN_DEPTH, max_stack_cuboid_depth)


def resolve_shot_stack_beat(shot_progress: float) -> tuple[str, float]:
    """Resolve shot stack beat.

    Args:
        shot_progress: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    p = clamp(shot_progress, 0.0, 1.0)
    lock_end = clamp(SHOT_STACK_BEAT_LOCK_FRACTION, 0.0, 1.0)
    emit_end = clamp(lock_end + SHOT_STACK_BEAT_EMIT_FRACTION, 0.0, 1.0)
    collapse_end = clamp(emit_end + SHOT_STACK_BEAT_COLLAPSE_FRACTION, 0.0, 1.0)
    if p < lock_end:
        return "lock_density", clamp(p / max(1e-5, lock_end), 0.0, 1.0)
    if p < emit_end:
        return "emit", clamp((p - lock_end) / max(1e-5, emit_end - lock_end), 0.0, 1.0)
    if p < collapse_end:
        return "collapse", clamp((p - emit_end) / max(1e-5, collapse_end - emit_end), 0.0, 1.0)
    return "stack_settle", clamp((p - collapse_end) / max(1e-5, 1.0 - collapse_end), 0.0, 1.0)


def resolve_density_relay_front(shot_beat: str, shot_beat_progress: float) -> float:
    """Resolve density relay front.

    Args:
        shot_beat: Input value for this computation.
        shot_beat_progress: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    beat = shot_beat or ""
    progress = clamp(shot_beat_progress, 0.0, 1.0)
    if beat == "lock_density":
        return 0.0
    if beat == "emit":
        return 0.5 * ease_in_out_circ01(progress)
    if beat == "collapse":
        return 0.5 + 0.5 * ease_in_out_circ01(progress)
    if beat == "stack_settle":
        return 1.0
    return 0.0


def resolve_emission_travel_progress(shot_beat: str, shot_beat_progress: float) -> float:
    """Resolve emission travel progress.

    Args:
        shot_beat: Input value for this computation.
        shot_beat_progress: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    beat = shot_beat or ""
    progress = clamp(shot_beat_progress, 0.0, 1.0)
    if beat == "lock_density":
        return 0.0
    if beat == "emit":
        return 0.0 + (0.72 - 0.0) * ease_in_out_circ01(progress)
    if beat == "collapse":
        return 0.72 + (1.0 - 0.72) * ease_in_out_circ01(progress)
    if beat == "stack_settle":
        return 1.0
    return progress


def reconstruct_replay(trace: dict[str, Any], replay: dict[str, Any]) -> ReplayBuild:
    """Reconstruct replay.

    Args:
        trace: Input value for this computation.
        replay: Input value for this computation.

    Returns:
        The computed value.
    """
    steps = trace.get("steps", [])
    step_count = len(steps)
    default_step_duration_ms = float(
        trace.get("timeline", {}).get("default_step_duration_ms", 800.0)
    )
    frames_per_step = max(1, int(round(default_step_duration_ms / (1000.0 / TARGET_FPS))))
    gate_frame_count = max(1, step_count * frames_per_step)
    reveal_frames = 48 if has_measurement_reveal(trace) else 0

    timeline = replay["timeline"]
    pullback_frames = max(1, int(timeline.get("camera_pullback_frames", 36)))
    base_frames_per_shot = max(1, int(timeline.get("frames_per_shot", 6)))
    extended_frames_per_shot = base_frames_per_shot + SHOT_STACK_EXTRA_FRAMES
    project_transition_frames = max(1, int(timeline.get("histogram_project_frames", 60)))
    shots_total = max(1, int(replay.get("shots_total", 0)))

    stack_frames_total = shots_total * extended_frames_per_shot
    project_frames_total = shots_total * extended_frames_per_shot

    replay_start_frame = gate_frame_count + reveal_frames
    replay_frame_count = (
        pullback_frames + stack_frames_total + project_transition_frames + project_frames_total
    )
    total_frames = replay_start_frame + replay_frame_count

    source_step_index = int(replay.get("source_step_index", max(0, step_count - 1)))
    source_step_index = max(0, min(max(0, step_count - 1), source_step_index))
    hold_hash = resolve_settle_state_hash(steps[source_step_index] if step_count > 0 else None)
    visual_source_hash = resolve_visual_source_state_hash(steps, source_step_index, hold_hash)

    events = replay.get("shot_events", [])
    max_event_index = max(0, len(events) - 1)
    shot_state_hash_by_shot: dict[int, str] = {}
    if events:
        for shot_idx in range(len(events)):
            event = (
                events[shot_idx]
                if shot_idx < len(events) and isinstance(events[shot_idx], dict)
                else None
            )
            shot_state_hash_by_shot[shot_idx] = resolve_event_state_hash(replay, event, hold_hash)
    final_transition_shot_index = max(0, min(max_event_index, shots_total - 1))
    final_transition_state_hash = shot_state_hash_by_shot.get(
        final_transition_shot_index, hold_hash
    )
    frames: list[ReplayFrame] = []

    for frame_index in range(replay_start_frame, total_frames):
        local_replay_frame = frame_index - replay_start_frame

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
            frames.append(
                ReplayFrame(
                    frame_index=frame_index,
                    phase="shot_camera_pullback",
                    phase_progress=phase_progress,
                    shot_index=-1,
                    shot_progress=0.0,
                    shot_beat="",
                    shot_beat_progress=0.0,
                    outcome_label="",
                    state_hash=hold_hash,
                )
            )
            continue

        if local_replay_frame < pullback_frames + stack_frames_total:
            phase = "shot_stack"
            stack_frame = local_replay_frame - pullback_frames
            shot_index = min(shots_total - 1, stack_frame // extended_frames_per_shot)
            shot_local = stack_frame - shot_index * extended_frames_per_shot
            shot_progress = (
                1.0
                if extended_frames_per_shot <= 1
                else clamp(
                    shot_local / float(max(1, extended_frames_per_shot - 1)),
                    0.0,
                    1.0,
                )
            )
            shot_beat, shot_beat_progress = resolve_shot_stack_beat(shot_progress)
            outcome_label = ""
            hash_shot_index = max(0, min(max_event_index, shot_index))
            state_hash = shot_state_hash_by_shot.get(hash_shot_index, hold_hash)
            if 0 <= shot_index < len(events) and isinstance(events[shot_index], dict):
                event = events[shot_index]
                outcome_label = str(event.get("outcome_label", ""))
            frames.append(
                ReplayFrame(
                    frame_index=frame_index,
                    phase=phase,
                    phase_progress=shot_progress,
                    shot_index=shot_index,
                    shot_progress=shot_progress,
                    shot_beat=shot_beat,
                    shot_beat_progress=shot_beat_progress,
                    outcome_label=outcome_label,
                    state_hash=state_hash,
                )
            )
            continue

        if local_replay_frame < pullback_frames + stack_frames_total + project_transition_frames:
            transition_frame = local_replay_frame - pullback_frames - stack_frames_total
            phase_progress = (
                1.0
                if project_transition_frames <= 1
                else clamp(
                    transition_frame / float(max(1, project_transition_frames - 1)),
                    0.0,
                    1.0,
                )
            )
            frames.append(
                ReplayFrame(
                    frame_index=frame_index,
                    phase="shot_histogram_project",
                    phase_progress=phase_progress,
                    shot_index=-1,
                    shot_progress=0.0,
                    shot_beat="",
                    shot_beat_progress=0.0,
                    outcome_label="",
                    state_hash=final_transition_state_hash,
                )
            )
            continue

        project_frame = (
            local_replay_frame - pullback_frames - stack_frames_total - project_transition_frames
        )
        shot_index = min(shots_total - 1, project_frame // extended_frames_per_shot)
        shot_local = project_frame - shot_index * extended_frames_per_shot
        shot_progress = (
            1.0
            if extended_frames_per_shot <= 1
            else clamp(
                shot_local / float(max(1, extended_frames_per_shot - 1)),
                0.0,
                1.0,
            )
        )
        outcome_label = ""
        hash_shot_index = max(0, min(max_event_index, shot_index))
        state_hash = shot_state_hash_by_shot.get(hash_shot_index, hold_hash)
        if 0 <= shot_index < len(events) and isinstance(events[shot_index], dict):
            event = events[shot_index]
            outcome_label = str(event.get("outcome_label", ""))
        frames.append(
            ReplayFrame(
                frame_index=frame_index,
                phase="shot_histogram_project",
                phase_progress=shot_progress,
                shot_index=shot_index,
                shot_progress=shot_progress,
                shot_beat="",
                shot_beat_progress=0.0,
                outcome_label=outcome_label,
                state_hash=state_hash,
            )
        )

    return ReplayBuild(
        frames=frames,
        shots_total=shots_total,
        pullback_frames=pullback_frames,
        base_frames_per_shot=base_frames_per_shot,
        extended_frames_per_shot=extended_frames_per_shot,
        stack_frames_total=stack_frames_total,
        project_transition_frames=project_transition_frames,
        project_frames_total=project_frames_total,
        replay_start_frame=replay_start_frame,
        hold_hash=hold_hash,
        visual_source_hash=visual_source_hash,
        shot_state_hash_by_shot=shot_state_hash_by_shot,
    )


def cumulative_counts_for_projection_frame(
    labels: list[str],
    events: list[dict[str, Any]],
    frame: ReplayFrame,
) -> dict[str, float]:
    """Compute cumulative counts for projection frame.

    Args:
        labels: Input value for this computation.
        events: Input value for this computation.
        frame: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    counts = {label: 0.0 for label in labels}
    if frame.phase != "shot_histogram_project" or frame.shot_index < 0:
        return counts

    completed = max(0, frame.shot_index)
    for idx in range(min(completed, len(events))):
        event = events[idx]
        if not isinstance(event, dict):
            continue
        label = str(event.get("outcome_label", ""))
        if label in counts:
            counts[label] += 1.0

    if frame.shot_index < len(events) and isinstance(events[frame.shot_index], dict):
        label = str(events[frame.shot_index].get("outcome_label", ""))
        if label in counts:
            counts[label] += clamp(frame.shot_progress, 0.0, 1.0)
    return counts


def validate_replay(trace: dict[str, Any]) -> tuple[list[str], list[str], int]:
    """Validate replay.

    Args:
        trace: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    failures: list[str] = []
    signatures: list[str] = []

    terminal_measurement = has_terminal_measurement(trace)
    replay = parse_replay(trace)
    if replay is None:
        if terminal_measurement:
            failures.append("terminal measurement trace is missing measurement_shot_replay")
        return failures, signatures, 0

    outcomes = replay.get("outcomes", [])
    shot_events = replay.get("shot_events", [])
    if not isinstance(outcomes, list) or not isinstance(shot_events, list):
        failures.append("replay payload arrays are malformed")
        return failures, signatures, 0

    if len(shot_events) != int(replay.get("shots_total", 0)):
        failures.append(
            f"shot_events length {len(shot_events)} != shots_total {replay.get('shots_total', 0)}"
        )

    labels = sorted(str(item.get("label", "")) for item in outcomes if isinstance(item, dict))
    labels = [label for label in labels if label]
    if len(set(labels)) != len(labels):
        failures.append("outcomes contains duplicate labels")

    for idx, event in enumerate(shot_events):
        if not isinstance(event, dict):
            failures.append(f"shot_events[{idx}] is not an object")
            continue
        shot_index = int(event.get("shot_index", -1))
        if shot_index != idx:
            failures.append(f"shot_events[{idx}] has shot_index={shot_index} (expected {idx})")

    replay_build = reconstruct_replay(trace, replay)
    frames = replay_build.frames

    expected_frame_count = (
        replay_build.pullback_frames
        + replay_build.stack_frames_total
        + replay_build.project_transition_frames
        + replay_build.project_frames_total
    )
    if len(frames) != expected_frame_count:
        failures.append("replay frame reconstruction length mismatch")

    # Phase ordering checks
    for idx, frame in enumerate(frames):
        if idx < replay_build.pullback_frames:
            expected_phase = "shot_camera_pullback"
        elif idx < replay_build.pullback_frames + replay_build.stack_frames_total:
            expected_phase = "shot_stack"
        else:
            expected_phase = "shot_histogram_project"
        if frame.phase != expected_phase:
            failures.append(
                f"frame {frame.frame_index}: expected phase {expected_phase}, got {frame.phase}"
            )

    # Stack growth and projection correctness checks.
    step_metrics = resolve_replay_step_metrics(trace, replay)
    responsible_source_by_shot: dict[int, ShotSourceCellSignature] = {}
    for idx, event in enumerate(shot_events):
        if not isinstance(event, dict):
            continue
        signature_a = resolve_replay_responsible_source_cell_signature(
            replay,
            event,
            step_metrics.rows,
            step_metrics.cols,
        )
        signature_b = resolve_replay_responsible_source_cell_signature(
            replay,
            event,
            step_metrics.rows,
            step_metrics.cols,
        )
        if signature_a is None:
            failures.append(
                f"shot_events[{idx}] could not resolve deterministic responsible source cell"
            )
            continue
        if signature_b is None or signature_b != signature_a:
            failures.append(
                f"shot_events[{idx}] responsible source cell resolver is not deterministic"
            )
            continue
        responsible_source_by_shot[idx] = signature_a
    source_cells_by_label: dict[str, set[str]] = {}
    unique_cells_across_labels: set[str] = set()
    labels_with_source: set[str] = set()
    for idx, signature in responsible_source_by_shot.items():
        event = (
            shot_events[idx]
            if idx < len(shot_events) and isinstance(shot_events[idx], dict)
            else {}
        )
        label = str(event.get("outcome_label", ""))
        cell_key = f"{signature.row}:{signature.col}:{signature.basis_label}:{signature.block_key}"
        unique_cells_across_labels.add(cell_key)
        if label:
            labels_with_source.add(label)
            if label not in source_cells_by_label:
                source_cells_by_label[label] = set()
            source_cells_by_label[label].add(cell_key)
    if len(labels_with_source) >= 2 and len(unique_cells_across_labels) < 2:
        failures.append(
            "responsible source-cell mapping is degenerate across multiple replay outcomes"
        )
    for label, cells in source_cells_by_label.items():
        if len(cells) > 1:
            failures.append(f"outcome label {label!r} maps to multiple responsible source cells")

    slot_depth_by_layer: dict[int, float] = {}
    prev_projection_shot = -1
    beat_order = {"lock_density": 0, "emit": 1, "collapse": 2, "stack_settle": 3}
    prev_beat_order_by_shot: dict[int, int] = {}
    prev_beat_progress_by_shot: dict[int, float] = {}
    beats_seen_by_shot: dict[int, set[str]] = {}
    prev_relay_front_by_shot: dict[int, float] = {}
    collapse_front_max_by_shot: dict[int, float] = {}
    collapse_terminal_front_by_shot: dict[int, float] = {}
    prev_emission_progress_by_shot: dict[int, float] = {}
    first_emit_progress_by_shot: dict[int, float] = {}
    collapse_emission_max_by_shot: dict[int, float] = {}
    stack_state_hash_by_shot: dict[int, str] = {}
    projection_state_hash_by_shot: dict[int, str] = {}
    base_cube_depth = resolve_base_cube_depth(step_metrics.cube_size)
    max_stack_cuboid_depth = resolve_max_stack_cuboid_depth(base_cube_depth)
    shot_cuboid_depth = resolve_shot_cuboid_depth(step_metrics.cube_size, replay_build.shots_total)
    density_front_z = resolve_density_rendered_front_z(step_metrics.cube_size)
    spawn_gap = resolve_spawn_front_gap(step_metrics.cube_size)
    qubit_front_z = resolve_qubit_front_z(step_metrics.cube_size)
    effective_max_depth = resolve_effective_max_depth_offset(
        step_metrics.cube_size,
        replay_build.shots_total,
        max_stack_cuboid_depth,
    )
    preview_spawn_center_z = resolve_spawn_center_z(step_metrics.cube_size, base_cube_depth)
    stack_spawn_center_z = resolve_spawn_center_z(step_metrics.cube_size, shot_cuboid_depth)
    if shot_cuboid_depth > max_stack_cuboid_depth + DEPTH_TOL:
        failures.append(
            "shot cuboid depth exceeds maximum stacked cuboid depth "
            f"({shot_cuboid_depth:.6f} > {max_stack_cuboid_depth:.6f})"
        )
    if preview_spawn_center_z - base_cube_depth * 0.5 <= density_front_z + DEPTH_TOL:
        failures.append(
            "preview spawn cuboid is not fully in front of rendered density front "
            f"({preview_spawn_center_z - base_cube_depth * 0.5:.6f} <= {density_front_z:.6f})"
        )
    if stack_spawn_center_z - shot_cuboid_depth * 0.5 <= density_front_z + DEPTH_TOL:
        failures.append(
            "stack spawn cuboid is not fully in front of rendered density front "
            f"({stack_spawn_center_z - shot_cuboid_depth * 0.5:.6f} <= {density_front_z:.6f})"
        )
    oldest_slot_center_z = qubit_front_z - effective_max_depth
    if oldest_slot_center_z - shot_cuboid_depth * 0.5 <= density_front_z + DEPTH_TOL:
        failures.append(
            "fixed-slot oldest cuboid intersects rendered density front "
            f"({oldest_slot_center_z - shot_cuboid_depth * 0.5:.6f} <= {density_front_z:.6f})"
        )
    if spawn_gap <= 0.0:
        failures.append("spawn gap must be positive")

    prev_scaled_depth: float | None = None
    for test_shots in range(1, replay_build.shots_total + 1):
        scaled_depth = resolve_shot_cuboid_depth(step_metrics.cube_size, test_shots)
        if prev_scaled_depth is not None and scaled_depth > prev_scaled_depth + DEPTH_TOL:
            failures.append(
                "shot cuboid depth is not non-increasing by shots_total "
                f"(n={test_shots}, {scaled_depth:.6f} > {prev_scaled_depth:.6f})"
            )
            break
        prev_scaled_depth = scaled_depth

    for shot_index in range(len(shot_events)):
        event = (
            shot_events[shot_index]
            if shot_index < len(shot_events) and isinstance(shot_events[shot_index], dict)
            else None
        )
        expected_hash = resolve_event_state_hash(replay, event, replay_build.hold_hash)
        runtime_hash = replay_build.shot_state_hash_by_shot.get(shot_index, "")
        if runtime_hash != expected_hash:
            failures.append(
                f"shot {shot_index}: shot state hash reconstruction mismatch ({runtime_hash} != {expected_hash})"
            )

    final_transition_shot_index = max(
        0, min(max(0, len(shot_events) - 1), replay_build.shots_total - 1)
    )
    final_transition_expected_hash = replay_build.shot_state_hash_by_shot.get(
        final_transition_shot_index,
        replay_build.hold_hash,
    )
    for frame in frames:
        counts = cumulative_counts_for_projection_frame(labels, shot_events, frame)
        total_count = float(sum(counts.values()))

        if frame.phase == "shot_camera_pullback":
            expected_hash = replay_build.hold_hash
            if frame.state_hash != expected_hash:
                failures.append(
                    f"frame {frame.frame_index}: pullback state hash mismatch "
                    f"({frame.state_hash} != {expected_hash})"
                )
        if frame.phase == "shot_stack":
            effective_shot_index = max(0, min(max(0, len(shot_events) - 1), frame.shot_index))
            expected_hash = replay_build.shot_state_hash_by_shot.get(
                effective_shot_index,
                replay_build.hold_hash,
            )
            if frame.state_hash != expected_hash:
                failures.append(
                    f"frame {frame.frame_index}: shot_stack state hash mismatch "
                    f"({frame.state_hash} != {expected_hash})"
                )
            previous_stack_hash = stack_state_hash_by_shot.get(frame.shot_index)
            if previous_stack_hash is None:
                stack_state_hash_by_shot[frame.shot_index] = frame.state_hash
            elif frame.state_hash != previous_stack_hash:
                failures.append(
                    f"frame {frame.frame_index}: shot_stack state hash changed within shot {frame.shot_index} "
                    f"({frame.state_hash} != {previous_stack_hash})"
                )
        if frame.phase == "shot_histogram_project" and frame.shot_index < 0:
            if frame.state_hash != final_transition_expected_hash:
                failures.append(
                    f"frame {frame.frame_index}: project transition state hash mismatch "
                    f"({frame.state_hash} != {final_transition_expected_hash})"
                )

        if frame.phase != "shot_histogram_project" or frame.shot_index < 0:
            if abs(total_count) > COUNT_TOL:
                failures.append(
                    f"frame {frame.frame_index}: histogram is not frozen before projection (sum={total_count:.6f})"
                )

        if frame.phase == "shot_stack":
            if frame.shot_index < 0:
                failures.append(
                    f"frame {frame.frame_index}: shot_stack has invalid shot_index={frame.shot_index}"
                )
                continue
            if frame.shot_beat not in beat_order:
                failures.append(f"frame {frame.frame_index}: unknown shot beat {frame.shot_beat!r}")
            else:
                beats_seen = beats_seen_by_shot.setdefault(frame.shot_index, set())
                beats_seen.add(frame.shot_beat)
                order = beat_order[frame.shot_beat]
                prev_order = prev_beat_order_by_shot.get(frame.shot_index, -1)
                prev_progress = prev_beat_progress_by_shot.get(frame.shot_index, 0.0)
                if order < prev_order:
                    failures.append(
                        f"frame {frame.frame_index}: shot beat regressed for shot {frame.shot_index} "
                        f"({frame.shot_beat} after order {prev_order})"
                    )
                if order == prev_order and frame.shot_beat_progress + COUNT_TOL < prev_progress:
                    failures.append(
                        f"frame {frame.frame_index}: shot beat progress regressed for shot {frame.shot_index} "
                        f"({frame.shot_beat_progress:.6f} < {prev_progress:.6f})"
                    )
                if prev_order < 0 and frame.shot_beat != "lock_density":
                    failures.append(
                        f"frame {frame.frame_index}: first beat for shot {frame.shot_index} is {frame.shot_beat}, "
                        "expected lock_density"
                    )
                prev_beat_order_by_shot[frame.shot_index] = order
                prev_beat_progress_by_shot[frame.shot_index] = frame.shot_beat_progress
                if frame.shot_beat in {"emit", "collapse"}:
                    relay_front = resolve_density_relay_front(
                        frame.shot_beat, frame.shot_beat_progress
                    )
                    prev_relay_front = prev_relay_front_by_shot.get(frame.shot_index)
                    if prev_relay_front is not None and relay_front + COUNT_TOL < prev_relay_front:
                        failures.append(
                            f"frame {frame.frame_index}: relay front regressed for shot {frame.shot_index} "
                            f"({relay_front:.6f} < {prev_relay_front:.6f})"
                        )
                    prev_relay_front_by_shot[frame.shot_index] = relay_front
                    if frame.shot_beat == "collapse":
                        prev_collapse_max = collapse_front_max_by_shot.get(frame.shot_index, 0.0)
                        collapse_front_max_by_shot[frame.shot_index] = max(
                            prev_collapse_max, relay_front
                        )
                        if frame.shot_beat_progress >= 1.0 - COUNT_TOL:
                            collapse_terminal_front_by_shot[frame.shot_index] = relay_front

                    emission_progress = resolve_emission_travel_progress(
                        frame.shot_beat, frame.shot_beat_progress
                    )
                    prev_emission = prev_emission_progress_by_shot.get(frame.shot_index)
                    if prev_emission is not None and emission_progress + COUNT_TOL < prev_emission:
                        failures.append(
                            f"frame {frame.frame_index}: emission travel regressed for shot {frame.shot_index} "
                            f"({emission_progress:.6f} < {prev_emission:.6f})"
                        )
                    prev_emission_progress_by_shot[frame.shot_index] = emission_progress
                    if (
                        frame.shot_beat == "emit"
                        and frame.shot_index not in first_emit_progress_by_shot
                    ):
                        first_emit_progress_by_shot[frame.shot_index] = emission_progress
                    if frame.shot_beat == "collapse":
                        prev_emit_max = collapse_emission_max_by_shot.get(frame.shot_index, 0.0)
                        collapse_emission_max_by_shot[frame.shot_index] = max(
                            prev_emit_max, emission_progress
                        )

            visible_layers = frame.shot_index + 1
            if visible_layers <= 0:
                failures.append(f"frame {frame.frame_index}: visible stack layers is non-positive")
            for layer_idx in range(visible_layers):
                slot_depth = resolve_slot_depth_offset(
                    step_metrics.cube_size,
                    replay_build.shots_total,
                    layer_idx,
                )
                if layer_idx in slot_depth_by_layer:
                    if abs(slot_depth - slot_depth_by_layer[layer_idx]) > DEPTH_TOL:
                        failures.append(
                            "frame "
                            f"{frame.frame_index}: slot depth drifted for layer {layer_idx} "
                            f"({slot_depth:.6f} != {slot_depth_by_layer[layer_idx]:.6f})"
                        )
                else:
                    slot_depth_by_layer[layer_idx] = slot_depth

        if frame.phase == "shot_histogram_project" and frame.shot_index >= 0:
            shot_progress = clamp(frame.shot_progress, 0.0, 1.0)
            active_label = frame.outcome_label
            if frame.shot_index < prev_projection_shot:
                failures.append(
                    f"frame {frame.frame_index}: projection shot_index regressed ({frame.shot_index} < {prev_projection_shot})"
                )
            prev_projection_shot = frame.shot_index

            for layer_idx in range(replay_build.shots_total):
                slot_depth = resolve_slot_depth_offset(
                    step_metrics.cube_size,
                    replay_build.shots_total,
                    layer_idx,
                )
                if layer_idx in slot_depth_by_layer:
                    if abs(slot_depth - slot_depth_by_layer[layer_idx]) > DEPTH_TOL:
                        failures.append(
                            "frame "
                            f"{frame.frame_index}: projection slot depth mismatch for layer {layer_idx} "
                            f"({slot_depth:.6f} != {slot_depth_by_layer[layer_idx]:.6f})"
                        )
                else:
                    slot_depth_by_layer[layer_idx] = slot_depth

            if frame.shot_index < len(shot_events) and isinstance(
                shot_events[frame.shot_index], dict
            ):
                event = shot_events[frame.shot_index]
                event_label = str(event.get("outcome_label", ""))
                if event_label:
                    active_label = event_label
                if frame.outcome_label != event_label:
                    failures.append(
                        f"frame {frame.frame_index}: projection source label mismatch {frame.outcome_label} != {event_label}"
                    )

            effective_shot_index = max(0, min(max(0, len(shot_events) - 1), frame.shot_index))
            expected_projection_hash = replay_build.shot_state_hash_by_shot.get(
                effective_shot_index,
                replay_build.hold_hash,
            )
            if frame.state_hash != expected_projection_hash:
                failures.append(
                    f"frame {frame.frame_index}: projection state hash mismatch "
                    f"({frame.state_hash} != {expected_projection_hash})"
                )
            previous_projection_hash = projection_state_hash_by_shot.get(frame.shot_index)
            if previous_projection_hash is None:
                projection_state_hash_by_shot[frame.shot_index] = frame.state_hash
            elif frame.state_hash != previous_projection_hash:
                failures.append(
                    f"frame {frame.frame_index}: projection state hash changed within shot {frame.shot_index} "
                    f"({frame.state_hash} != {previous_projection_hash})"
                )

            expected_total = frame.shot_index + shot_progress
            if abs(total_count - expected_total) > COUNT_TOL:
                failures.append(
                    f"frame {frame.frame_index}: projected histogram total {total_count:.6f} != {expected_total:.6f}"
                )

            if not active_label:
                failures.append(
                    f"frame {frame.frame_index}: projection frame is missing active outcome label"
                )
            for label, count in counts.items():
                if label != active_label:
                    if abs(count - round(count)) > COUNT_TOL:
                        failures.append(
                            f"frame {frame.frame_index}: non-active label {label} has fractional projected count {count:.6f}"
                        )
                    continue

                base_count = count - shot_progress
                if abs(base_count - round(base_count)) > COUNT_TOL:
                    failures.append(
                        f"frame {frame.frame_index}: active label {label} base projected count is not integer ({base_count:.6f})"
                    )
                if COUNT_TOL < shot_progress < 1.0 - COUNT_TOL:
                    fractional = count - math.floor(count)
                    if abs(fractional - shot_progress) > COUNT_TOL:
                        failures.append(
                            f"frame {frame.frame_index}: active label {label} fractional progress {fractional:.6f} != shot_progress {shot_progress:.6f}"
                        )

        source_signature = ""
        if frame.shot_index >= 0 and frame.shot_index in responsible_source_by_shot:
            src = responsible_source_by_shot[frame.shot_index]
            source_signature = (
                f":src={src.row},{src.col},{src.basis_label},{src.state_hash},{src.block_key}"
            )
        signatures.append(
            f"{frame.frame_index}:{frame.phase}:{frame.shot_index}:{frame.shot_progress:.6f}:"
            f"{frame.shot_beat}:{frame.shot_beat_progress:.6f}:{frame.state_hash}:{total_count:.6f}"
            f"{source_signature}"
        )

    for shot_index, stack_hash in stack_state_hash_by_shot.items():
        project_hash = projection_state_hash_by_shot.get(shot_index)
        if project_hash is None:
            continue
        if stack_hash != project_hash:
            failures.append(
                f"shot {shot_index}: stack/project state hash mismatch ({stack_hash} != {project_hash})"
            )

    if frames:
        final_counts = cumulative_counts_for_projection_frame(labels, shot_events, frames[-1])
        final_total = float(sum(final_counts.values()))
        if abs(final_total - replay_build.shots_total) > COUNT_TOL:
            failures.append(
                f"final projected histogram total {final_total:.6f} != shots_total {replay_build.shots_total}"
            )
    for shot_index in range(replay_build.shots_total):
        beats_seen = beats_seen_by_shot.get(shot_index, set())
        if not beats_seen:
            failures.append(f"shot {shot_index}: missing shot_stack beats")
            continue
        if "lock_density" not in beats_seen:
            failures.append(f"shot {shot_index}: missing lock_density beat")
        if "collapse" not in beats_seen:
            failures.append(f"shot {shot_index}: missing collapse beat")
        if "stack_settle" not in beats_seen:
            failures.append(f"shot {shot_index}: missing stack_settle beat")
        if "emit" in beats_seen or "collapse" in beats_seen:
            collapse_front = collapse_terminal_front_by_shot.get(
                shot_index,
                collapse_front_max_by_shot.get(shot_index, 0.0),
            )
            if collapse_front + COUNT_TOL < RELAY_FRONT_COMPLETE_MIN:
                failures.append(
                    f"shot {shot_index}: relay front did not reach completion "
                    f"({collapse_front:.6f} < {RELAY_FRONT_COMPLETE_MIN:.2f})"
                )
        if "emit" in beats_seen:
            first_emit = first_emit_progress_by_shot.get(shot_index, 1.0)
            if first_emit - COUNT_TOL > EMISSION_TRAVEL_START_MAX:
                failures.append(
                    f"shot {shot_index}: first emit travel is too advanced "
                    f"({first_emit:.6f} > {EMISSION_TRAVEL_START_MAX:.2f})"
                )
        if "collapse" in beats_seen:
            collapse_emit = collapse_emission_max_by_shot.get(shot_index, 0.0)
            if collapse_emit + COUNT_TOL < EMISSION_TRAVEL_COMPLETE_MIN:
                failures.append(
                    f"shot {shot_index}: collapse travel did not reach completion "
                    f"({collapse_emit:.6f} < {EMISSION_TRAVEL_COMPLETE_MIN:.2f})"
                )

    return failures, signatures, len(frames)


def main() -> int:
    """Run the script entry point.

    Returns:
        The computed integer value.
    """
    parser = argparse.ArgumentParser(description="Validate measurement shot replay reconstruction.")
    parser.add_argument("--trace", default="viewer/processing_qave/data/trace.json")
    args = parser.parse_args()

    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))

    failures_a, signatures_a, frame_count = validate_replay(trace)
    failures_b, signatures_b, _ = validate_replay(trace)
    failures = list(failures_a)

    if failures_b:
        failures.append("second validation pass produced failures")
        failures.extend(f"second pass: {item}" for item in failures_b[:10])
    if signatures_a != signatures_b:
        failures.append(
            "determinism failure: replay signatures differ across repeated reconstruction runs"
        )

    print(f"trace={trace_path}")
    print(f"replay_frames_checked={frame_count}")
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
