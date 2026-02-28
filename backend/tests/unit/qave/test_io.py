# ruff: noqa: E501
"""Tests for qave artifact IO helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qave.errors import ArtifactIOError
from qave.io import ensure_out_dir, resolve_out_dir, to_serializable, write_json
from qave_backend.contracts.models import SimulationRequest


def _request() -> SimulationRequest:
    """Build a minimal request fixture for IO serialization checks."""
    return SimulationRequest(
        contract_version="0.1.0",
        request_id="req_io",
        algorithm_id="bell",
        mode="preview",
        seed=1,
        precision_profile="balanced",
        measurement_mode="collapse",
        animation_profile="teaching_default",
    )


def test_to_serializable_converts_pydantic_models() -> None:
    """Given pydantic model payload, when serialized, then dict output is produced."""
    payload = to_serializable(_request())
    assert isinstance(payload, dict)
    assert payload["request_id"] == "req_io"


def test_resolve_out_dir_prefers_explicit_path(monkeypatch, tmp_path: Path) -> None:
    """Given explicit out_dir, when resolving path, then explicit path takes priority."""
    monkeypatch.setenv("QAVE_OUT_DIR", str(tmp_path / "env"))
    explicit = tmp_path / "explicit"

    resolved = resolve_out_dir(explicit_out_dir=explicit, request_id="req")
    assert resolved == explicit.resolve()


def test_resolve_out_dir_uses_env_override_when_explicit_missing(
    monkeypatch, tmp_path: Path
) -> None:
    """Given env override, when explicit out_dir is missing, then env path is returned."""
    env_out_dir = tmp_path / "env"
    monkeypatch.setenv("QAVE_OUT_DIR", str(env_out_dir))

    resolved = resolve_out_dir(explicit_out_dir=None, request_id="req")
    assert resolved == env_out_dir.resolve()


def test_resolve_out_dir_sanitizes_request_id_for_default_path(monkeypatch, tmp_path: Path) -> None:
    """Given request ID with separators, when resolving default path, then it is sanitized."""
    monkeypatch.delenv("QAVE_OUT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    resolved = resolve_out_dir(explicit_out_dir=None, request_id="seed 42/ghz demo")
    assert resolved == (tmp_path / "qave_artifacts" / "seed_42_ghz_demo").resolve()


def test_ensure_out_dir_wraps_os_errors(monkeypatch, tmp_path: Path) -> None:
    """Given mkdir failure, when ensuring out_dir, then ArtifactIOError is raised."""
    target = tmp_path / "blocked"

    def _raise(*_args, **_kwargs):
        """Raise deterministic OSError for mkdir call."""
        raise OSError("mkdir failed")

    monkeypatch.setattr(Path, "mkdir", _raise)
    with pytest.raises(ArtifactIOError, match="Unable to create output directory"):
        ensure_out_dir(target)


def test_write_json_writes_canonical_pretty_json(tmp_path: Path) -> None:
    """Given serializable payload, when writing JSON, then newline-terminated pretty file is created."""
    out_file = tmp_path / "payload.json"
    written = write_json(out_file, _request())

    text = written.read_text(encoding="utf-8")
    assert written == out_file
    assert text.endswith("\n")
    data = json.loads(text)
    assert data["request_id"] == "req_io"


def test_write_json_wraps_os_errors(monkeypatch, tmp_path: Path) -> None:
    """Given write_text failure, when writing JSON, then ArtifactIOError is raised."""
    out_file = tmp_path / "payload.json"

    def _raise(*_args, **_kwargs):
        """Raise deterministic OSError for write_text call."""
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _raise)
    with pytest.raises(ArtifactIOError, match="Unable to write JSON artifact"):
        write_json(out_file, {"ok": True})
