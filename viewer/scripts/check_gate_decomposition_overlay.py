#!/usr/bin/env python3
"""Validate gate-action decomposition overlay math against trace payloads."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def is_rectangular(real: Any, imag: Any) -> bool:
    """Return whether rectangular.

    Args:
        real: Input value for this computation.
        imag: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    if not isinstance(real, list) or not isinstance(imag, list):
        return False
    if not real or not imag or len(real) != len(imag):
        return False
    cols = len(real[0]) if isinstance(real[0], list) else 0
    if cols <= 0:
        return False
    for row in range(len(real)):
        if not isinstance(real[row], list) or not isinstance(imag[row], list):
            return False
        if len(real[row]) != cols or len(imag[row]) != cols:
            return False
    return True


def is_square(real: Any, imag: Any) -> bool:
    """Return whether square.

    Args:
        real: Input value for this computation.
        imag: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    if not is_rectangular(real, imag):
        return False
    return len(real) == len(real[0])


def is_power_of_two(value: int) -> bool:
    """Return whether power of two.

    Args:
        value: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    return value > 0 and (value & (value - 1)) == 0


def normalize_gate_name(value: str) -> str:
    """Normalize gate name.

    Args:
        value: Input value for this computation.

    Returns:
        The computed string value.
    """
    return "".join(ch for ch in value.lower() if ch.isalnum())


def is_nonunitary_gate_name(name: str) -> bool:
    """Return whether nonunitary gate name.

    Args:
        name: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    return name in {"measure", "m", "reset"}


def block_qubit_key(block: dict[str, Any]) -> str:
    """Compute block qubit key.

    Args:
        block: Input value for this computation.

    Returns:
        The computed string value.
    """
    qubits = block.get("qubits") or []
    if not isinstance(qubits, list):
        return ""
    return ",".join(str(item) for item in qubits)


def select_preferred_block(blocks: Any) -> dict[str, Any] | None:
    """Select preferred block.

    Args:
        blocks: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    if not isinstance(blocks, list) or not blocks:
        return None

    largest: dict[str, Any] | None = None
    largest_span = -1
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if not is_rectangular(block.get("real"), block.get("imag")):
            continue
        qubits = block.get("qubits") or []
        span = len(qubits) if isinstance(qubits, list) else 0
        if span > largest_span:
            largest_span = span
            largest = block
    if largest is not None:
        return largest

    for block in blocks:
        if isinstance(block, dict) and block_qubit_key(block) == "0,1":
            return block
    for block in blocks:
        if isinstance(block, dict) and block_qubit_key(block) == "0":
            return block
    return blocks[0] if isinstance(blocks[0], dict) else None


def select_matching_block(blocks: Any, active_block: dict[str, Any]) -> dict[str, Any] | None:
    """Select matching block.

    Args:
        blocks: Input value for this computation.
        active_block: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    if not isinstance(blocks, list):
        return None
    active_key = block_qubit_key(active_block)
    rows = len(active_block["real"])
    cols = len(active_block["real"][0])
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if not is_rectangular(block.get("real"), block.get("imag")):
            continue
        if len(block["real"]) != rows or len(block["real"][0]) != cols:
            continue
        if block_qubit_key(block) == active_key:
            return block
    return None


def is_earlier_sample(candidate: dict[str, Any], current: dict[str, Any] | None) -> bool:
    """Return whether earlier sample.

    Args:
        candidate: Input value for this computation.
        current: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    if current is None:
        return True
    candidate_t = float(candidate.get("t_normalized", 0.0))
    current_t = float(current.get("t_normalized", 0.0))
    if candidate_t < current_t - 1e-6:
        return True
    if candidate_t > current_t + 1e-6:
        return False
    candidate_idx = int(candidate.get("sample_index", 0))
    current_idx = int(current.get("sample_index", 0))
    return candidate_idx < current_idx


