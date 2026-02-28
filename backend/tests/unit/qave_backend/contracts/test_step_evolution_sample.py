"""Tests for `StepEvolutionSample` contract behavior."""

from __future__ import annotations

from qave_backend.contracts.models import GateMatrixSample, StepEvolutionSample


def test_step_evolution_sample_accepts_optional_gate_matrix() -> None:
    """Given sample payload variants, when parsing contract, then gate_matrix remains optional."""
    with_matrix = StepEvolutionSample(
        sample_index=0,
        phase="apply_gate",
        t_normalized=0.5,
        state_hash="state_hash",
        top_k_amplitudes=[],
        reduced_density_blocks=[],
        measurement_histogram=[],
        gate_matrix=GateMatrixSample(
            gate_name="h",
            qubits=[0],
            real=[[1.0, 0.0], [0.0, 1.0]],
            imag=[[0.0, 0.0], [0.0, 0.0]],
        ),
    )
    without_matrix = StepEvolutionSample(
        sample_index=0,
        phase="apply_gate",
        t_normalized=0.5,
        state_hash="state_hash",
        top_k_amplitudes=[],
        reduced_density_blocks=[],
        measurement_histogram=[],
    )

    assert with_matrix.gate_matrix is not None
    assert with_matrix.gate_matrix.gate_name == "h"
    assert without_matrix.gate_matrix is None
