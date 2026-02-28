"""High-level public API entrypoints for qave package workflows."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from qiskit import QuantumCircuit

from qave._contract_version import CURRENT_CONTRACT_VERSION
from qave.errors import ContractValidationError, InputValidationError
from qave.io import ensure_out_dir, resolve_out_dir, write_json
from qave.options import ArtifactOptions, RenderOptions, SimulationOptions
from qave.render import run_render_pipeline
from qave.results import (
    AnimationGenerationResult,
    ArtifactPaths,
    DiagnosticEntry,
    TraceGenerationResult,
)
from qave_backend.contracts.models import QuantumCircuitIR, SimulationRequest
from qave_backend.ingest.openqasm_importer import import_openqasm
from qave_backend.ingest.qiskit_importer import import_qiskit_circuit
from qave_backend.simulator.backend_a import simulate_backend_a


def _default_request_id() -> str:
    """Build a timestamp-based fallback request identifier."""
    return f"qave_req_{int(time.time() * 1000)}"


def _resolve_options(
    options: SimulationOptions | None,
    artifacts: ArtifactOptions | None,
) -> tuple[SimulationOptions, ArtifactOptions]:
    """Resolve optional API options to concrete dataclass instances.

    Args:
        options: Optional simulation behavior overrides.
        artifacts: Optional artifact writing overrides.

    Returns:
        Tuple of resolved simulation and artifact options.
    """
    resolved_options = options or SimulationOptions()
    resolved_artifacts = artifacts or ArtifactOptions()
    return resolved_options, resolved_artifacts


def _build_request(options: SimulationOptions) -> SimulationRequest:
    """Build a validated simulation request payload from API options.

    Args:
        options: User-facing simulation options dataclass.

    Returns:
        Normalized simulation request model for backend execution.

    Raises:
        ContractValidationError: If options do not satisfy contract constraints.
    """
    try:
        return SimulationRequest(
            contract_version=CURRENT_CONTRACT_VERSION,
            request_id=options.request_id or _default_request_id(),
            algorithm_id=options.algorithm_id,
            params=options.params,
            mode=options.mode,
            seed=options.seed,
            precision_profile=options.precision_profile,
            measurement_mode=options.measurement_mode,
            animation_profile=options.animation_profile,
            shot_count=options.shot_count,
        )
    except ValueError as exc:
        msg = f"Invalid simulation options: {exc}"
        raise ContractValidationError(msg) from exc


def _write_trace_artifacts(
    *,
    out_dir: Path,
    trace: object,
    simulation_result: object,
    validation: object | None,
    write_result_json: bool,
    write_validation_json: bool,
) -> ArtifactPaths:
    """Persist trace/result/validation JSON artifacts according to flags.

    Args:
        out_dir: Output directory for generated artifacts.
        trace: Algorithm trace payload.
        simulation_result: Simulation result payload.
        validation: Optional validation report payload.
        write_result_json: Whether to persist `result.json`.
        write_validation_json: Whether to persist `validation.json`.

    Returns:
        Paths to all generated artifacts.
    """
    trace_path = write_json(out_dir / "trace.json", trace)

    result_path: Path | None = None
    if write_result_json:
        result_path = write_json(out_dir / "result.json", simulation_result)

    validation_path: Path | None = None
    if write_validation_json and validation is not None:
        validation_path = write_json(out_dir / "validation.json", validation)

    return ArtifactPaths(
        out_dir=out_dir,
        trace_json=trace_path,
        result_json=result_path,
        validation_json=validation_path,
    )


def _trace_from_ir(
    *,
    ir_loader: Callable[[], QuantumCircuitIR],
    options: SimulationOptions | None = None,
    artifacts: ArtifactOptions | None = None,
) -> TraceGenerationResult:
    """Generate simulation artifacts from an IR loader callback.

    Args:
        ir_loader: Deferred IR construction callback.
        options: Optional simulation behavior overrides.
        artifacts: Optional artifact writing overrides.

    Returns:
        Trace-generation result bundle including diagnostics and file paths.
    """
    resolved_options, resolved_artifacts = _resolve_options(options, artifacts)
    request = _build_request(resolved_options)
    out_dir = ensure_out_dir(
        resolve_out_dir(
            explicit_out_dir=resolved_artifacts.out_dir,
            request_id=request.request_id,
        )
    )

    ir = ir_loader()
    simulation_result, trace, validation = simulate_backend_a(ir, request)
    paths = _write_trace_artifacts(
        out_dir=out_dir,
        trace=trace,
        simulation_result=simulation_result,
        validation=validation,
        write_result_json=resolved_artifacts.write_result_json,
        write_validation_json=resolved_artifacts.write_validation_json,
    )

    diagnostics = [
        DiagnosticEntry(code=item.code, message=item.message, source="backend")
        for item in simulation_result.diagnostics
    ]
    return TraceGenerationResult(
        request=request,
        simulation_result=simulation_result,
        trace=trace,
        validation=validation,
        paths=paths,
        diagnostics=diagnostics,
    )


def generate_trace_from_qiskit(
    circuit: QuantumCircuit,
    *,
    options: SimulationOptions | None = None,
    artifacts: ArtifactOptions | None = None,
) -> TraceGenerationResult:
    """Generate contract artifacts from a Qiskit circuit."""
    if not isinstance(circuit, QuantumCircuit):
        msg = "circuit must be an instance of qiskit.QuantumCircuit"
        raise InputValidationError(msg)

    try:
        return _trace_from_ir(
            ir_loader=lambda: import_qiskit_circuit(circuit),
            options=options,
            artifacts=artifacts,
        )
    except ValueError as exc:
        msg = f"Qiskit circuit import failed: {exc}"
        raise InputValidationError(msg) from exc


def generate_trace_from_openqasm(
    qasm: str,
    *,
    options: SimulationOptions | None = None,
    artifacts: ArtifactOptions | None = None,
) -> TraceGenerationResult:
    """Generate contract artifacts from OpenQASM source text."""
    if not isinstance(qasm, str) or not qasm.strip():
        msg = "qasm must be a non-empty OpenQASM string"
        raise InputValidationError(msg)

    try:
        return _trace_from_ir(
            ir_loader=lambda: import_openqasm(qasm),
            options=options,
            artifacts=artifacts,
        )
    except ValueError as exc:
        msg = f"OpenQASM import failed: {exc}"
        raise InputValidationError(msg) from exc


def generate_animation_from_qiskit(
    circuit: QuantumCircuit,
    *,
    options: SimulationOptions | None = None,
    render: RenderOptions | None = None,
    artifacts: ArtifactOptions | None = None,
) -> AnimationGenerationResult:
    """Generate trace artifacts and rendered animation outputs from a Qiskit circuit."""
    trace_result = generate_trace_from_qiskit(circuit, options=options, artifacts=artifacts)
    resolved_render = render or RenderOptions()

    frames_dir, mp4_path, gif_path, render_diags = run_render_pipeline(
        trace_path=trace_result.paths.trace_json,
        render=resolved_render,
        out_dir=trace_result.paths.out_dir,
    )

    diagnostics = [*trace_result.diagnostics, *render_diags]
    return AnimationGenerationResult(
        request=trace_result.request,
        simulation_result=trace_result.simulation_result,
        trace=trace_result.trace,
        validation=trace_result.validation,
        paths=trace_result.paths,
        diagnostics=diagnostics,
        frames_dir=frames_dir,
        mp4_path=mp4_path,
        gif_path=gif_path,
    )


def generate_animation_from_openqasm(
    qasm: str,
    *,
    options: SimulationOptions | None = None,
    render: RenderOptions | None = None,
    artifacts: ArtifactOptions | None = None,
) -> AnimationGenerationResult:
    """Generate trace artifacts and rendered animation outputs from OpenQASM text."""
    trace_result = generate_trace_from_openqasm(qasm, options=options, artifacts=artifacts)
    resolved_render = render or RenderOptions()

    frames_dir, mp4_path, gif_path, render_diags = run_render_pipeline(
        trace_path=trace_result.paths.trace_json,
        render=resolved_render,
        out_dir=trace_result.paths.out_dir,
    )

    diagnostics = [*trace_result.diagnostics, *render_diags]
    return AnimationGenerationResult(
        request=trace_result.request,
        simulation_result=trace_result.simulation_result,
        trace=trace_result.trace,
        validation=trace_result.validation,
        paths=trace_result.paths,
        diagnostics=diagnostics,
        frames_dir=frames_dir,
        mp4_path=mp4_path,
        gif_path=gif_path,
    )