def resolve_gate_start_block(
    step: dict[str, Any], active_block: dict[str, Any]
) -> dict[str, Any] | None:
    """Resolve gate start block.

    Args:
        step: Input value for this computation.
        active_block: Input value for this computation.

    Returns:
        The computed mapping value.
    """
    samples = step.get("evolution_samples") or []
    if not isinstance(samples, list):
        return None

    earliest_pre: dict[str, Any] | None = None
    earliest_any: dict[str, Any] | None = None
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        block = select_matching_block(sample.get("reduced_density_blocks"), active_block)
        if block is None:
            continue
        if is_earlier_sample(sample, earliest_any):
            earliest_any = sample
        if str(sample.get("phase", "")) == "pre_gate" and is_earlier_sample(sample, earliest_pre):
            earliest_pre = sample

    selected = earliest_pre if earliest_pre is not None else earliest_any
    if selected is None:
        return None
    return select_matching_block(selected.get("reduced_density_blocks"), active_block)


def index_of_qubit(qubits: list[int], target: int) -> int:
    """Compute index of qubit.

    Args:
        qubits: Input value for this computation.
        target: Input value for this computation.

    Returns:
        The computed integer value.
    """
    for idx, qubit in enumerate(qubits):
        if int(qubit) == int(target):
            return idx
    return -1


def basis_bit(index: int, block_qubit_count: int, block_position: int) -> int:
    """Compute basis bit.

    Args:
        index: Input value for this computation.
        block_qubit_count: Input value for this computation.
        block_position: Input value for this computation.

    Returns:
        The computed integer value.
    """
    del block_qubit_count  # qubit positions are little-endian in the exported basis index
    return (index >> max(0, block_position)) & 1


def local_basis_index(index: int, block_qubit_count: int, gate_positions: list[int]) -> int:
    """Compute local basis index.

    Args:
        index: Input value for this computation.
        block_qubit_count: Input value for this computation.
        gate_positions: Input value for this computation.

    Returns:
        The computed integer value.
    """
    local = 0
    for block_position in gate_positions:
        local = (local << 1) | basis_bit(index, block_qubit_count, block_position)
    return local


