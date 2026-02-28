"""Artifact IO helpers for qave APIs."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from qave.errors import ArtifactIOError


def to_serializable(obj: Any) -> Any:
    """Convert pydantic models to JSON-serializable python objects."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    return obj


def ensure_out_dir(path: Path) -> Path:
    """Create and return the output directory."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        msg = f"Unable to create output directory: {path}"
        raise ArtifactIOError(msg) from exc
    return path


def _sanitize_request_id(request_id: str) -> str:
    """Sanitize request id for safe filesystem directory names."""
    safe_request_id = re.sub(r"[^A-Za-z0-9._-]", "_", request_id).strip("._-")
    if not safe_request_id:
        return "request"
    return safe_request_id


def resolve_out_dir(*, explicit_out_dir: Path | None, request_id: str) -> Path:
    """Resolve output directory from explicit option, env var, or default policy."""
    if explicit_out_dir is not None:
        return explicit_out_dir.expanduser().resolve()

    env_out_dir = os.getenv("QAVE_OUT_DIR", "").strip()
    if env_out_dir:
        return Path(env_out_dir).expanduser().resolve()

    safe_request_id = _sanitize_request_id(request_id)
    return (Path.cwd() / "qave_artifacts" / safe_request_id).expanduser().resolve()


def write_json(path: Path, payload: Any) -> Path:
    """Write JSON with canonical formatting for artifacts."""
    try:
        path.write_text(json.dumps(to_serializable(payload), indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        msg = f"Unable to write JSON artifact: {path}"
        raise ArtifactIOError(msg) from exc
    return path
