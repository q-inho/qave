# ruff: noqa: E501
"""Tests for observable extraction behavior and invariants."""

from __future__ import annotations

import numpy as np

from qave_backend.contracts.models import ApproximationPolicy, ScalabilityPolicy
from qave_backend.observables.extractor import ObservableExtractor


def _policy() -> ScalabilityPolicy:
    """Build deterministic scalability policy fixture for observable tests."""
    return ScalabilityPolicy(
        small_n_max=8,
        medium_n_max=16,
        small_mode_features=["full"],
        medium_mode_features=["topk"],
        large_mode_features=["reduced"],
        approximation_policy=ApproximationPolicy(
            allow_approx_backends=True,
            fallback_backend_order=["statevector"],
        ),
    )


def test_bell_snapshot_captures_local_mixedness_and_density_block() -> None:
    """Given Bell state, when extracting observables, then local purity and full density are correct."""
    state = np.zeros(4, dtype=np.complex128)
    state[0] = 1 / np.sqrt(2)
    state[3] = 1 / np.sqrt(2)

    snapshot = ObservableExtractor().extract(state, step_index=0, policy=_policy())

    assert len(snapshot.bloch_vectors) == 2
    assert abs(snapshot.bloch_vectors[0].z) < 1e-9
    assert abs(snapshot.bloch_vectors[1].z) < 1e-9

    assert len(snapshot.purity_entropy) == 2
    for item in snapshot.purity_entropy:
        assert np.isclose(item.purity, 0.5, atol=1e-9)

    full_block = snapshot.reduced_density_blocks[0]
    rho = np.array(full_block.real) + 1j * np.array(full_block.imag)
    assert full_block.qubits == [0, 1]
    assert rho.shape == (4, 4)
    assert np.allclose(rho, rho.conj().T, atol=1e-9)
    assert np.isclose(np.trace(rho), 1.0, atol=1e-9)


def test_observables_are_global_phase_invariant() -> None:
    """Given globally phase-shifted equivalent states, when extracting observables, then values match."""
    state = np.array([0.5 + 0.5j, 0.5 - 0.5j], dtype=np.complex128)
    phased = state * np.exp(1j * 0.87)

    extractor = ObservableExtractor()
    original = extractor.extract(state, step_index=0, policy=_policy())
    shifted = extractor.extract(phased, step_index=0, policy=_policy())

    assert np.allclose(
        [entry.probability for entry in original.measurement_histogram],
        [entry.probability for entry in shifted.measurement_histogram],
    )
    assert np.allclose(
        [entry.magnitude for entry in original.top_k_amplitudes],
        [entry.magnitude for entry in shifted.top_k_amplitudes],
    )


def test_ghz_snapshot_contains_full_density_block_for_three_qubits() -> None:
    """Given GHZ state, when extracting observables, then full-system density payload is present."""
    state = np.zeros(8, dtype=np.complex128)
    state[0] = 1 / np.sqrt(2)
    state[7] = 1 / np.sqrt(2)

    snapshot = ObservableExtractor().extract(state, step_index=0, policy=_policy())
    full_block = snapshot.reduced_density_blocks[0]
    rho = np.array(full_block.real) + 1j * np.array(full_block.imag)

    assert full_block.qubits == [0, 1, 2]
    assert rho.shape == (8, 8)
    assert np.allclose(rho, rho.conj().T, atol=1e-9)
    assert np.isclose(np.trace(rho), 1.0, atol=1e-9)
