"""Internal runtime models for simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from qave_backend.contracts.models import GateOp


@dataclass(slots=True)
class StepSnapshot:
    """Represent Step Snapshot."""

    step_index: int
    gate: GateOp
    state_before: NDArray[np.complex128]
    state_after: NDArray[np.complex128]
    evolution_states: list[EvolutionState] = field(default_factory=list)
    measurement_execution: MeasurementExecution | None = None


@dataclass(slots=True)
class EvolutionState:
    """Represent Evolution State."""

    sample_index: int
    phase: Literal["pre_gate", "apply_gate", "settle"]
    t_normalized: float
    state: NDArray[np.complex128]
    gate_matrix: NDArray[np.complex128] | None = None


@dataclass(slots=True)
class MeasurementExecution:
    """Represent Measurement Execution."""

    qubits: list[int]
    outcomes: list[tuple[str, float]]
    selected_outcome: str | None
    deferred: bool = False


def canonicalize_global_phase(state: NDArray[np.complex128]) -> NDArray[np.complex128]:
    """Remove global phase by fixing first non-zero amplitude to a non-negative real value."""
    normalized = state.astype(np.complex128, copy=True)
    for amplitude in normalized:
        mag = np.abs(amplitude)
        if mag > 1e-15:
            normalized /= amplitude / mag
            break
    return normalized
