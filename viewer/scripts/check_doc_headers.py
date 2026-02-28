#!/usr/bin/env python3
"""Validate structured documentation headers for first-party non-Python files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HeaderRequirement:
    """Define required marker lines for a file family."""

    label: str
    glob_pattern: str
    markers: tuple[str, ...]


REQUIREMENTS = (
    HeaderRequirement(
        label="Processing",
        glob_pattern="viewer/processing_qave/*.pde",
        markers=("Purpose:", "Inputs:", "Outputs:", "Determinism/Timing:"),
    ),
    HeaderRequirement(
        label="Shell",
        glob_pattern="viewer/scripts/*.sh",
        markers=("Purpose:", "Inputs:", "Outputs:", "Usage:"),
    ),
)


def read_header_window(path: Path, *, max_lines: int = 60) -> str:
    """Read the header scan window from a file.

    Args:
        path: File path to read.
        max_lines: Maximum number of initial lines to inspect.

    Returns:
        The concatenated text from the leading header window.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[:max_lines])


def find_missing_markers(header_text: str, markers: tuple[str, ...]) -> list[str]:
    """Collect required header markers that are not present.

    Args:
        header_text: Leading file text used for header validation.
        markers: Required marker strings.

    Returns:
        A list of missing markers.
    """
    return [marker for marker in markers if marker not in header_text]


def validate_requirement(root: Path, requirement: HeaderRequirement) -> list[str]:
    """Validate files for one requirement group.

    Args:
        root: Repository root directory.
        requirement: File family and marker specification.

    Returns:
        A list of validation failures.
    """
    failures: list[str] = []
    for path in sorted(root.glob(requirement.glob_pattern)):
        header_text = read_header_window(path)
        missing = find_missing_markers(header_text, requirement.markers)
        if missing:
            failures.append(
                f"{path}: missing {', '.join(missing)} ({requirement.label} header requirement)"
            )
    return failures


def validate_headers(root: Path) -> list[str]:
    """Validate all configured structured-header requirements.

    Args:
        root: Repository root directory.

    Returns:
        A list of all validation failures.
    """
    failures: list[str] = []
    for requirement in REQUIREMENTS:
        failures.extend(validate_requirement(root, requirement))
    return failures


def main() -> int:
    """Run structured-header checks and return a process exit code."""
    parser = argparse.ArgumentParser(
        description="Validate structured header comments for first-party PDE and shell files."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path (defaults to current working directory).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures = validate_headers(root)
    if failures:
        print("Structured-header validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Structured-header validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
