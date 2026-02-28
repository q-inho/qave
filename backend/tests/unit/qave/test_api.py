# ruff: noqa: E501
"""Unit tests for qave.api orchestration helpers."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from qiskit import QuantumCircuit

import qave.api as api_module
from qave import ContractValidationError, InputValidationError
from qave.options import ArtifactOptions, RenderOptions, SimulationOptions
from qave.results import ArtifactPaths, DiagnosticEntry, TraceGenerationResult


def _fake_trace_result(tmp_path: Path) -> TraceGenerationResult:
    """Build a minimal trace result fixture rooted in a temporary directory."""
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    trace_path = out_dir / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")
    return TraceGenerationResult(
        request="request",  # type: ignore[arg-type]
        simulation_result="simulation_result",  # type: ignore[arg-type]
        trace="trace",  # type: ignore[arg-type]
        validation=None,
        paths=ArtifactPaths(out_dir=out_dir, trace_json=trace_path),
        diagnostics=[DiagnosticEntry(code="TRACE", message="ok", source="test")],
    )


def test_default_request_id_uses_current_time(monkeypatch) -> None:
    """Given fixed wall clock time, when building default request ID, then ID is deterministic."""
    monkeypatch.setattr(time, "time", lambda: 1234.567)
    assert api_module._default_request_id() == "qave_req_1234567"


def test_resolve_options_falls_back_to_dataclass_defaults() -> None:
    """Given missing options and artifacts, when resolving, then dataclass defaults are returned."""
    options, artifacts = api_module._resolve_options(None, None)
    assert options == SimulationOptions()
    assert artifacts == ArtifactOptions()


def test_build_request_maps_public_options_to_contract_model() -> None:
    """Given simulation options, when building request, then contract fields are mapped correctly."""
    request = api_module._build_request(
        SimulationOptions(
            algorithm_id="ghz",
            mode="validation",
            measurement_mode="collapse",
            seed=9,
            precision_profile="strict",
            animation_profile="analysis_slow",
            shot_count=128,
            request_id="req_abc",
            params={"qubits": 3},
        )
    )

    assert request.request_id == "req_abc"
    assert request.algorithm_id == "ghz"
    assert request.mode == "validation"
    assert request.animation_profile == "analysis_slow"
    assert request.shot_count == 128


def test_build_request_wraps_value_errors_as_contract_validation_error(monkeypatch) -> None:
    """Given contract model raises ValueError, when building request, then ContractValidationError is raised."""

    def _raise(*_args, **_kwargs):
        """Raise deterministic value error for request model construction."""
        raise ValueError("invalid request")

    monkeypatch.setattr(api_module, "SimulationRequest", _raise)

    with pytest.raises(ContractValidationError, match="Invalid simulation options"):
        api_module._build_request(SimulationOptions())


def test_write_trace_artifacts_writes_validation_when_enabled(tmp_path: Path) -> None:
    """Given validation payload and write flag, when writing artifacts, then validation JSON is emitted."""
    paths = api_module._write_trace_artifacts(
        out_dir=tmp_path,
        trace={"trace": True},
        simulation_result={"status": "ok"},
        validation={"pass": True},
        write_result_json=True,
        write_validation_json=True,
    )

    assert paths.trace_json.exists()
    assert paths.result_json is not None and paths.result_json.exists()
    assert paths.validation_json is not None and paths.validation_json.exists()


def test_generate_trace_from_qiskit_rejects_non_circuit() -> None:
    """Given non-circuit payload, when generating trace from Qiskit input, then validation error is raised."""
    with pytest.raises(InputValidationError, match="QuantumCircuit"):
        api_module.generate_trace_from_qiskit("not-a-circuit")


def test_generate_trace_from_openqasm_rejects_empty_payload() -> None:
    """Given empty OpenQASM payload, when generating trace, then validation error is raised."""
    with pytest.raises(InputValidationError, match="non-empty"):
        api_module.generate_trace_from_openqasm("")


def test_generate_trace_from_qiskit_wraps_import_errors(monkeypatch) -> None:
    """Given importer failure, when generating trace from Qiskit, then ValueError is wrapped."""

    def _raise(*_args, **_kwargs):
        """Raise deterministic importer failure."""
        raise ValueError("bad import")

    monkeypatch.setattr(api_module, "_trace_from_ir", _raise)
    with pytest.raises(InputValidationError, match="Qiskit circuit import failed"):
        api_module.generate_trace_from_qiskit(QuantumCircuit(1))


def test_generate_trace_from_openqasm_wraps_import_errors(monkeypatch) -> None:
    """Given importer failure, when generating trace from OpenQASM, then ValueError is wrapped."""

    def _raise(*_args, **_kwargs):
        """Raise deterministic importer failure."""
        raise ValueError("bad import")

    monkeypatch.setattr(api_module, "_trace_from_ir", _raise)
    with pytest.raises(InputValidationError, match="OpenQASM import failed"):
        api_module.generate_trace_from_openqasm("OPENQASM 2.0;")


def test_generate_animation_from_qiskit_uses_render_pipeline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given generated trace, when requesting animation, then render diagnostics are merged."""
    trace_result = _fake_trace_result(tmp_path)
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = tmp_path / "animation.mp4"
    mp4_path.write_bytes(b"")

    monkeypatch.setattr(api_module, "generate_trace_from_qiskit", lambda *_a, **_k: trace_result)

    def _fake_run_render_pipeline(*, trace_path: Path, render: RenderOptions, out_dir: Path):
        """Return deterministic render outputs for API animation tests."""
        assert trace_path == trace_result.paths.trace_json
        assert render.width == 1920
        assert render.height == 1080
        assert render.fps == 60
        assert out_dir == trace_result.paths.out_dir
        return frames_dir, mp4_path, None, [DiagnosticEntry(code="RENDER", message="ok")]

    monkeypatch.setattr(api_module, "run_render_pipeline", _fake_run_render_pipeline)

    result = api_module.generate_animation_from_qiskit(QuantumCircuit(1))
    assert result.frames_dir == frames_dir
    assert result.mp4_path == mp4_path
    assert [item.code for item in result.diagnostics] == ["TRACE", "RENDER"]


def test_generate_animation_from_openqasm_uses_render_pipeline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given generated OpenQASM trace, when requesting animation, then composed result is returned."""
    trace_result = _fake_trace_result(tmp_path)
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    gif_path = tmp_path / "animation.gif"

    monkeypatch.setattr(api_module, "generate_trace_from_openqasm", lambda *_a, **_k: trace_result)

    def _fake_run_render_pipeline(*, trace_path: Path, render: RenderOptions, out_dir: Path):
        """Return deterministic render outputs for OpenQASM animation path."""
        assert trace_path == trace_result.paths.trace_json
        assert out_dir == trace_result.paths.out_dir
        return frames_dir, None, gif_path, [DiagnosticEntry(code="RENDER", message="ok")]

    monkeypatch.setattr(api_module, "run_render_pipeline", _fake_run_render_pipeline)

    result = api_module.generate_animation_from_openqasm("OPENQASM 2.0;")
    assert result.frames_dir == frames_dir
    assert result.mp4_path is None
    assert result.gif_path == gif_path
    assert [item.code for item in result.diagnostics] == ["TRACE", "RENDER"]
