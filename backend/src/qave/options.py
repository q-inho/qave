"""Public option dataclasses for qave workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

AlgorithmId = Literal[
    "bell",
    "ghz",
    "qft",
    "teleportation",
    "grover",
    "vqe",
    "custom",
]


@dataclass(frozen=True, slots=True)
class SimulationOptions:
    """Simulation behavior options used by trace and animation APIs."""

    algorithm_id: AlgorithmId = "custom"
    mode: Literal["preview", "validation"] = "preview"
    measurement_mode: Literal["collapse"] = "collapse"
    seed: int = 42
    shot_count: int = 100
    precision_profile: Literal["fast", "balanced", "strict"] = "balanced"
    animation_profile: Literal["teaching_default", "analysis_slow", "presentation_fast"] = (
        "teaching_default"
    )
    request_id: str | None = None
    params: dict[str, str | int | float | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize values after dataclass initialization."""
        if self.measurement_mode != "collapse":
            msg = "measurement_mode must be 'collapse'; branching is no longer supported"
            raise ValueError(msg)
        if self.shot_count < 1:
            msg = "shot_count must be >= 1"
            raise ValueError(msg)
        if self.seed < 0:
            msg = "seed must be >= 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RenderOptions:
    """Rendering and encoding options for animation generation APIs."""

    width: int = 1920
    height: int = 1080
    fps: int = 60
    keep_frames: bool = True
    emit_mp4: bool = True
    emit_gif: bool = False
    record_mode: Literal["full"] = "full"
    processing_runner: str | None = None
    ffmpeg_bin: str = "ffmpeg"
    sketch_dir: Path | None = None

    def __post_init__(self) -> None:
        """Validate and normalize values after dataclass initialization."""
        if self.width < 320 or self.height < 240:
            msg = "width/height must be at least 320x240"
            raise ValueError(msg)
        if self.fps < 1:
            msg = "fps must be >= 1"
            raise ValueError(msg)
        if not (self.keep_frames or self.emit_mp4 or self.emit_gif):
            msg = "At least one of keep_frames, emit_mp4, or emit_gif must be True."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ArtifactOptions:
    """Filesystem artifact output controls."""

    out_dir: Path | None = None
    write_result_json: bool = True
    write_validation_json: bool = False
