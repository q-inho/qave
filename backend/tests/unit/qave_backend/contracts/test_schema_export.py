# ruff: noqa: E501
"""Tests for contract schema export utilities and CLI wiring."""

from __future__ import annotations

import json
from pathlib import Path

from qave_backend.contracts import schema_export


def test_export_schemas_writes_required_schema_files(tmp_path: Path) -> None:
    """Given writable target directory, when exporting schemas, then canonical files are produced."""
    written = schema_export.export_schemas(tmp_path)
    names = {path.name for path in written}

    assert "SimulationRequest.schema.json" in names
    assert "SimulationResult.schema.json" in names
    assert "AlgorithmTrace.schema.json" in names


def test_algorithm_trace_schema_includes_evolution_samples_and_replay(tmp_path: Path) -> None:
    """Given exported algorithm schema, when loading JSON, then animation fields are present."""
    schema_export.export_schemas(tmp_path)
    schema_path = tmp_path / "AlgorithmTrace.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    step_schema = schema["$defs"]["TraceStep"]["properties"]
    assert "evolution_samples" in step_schema
    assert "operation_name" in step_schema
    assert "operation_qubits" in step_schema
    assert "operation_controls" in step_schema
    assert "operation_targets" in step_schema

    evolution_schema = schema["$defs"]["StepEvolutionSample"]["properties"]
    assert "gate_matrix" in evolution_schema
    assert "measurement_shot_replay" in schema["properties"]


def test_simulation_request_schema_includes_shot_count_and_custom_algorithm(tmp_path: Path) -> None:
    """Given exported request schema, when inspected, then shot_count and custom algorithm are supported."""
    schema_export.export_schemas(tmp_path)
    schema_path = tmp_path / "SimulationRequest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert "shot_count" in schema["properties"]
    integer_branch = next(
        option
        for option in schema["properties"]["shot_count"]["anyOf"]
        if option.get("type") == "integer"
    )
    assert integer_branch["minimum"] == 1
    assert "custom" in schema["properties"]["algorithm_id"]["enum"]


def test_resolve_repo_contracts_dir_finds_repo_root_from_nested_path(tmp_path: Path) -> None:
    """Given nested working directory, when locating repo contracts dir, then parent checkout is resolved."""
    repo_root = tmp_path / "repo"
    nested = repo_root / "backend" / "src"
    nested.mkdir(parents=True, exist_ok=True)
    changelog = repo_root / "contracts" / "CHANGELOG.md"
    changelog.parent.mkdir(parents=True, exist_ok=True)
    changelog.write_text("# changelog", encoding="utf-8")

    resolved = schema_export._resolve_repo_contracts_dir(nested)
    assert resolved == repo_root / "contracts" / "schemas"


def test_resolve_target_dir_prioritizes_explicit_then_repo_then_default(
    monkeypatch, tmp_path: Path
) -> None:
    """Given target resolution paths, when resolving output dir, then precedence is explicit > repo > cwd."""
    explicit = tmp_path / "explicit"
    assert schema_export._resolve_target_dir(explicit) == explicit

    repo_dir = tmp_path / "repo_contracts"
    monkeypatch.setattr(schema_export, "_resolve_repo_contracts_dir", lambda _cwd: repo_dir)
    assert schema_export._resolve_target_dir(None) == repo_dir

    monkeypatch.setattr(schema_export, "_resolve_repo_contracts_dir", lambda _cwd: None)
    monkeypatch.chdir(tmp_path)
    assert schema_export._resolve_target_dir(None) == tmp_path / "contracts" / "schemas"


def test_main_wires_cli_arguments_into_export(monkeypatch, tmp_path: Path) -> None:
    """Given CLI args, when running exporter main, then export receives parsed target path."""
    out_dir = tmp_path / "schemas"
    captured: list[Path] = []

    def _fake_export(path: Path) -> list[Path]:
        """Capture export path and return deterministic output list."""
        captured.append(path)
        return [path / "SimulationRequest.schema.json"]

    monkeypatch.setattr(schema_export, "export_schemas", _fake_export)
    schema_export.main(["--out-dir", str(out_dir)])

    assert captured == [out_dir]
