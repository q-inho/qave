"""Public result dataclasses for qave workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qave.errors import InputValidationError
from qave_backend.contracts.models import (
    AlgorithmTrace,
    MeasurementShotReplay,
    SimulationRequest,
    SimulationResult,
    ValidationReport,
)


@dataclass(frozen=True, slots=True)
class DiagnosticEntry:
    """Structured diagnostic surfaced by qave orchestration APIs."""

    code: str
    message: str
    source: str = "qave"


@dataclass(frozen=True, slots=True)
class ArtifactPaths:
    """Written artifact paths for a trace generation workflow."""

    out_dir: Path
    trace_json: Path
    result_json: Path | None = None
    validation_json: Path | None = None


@dataclass(frozen=True, slots=True)
class TraceGenerationResult:
    """Typed return value from trace generation APIs."""

    request: SimulationRequest
    simulation_result: SimulationResult
    trace: AlgorithmTrace
    validation: ValidationReport | None
    paths: ArtifactPaths
    diagnostics: list[DiagnosticEntry] = field(default_factory=list)

    def require_measurement_shot_replay(self) -> MeasurementShotReplay:
        """Return `measurement_shot_replay` payload or raise when unavailable.

        QAVE emits `measurement_shot_replay` only when the circuit ends with a terminal
        measurement operation. Tutorials can use this helper to fail fast with a typed
        qave exception instead of embedding ad-hoc `RuntimeError` checks.

        Returns:
            Measurement shot replay contract payload from the generated trace.

        Raises:
            InputValidationError: If `measurement_shot_replay` is missing. Ensure the circuit ends
                with a terminal measurement and `SimulationOptions(shot_count>=1)` is set.
        """
        replay = self.trace.measurement_shot_replay
        if replay is None:
            msg = (
                "Trace does not include measurement_shot_replay. Ensure the circuit ends with a "
                "terminal measurement and SimulationOptions(shot_count>=1) is set."
            )
            raise InputValidationError(msg)
        return replay


@dataclass(frozen=True, slots=True)
class AnimationGenerationResult(TraceGenerationResult):
    """Typed return value from animation generation APIs."""

    frames_dir: Path = Path("")
    mp4_path: Path | None = None
    gif_path: Path | None = None
