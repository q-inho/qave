"""qave public package API."""

from qave._contract_version import CONTRACT_VERSION, contract_version
from qave.api import (
    generate_animation_from_openqasm,
    generate_animation_from_qiskit,
    generate_trace_from_openqasm,
    generate_trace_from_qiskit,
)
from qave.errors import (
    ArtifactIOError,
    ContractValidationError,
    InputValidationError,
    QaveError,
    RenderExecutionError,
    RuntimeDependencyError,
)
from qave.options import ArtifactOptions, RenderOptions, SimulationOptions
from qave.results import (
    AnimationGenerationResult,
    ArtifactPaths,
    DiagnosticEntry,
    TraceGenerationResult,
)
from qave_backend.simulator.backend_a import simulate_backend_a

__all__ = [
    "CONTRACT_VERSION",
    "AnimationGenerationResult",
    "ArtifactIOError",
    "ArtifactOptions",
    "ArtifactPaths",
    "ContractValidationError",
    "DiagnosticEntry",
    "InputValidationError",
    "QaveError",
    "RenderExecutionError",
    "RenderOptions",
    "RuntimeDependencyError",
    "SimulationOptions",
    "TraceGenerationResult",
    "contract_version",
    "generate_animation_from_openqasm",
    "generate_animation_from_qiskit",
    "generate_trace_from_openqasm",
    "generate_trace_from_qiskit",
    "simulate_backend_a",
]
