"""Schema export utility for public contract models.

This module is used in two contexts:

- Repository development: export schemas into the repo's `contracts/schemas/` directory.
- Installed package usage: export schemas into a caller-chosen directory.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from qave_backend.contracts.models import (
    AlgorithmTrace,
    BackendCapability,
    MeasurementModel,
    ObservableSnapshot,
    QuantumCircuitIR,
    ScalabilityPolicy,
    SimulationRequest,
    SimulationResult,
    ValidationReport,
)

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "QuantumCircuitIR": QuantumCircuitIR,
    "SimulationRequest": SimulationRequest,
    "SimulationResult": SimulationResult,
    "AlgorithmTrace": AlgorithmTrace,
    "ObservableSnapshot": ObservableSnapshot,
    "MeasurementModel": MeasurementModel,
    "ScalabilityPolicy": ScalabilityPolicy,
    "BackendCapability": BackendCapability,
    "ValidationReport": ValidationReport,
}


def export_schemas(target_dir: Path) -> list[Path]:
    """Export schemas."""
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for name, model in SCHEMA_MODELS.items():
        schema_path = target_dir / f"{name}.schema.json"
        schema = model.model_json_schema(by_alias=True)
        schema_path.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(schema_path)

    return written


def _resolve_repo_contracts_dir(cwd: Path) -> Path | None:
    """Return the repo `contracts/schemas` directory when running inside a checkout.

    Args:
        cwd: Current working directory.

    Returns:
        The resolved `contracts/schemas` path if `contracts/CHANGELOG.md` is found in `cwd`
        or an ancestor directory; otherwise `None`.
    """
    for candidate in [cwd, *cwd.parents]:
        changelog = candidate / "contracts" / "CHANGELOG.md"
        if changelog.exists():
            return candidate / "contracts" / "schemas"
    return None


def _resolve_target_dir(out_dir: Path | None) -> Path:
    """Resolve the target directory for schema export.

    Args:
        out_dir: Optional explicit output directory.

    Returns:
        A directory path to write schema JSON files into.
    """
    if out_dir is not None:
        return out_dir

    cwd = Path.cwd().resolve()
    repo_contracts = _resolve_repo_contracts_dir(cwd)
    if repo_contracts is not None:
        return repo_contracts

    return cwd / "contracts" / "schemas"


def main(argv: Sequence[str] | None = None) -> None:
    """Export all contract schemas."""
    parser = argparse.ArgumentParser(prog="qave-export-schemas")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=(
            "Directory to write schema JSON files into. "
            "When omitted, the exporter writes to the repository `contracts/schemas/` "
            "directory when executed inside a repo checkout; otherwise it writes to "
            "`./contracts/schemas/` under the current working directory."
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    target = _resolve_target_dir(args.out_dir)
    written = export_schemas(target)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
