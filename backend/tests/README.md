# Testing

Run all repo quality gates:

```bash
uvx tox
```

Run a specific gate:

- `uvx tox -e format`: auto-format Python and viewer script files via ruff format
- `uvx tox -e lint`: ruff + documentation/header checks
- `uvx tox -e type`: mypy checks for `backend/src` and `backend/tests`
- `uvx tox -e py`: backend unit/integration tests (Python 3.12)
- `uvx tox -e coverage`: backend tests + coverage threshold (`--fail-under=90`)
- `uvx tox -e spell`: repository-wide spelling checks using typos
- `uvx tox -e schemas`: export schemas and ensure `contracts/schemas/` is committed
- `uvx tox -e viewer-smoke`: deterministic Processing viewer smoke checks (Linux CI)

## Pre-commit

Install the git hook (requires `pre-commit`; installed by `uv sync --project backend --extra dev`):

```bash
uv sync --project backend --extra dev
uv run --project backend --extra dev pre-commit install
```

Run locally:

```bash
uv run --project backend --extra dev pre-commit run --all-files
```

## Backend test organization policy

This test suite is organized by domain to keep behavior coverage clear and maintainable.

## Structure

- `unit/qave/`: package-level API, options, rendering, notebook, and IO behavior.
- `unit/qave_backend/contracts/`: contract model and schema export behavior.
- `unit/qave_backend/ingest/`: OpenQASM and Qiskit ingestion behavior.
- `unit/qave_backend/simulator/`: gate math and statevector engine behavior.
- `unit/qave_backend/observables/`: observable extraction behavior.
- `unit/qave_backend/measurement/`: measurement-model shaping behavior.
- `unit/qave_backend/validation/`: parity helper and numerical utility behavior.
- `integration/api/`: end-to-end package API workflows.
- `integration/backend_a/`: end-to-end backend simulation and measurement workflows.
