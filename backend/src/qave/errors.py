"""Public exception hierarchy for the qave API package."""

from __future__ import annotations


class QaveError(Exception):
    """Base class for all qave package exceptions."""


class InputValidationError(QaveError):
    """Raised when user-provided input is malformed or unsupported."""


class ContractValidationError(QaveError):
    """Raised when contract model serialization/validation fails."""


class RuntimeDependencyError(QaveError):
    """Raised when required runtime tools are unavailable."""


class RenderExecutionError(QaveError):
    """Raised when Processing/ffmpeg execution fails."""


class ArtifactIOError(QaveError):
    """Raised when artifact writing or discovery fails."""