def complex_mul(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Compute complex mul.

    Args:
        a: Input value for this computation.
        b: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def complex_conj(a: tuple[float, float]) -> tuple[float, float]:
    """Compute complex conj.

    Args:
        a: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    return (a[0], -a[1])


def complex_abs(a: tuple[float, float]) -> float:
    """Compute complex abs.

    Args:
        a: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    return math.sqrt(a[0] * a[0] + a[1] * a[1])


def embed_gate_matrix(
    gate_matrix: dict[str, Any], active_block: dict[str, Any]
) -> list[list[tuple[float, float]]] | None:
    """Compute embed gate matrix.

    Args:
        gate_matrix: Input value for this computation.
        active_block: Input value for this computation.

    Returns:
        The computed list value.
    """
    gate_real = gate_matrix.get("real")
    gate_imag = gate_matrix.get("imag")
    if not is_square(gate_real, gate_imag):
        return None

    block_real = active_block.get("real")
    block_imag = active_block.get("imag")
    if not is_square(block_real, block_imag):
        return None

    block_dim = len(block_real)
    block_qubits = [int(item) for item in active_block.get("qubits") or []]
    block_qubit_count = len(block_qubits)
    if block_dim != (1 << max(0, block_qubit_count)):
        return None

    gate_qubits = [int(item) for item in gate_matrix.get("qubits") or []]
    local_dim = len(gate_real)
    if local_dim != (1 << max(0, len(gate_qubits))):
        return None

    gate_positions: list[int] = []
    used_positions: set[int] = set()
    for gate_qubit in gate_qubits:
        pos = index_of_qubit(block_qubits, gate_qubit)
        if pos < 0 or pos in used_positions:
            return None
        gate_positions.append(pos)
        used_positions.add(pos)

    embedded: list[list[tuple[float, float]]] = [
        [(0.0, 0.0) for _ in range(block_dim)] for _ in range(block_dim)
    ]
    for row in range(block_dim):
        for col in range(block_dim):
            env_match = True
            for block_position in range(block_qubit_count):
                if block_position in used_positions:
                    continue
                if basis_bit(row, block_qubit_count, block_position) != basis_bit(
                    col,
                    block_qubit_count,
                    block_position,
                ):
                    env_match = False
                    break
            if not env_match:
                continue

            local_row = local_basis_index(row, block_qubit_count, gate_positions)
            local_col = local_basis_index(col, block_qubit_count, gate_positions)
            embedded[row][col] = (
                float(gate_real[local_row][local_col]),
                float(gate_imag[local_row][local_col]),
            )
    return embedded


def is_approximately_unitary(matrix: list[list[tuple[float, float]]], eps: float) -> bool:
    """Return whether approximately unitary.

    Args:
        matrix: Input value for this computation.
        eps: Input value for this computation.

    Returns:
        True when the condition is met; otherwise False.
    """
    if not matrix or len(matrix) != len(matrix[0]):
        return False
    dim = len(matrix)
    for i in range(dim):
        for j in range(dim):
            sum_re = 0.0
            sum_im = 0.0
            for k in range(dim):
                aik = matrix[i][k]
                ajk = matrix[j][k]
                sum_re += aik[0] * ajk[0] + aik[1] * ajk[1]
                sum_im += aik[1] * ajk[0] - aik[0] * ajk[1]
            target_re = 1.0 if i == j else 0.0
            err = math.sqrt((sum_re - target_re) ** 2 + sum_im**2)
            if err > eps:
                return False
    return True


def predict_density(
    embedded: list[list[tuple[float, float]]],
    start_block: dict[str, Any],
) -> list[list[tuple[float, float]]]:
    """Compute predict density.

    Args:
        embedded: Input value for this computation.
        start_block: Input value for this computation.

    Returns:
        The computed list value.
    """
    dim = len(embedded)
    start_real = start_block["real"]
    start_imag = start_block["imag"]
    predicted: list[list[tuple[float, float]]] = [
        [(0.0, 0.0) for _ in range(dim)] for _ in range(dim)
    ]
    for i in range(dim):
        for j in range(dim):
            sum_re = 0.0
            sum_im = 0.0
            for a in range(dim):
                for b in range(dim):
                    kia = embedded[i][a]
                    rho_ab = (float(start_real[a][b]), float(start_imag[a][b]))
                    kjb = embedded[j][b]
                    first = complex_mul(kia, rho_ab)
                    term = complex_mul(first, complex_conj(kjb))
                    sum_re += term[0]
                    sum_im += term[1]
            predicted[i][j] = (sum_re, sum_im)
    return predicted


def normalize_density_if_needed(
    predicted: list[list[tuple[float, float]]],
    eps: float,
) -> tuple[list[list[tuple[float, float]]], float]:
    """Normalize density if needed.

    Args:
        predicted: Input value for this computation.
        eps: Input value for this computation.

    Returns:
        The computed tuple value.
    """
    dim = len(predicted)
    trace_real = sum(predicted[i][i][0] for i in range(dim))
    if trace_real <= eps:
        return predicted, trace_real
    inv_trace = 1.0 / trace_real
    normalized: list[list[tuple[float, float]]] = [
        [(cell[0] * inv_trace, cell[1] * inv_trace) for cell in row] for row in predicted
    ]
    return normalized, trace_real


def max_complex_error(
    predicted: list[list[tuple[float, float]]], active_block: dict[str, Any]
) -> float:
    """Return the maximum complex error.

    Args:
        predicted: Input value for this computation.
        active_block: Input value for this computation.

    Returns:
        The computed floating-point value.
    """
    dim = len(predicted)
    active_real = active_block["real"]
    active_imag = active_block["imag"]
    max_err = 0.0
    for i in range(dim):
        for j in range(dim):
            diff_re = predicted[i][j][0] - float(active_real[i][j])
            diff_im = predicted[i][j][1] - float(active_imag[i][j])
            max_err = max(max_err, math.sqrt(diff_re * diff_re + diff_im * diff_im))
    return max_err


def main() -> None:
    """Run the script entry point."""
    parser = argparse.ArgumentParser(
        description="Validate gate-action decomposition overlay math against a trace."
    )
    parser.add_argument("--trace", required=True, help="Path to trace.json")
    parser.add_argument(
        "--tol", type=float, default=5e-4, help="Max per-cell complex error tolerance"
    )
    parser.add_argument(
        "--unitary-eps",
        type=float,
        default=2e-3,
        help="Tolerance for unitarity check on embedded operator",
    )
    parser.add_argument(
        "--eps", type=float, default=1e-8, help="Small epsilon for normalization checks"
    )
    args = parser.parse_args()

    trace_path = Path(args.trace)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    steps = trace.get("steps") or []
    if not isinstance(steps, list) or not steps:
        raise SystemExit(f"[error] No steps found in {trace_path}")

    checked = 0
    max_error = 0.0
    normalized_nonunitary_checked = 0
    skipped = 0

    for step_index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        samples = step.get("evolution_samples") or []
        if not isinstance(samples, list):
            continue

        for sample in samples:
            if not isinstance(sample, dict):
                continue
            if str(sample.get("phase", "")) != "apply_gate":
                continue

            active_block = select_preferred_block(sample.get("reduced_density_blocks"))
            if active_block is None:
                skipped += 1
                continue
            if not is_square(active_block.get("real"), active_block.get("imag")):
                skipped += 1
                continue
            dim = len(active_block["real"])
            if dim > 8 or not is_power_of_two(dim):
                skipped += 1
                continue

            gate_matrix = sample.get("gate_matrix")
            if not isinstance(gate_matrix, dict):
                skipped += 1
                continue
            if not is_square(gate_matrix.get("real"), gate_matrix.get("imag")):
                skipped += 1
                continue

            gate_qubits = gate_matrix.get("qubits") or []
            block_qubits = active_block.get("qubits") or []
            if not all(int(q) in [int(bq) for bq in block_qubits] for q in gate_qubits):
                skipped += 1
                continue

            start_block = resolve_gate_start_block(step, active_block)
            if start_block is None:
                skipped += 1
                continue

            embedded = embed_gate_matrix(gate_matrix, active_block)
            if embedded is None:
                skipped += 1
                continue

            predicted_raw = predict_density(embedded, start_block)
            predicted = predicted_raw

            gate_name = normalize_gate_name(str(gate_matrix.get("gate_name", "")))
            nonunitary = is_nonunitary_gate_name(gate_name) or not is_approximately_unitary(
                embedded,
                args.unitary_eps,
            )
            if nonunitary:
                predicted, trace_real = normalize_density_if_needed(predicted_raw, args.eps)
                if trace_real > args.eps:
                    err_raw = max_complex_error(predicted_raw, active_block)
                    err_norm = max_complex_error(predicted, active_block)
                    if err_norm > err_raw + args.tol:
                        raise SystemExit(
                            "[error] Normalized non-unitary prediction is less accurate than raw prediction "
                            f"at step={step_index}, sample_index={sample.get('sample_index')}, "
                            f"err_raw={err_raw:.6e}, err_norm={err_norm:.6e}"
                        )
                    normalized_nonunitary_checked += 1

            err = max_complex_error(predicted, active_block)
            max_error = max(max_error, err)
            checked += 1
            if err > args.tol:
                raise SystemExit(
                    "[error] Decomposition mismatch exceeds tolerance "
                    f"at step={step_index}, sample_index={sample.get('sample_index')}, "
                    f"err={err:.6e}, tol={args.tol:.6e}"
                )

    if checked == 0:
        raise SystemExit("[error] No eligible apply_gate samples were validated.")

    print(
        "[ok] decomposition overlay checks passed: "
        f"checked={checked}, skipped={skipped}, "
        f"normalized_nonunitary_checked={normalized_nonunitary_checked}, "
        f"max_error={max_error:.6e}, tol={args.tol:.6e}"
    )


if __name__ == "__main__":
    main()
