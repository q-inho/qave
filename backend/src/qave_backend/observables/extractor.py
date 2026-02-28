"""Observable extraction for state snapshots."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from qave_backend.contracts.models import (
    BipartitionEntropy,
    BlochVector,
    EntanglementMetrics,
    MeasurementHistogramEntry,
    MutualInformationEdge,
    ObservableSnapshot,
    PurityEntropy,
    ReducedDensityBlock,
    ScalabilityPolicy,
    TopKAmplitude,
)


def _basis_label(index: int, num_qubits: int) -> str:
    """Format a basis-state index as a fixed-width binary label."""
    return format(index, f"0{num_qubits}b")


def _reduced_density_matrix(
    state: NDArray[np.complex128],
    num_qubits: int,
    subsystem_qubits: list[int],
) -> NDArray[np.complex128]:
    """Compute a subsystem reduced density matrix by tracing out the environment."""
    subsystem_axes = [num_qubits - 1 - qubit for qubit in subsystem_qubits]
    env_axes = [axis for axis in range(num_qubits) if axis not in subsystem_axes]

    tensor = state.reshape((2,) * num_qubits)
    permutation = subsystem_axes + env_axes
    reordered = np.transpose(tensor, permutation)

    dim_sub = 2 ** len(subsystem_qubits)
    flattened = reordered.reshape(dim_sub, -1)
    return flattened @ flattened.conj().T


def _full_density_matrix(state: NDArray[np.complex128]) -> NDArray[np.complex128]:
    """Compute full-system density matrix from a pure state vector."""
    return np.outer(state, state.conj())


def _von_neumann_entropy(rho: NDArray[np.complex128]) -> float:
    """Compute Von Neumann entropy from a density matrix eigenvalue spectrum."""
    eigenvalues = np.clip(np.real(np.linalg.eigvalsh(rho)), 0.0, 1.0)
    entropy = 0.0
    for value in eigenvalues:
        if value > 1e-15:
            entropy -= float(value * math.log2(value))
    return entropy


class ObservableExtractor:
    """Builds compact observable snapshots from pure states."""

    def extract(
        self,
        state: NDArray[np.complex128],
        step_index: int,
        policy: ScalabilityPolicy,
    ) -> ObservableSnapshot:
        """Extract."""
        num_qubits = round(math.log2(state.shape[0]))
        probabilities = np.abs(state) ** 2

        bloch_vectors: list[BlochVector] = []
        purity_entropy: list[PurityEntropy] = []
        single_entropies: dict[int, float] = {}

        for qubit in range(num_qubits):
            rho = _reduced_density_matrix(state, num_qubits, [qubit])
            rho00 = rho[0, 0]
            rho11 = rho[1, 1]
            rho01 = rho[0, 1]

            x = 2.0 * float(np.real(rho01))
            y = -2.0 * float(np.imag(rho01))
            z = float(np.real(rho00 - rho11))

            bloch_vectors.append(BlochVector(qubit=qubit, x=x, y=y, z=z))

            purity = float(np.real(np.trace(rho @ rho)))
            entropy = _von_neumann_entropy(rho)
            single_entropies[qubit] = entropy
            purity_entropy.append(PurityEntropy(qubit=qubit, purity=purity, entropy=entropy))

        if num_qubits <= policy.small_n_max:
            top_k = min(2**num_qubits, 32)
        elif num_qubits <= policy.medium_n_max:
            top_k = min(2**num_qubits, 16)
        else:
            top_k = min(2**num_qubits, 8)

        top_indices = np.argsort(probabilities)[::-1][:top_k]
        top_k_amplitudes: list[TopKAmplitude] = []
        for idx in top_indices:
            amplitude = state[int(idx)]
            top_k_amplitudes.append(
                TopKAmplitude(
                    basis=_basis_label(int(idx), num_qubits),
                    magnitude=float(np.abs(amplitude)),
                    phase=float(np.angle(amplitude)),
                )
            )

        rho_full = _full_density_matrix(state)
        reduced_density_blocks = [
            ReducedDensityBlock(
                qubits=list(range(num_qubits)),
                real=np.real(rho_full).tolist(),
                imag=np.imag(rho_full).tolist(),
            )
        ]

        mutual_information_edges: list[MutualInformationEdge] = []
        if num_qubits <= 8:
            for i in range(num_qubits):
                for j in range(i + 1, num_qubits):
                    rho_ij = _reduced_density_matrix(state, num_qubits, [i, j])
                    s_ij = _von_neumann_entropy(rho_ij)
                    mi = single_entropies[i] + single_entropies[j] - s_ij
                    mutual_information_edges.append(
                        MutualInformationEdge(i=i, j=j, value=float(mi))
                    )

        bipartition_entropy: list[BipartitionEntropy] = []
        if num_qubits >= 2:
            split = num_qubits // 2
            left = list(range(split))
            right = list(range(split, num_qubits))
            if left and right:
                rho_left = _reduced_density_matrix(state, num_qubits, left)
                bipartition_entropy.append(
                    BipartitionEntropy(
                        left=left,
                        right=right,
                        value=_von_neumann_entropy(rho_left),
                    )
                )

        hist_limit = min(2**num_qubits, 64)
        hist_indices = np.argsort(probabilities)[::-1][:hist_limit]
        histogram = [
            MeasurementHistogramEntry(
                outcome=_basis_label(int(idx), num_qubits),
                probability=float(probabilities[int(idx)]),
                samples=None,
            )
            for idx in hist_indices
        ]

        return ObservableSnapshot(
            snapshot_id=f"snapshot_{step_index}",
            step_index=step_index,
            bloch_vectors=bloch_vectors,
            purity_entropy=purity_entropy,
            top_k_amplitudes=top_k_amplitudes,
            reduced_density_blocks=reduced_density_blocks,
            entanglement_metrics=EntanglementMetrics(
                mutual_information_edges=mutual_information_edges,
                bipartition_entropy=bipartition_entropy,
            ),
            measurement_histogram=histogram,
        )
