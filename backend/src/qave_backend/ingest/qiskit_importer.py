"""Qiskit-based import paths into QuantumCircuitIR."""

from __future__ import annotations

from typing import Any, Literal

from qiskit import QuantumCircuit, qasm2

from qave_backend.contracts.models import ClassicalMapEntry, GateOp, QuantumCircuitIR, SourceFormat


def _to_float_params(params: list[Any]) -> list[float]:
    """Convert instruction parameters to numeric floats or raise on symbols."""
    values: list[float] = []
    for param in params:
        try:
            values.append(float(param))
        except (TypeError, ValueError) as exc:
            msg = f"Unsupported symbolic parameter {param!r}; bind parameters before import"
            raise ValueError(msg) from exc
    return values


def _controls_and_targets(op: Any, qubit_indices: list[int]) -> tuple[list[int], list[int]]:
    """Split qubit indices into control and target lists for controlled operations."""
    num_ctrl = int(getattr(op, "num_ctrl_qubits", 0) or 0)
    if num_ctrl <= 0:
        return [], qubit_indices
    controls = qubit_indices[:num_ctrl]
    targets = qubit_indices[num_ctrl:]
    return controls, targets


def import_qiskit_circuit(
    circuit: QuantumCircuit,
    source_format: SourceFormat = "qiskit_json",
    source_metadata: dict[str, str | int | float | bool] | None = None,
) -> QuantumCircuitIR:
    """Convert a Qiskit circuit into project IR."""
    steps: list[GateOp] = []
    classical_map: dict[tuple[int, int], ClassicalMapEntry] = {}

    for index, instruction in enumerate(circuit.data):
        op = instruction.operation
        qubit_indices = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        clbit_indices = [circuit.find_bit(clbit).index for clbit in instruction.clbits]

        kind: Literal["unitary", "measurement", "reset"]
        if op.name == "measure":
            kind = "measurement"
            controls: list[int] = []
            targets = qubit_indices
        elif op.name == "reset":
            kind = "reset"
            controls = []
            targets = qubit_indices
        else:
            kind = "unitary"
            controls, targets = _controls_and_targets(op, qubit_indices)

        params = _to_float_params(list(getattr(op, "params", [])))
        metadata: dict[str, str | int | float | bool] = {}
        label = getattr(op, "label", None)
        if label is not None:
            metadata["label"] = str(label)

        step = GateOp(
            id=f"op_{index}_{op.name}",
            kind=kind,
            name=op.name,
            targets=targets,
            controls=controls,
            classical_targets=clbit_indices or None,
            params=params,
            time_index=index,
            metadata=metadata,
        )
        steps.append(step)

        if kind == "measurement":
            for qubit_index, clbit_index in zip(qubit_indices, clbit_indices, strict=False):
                classical_map[(qubit_index, clbit_index)] = ClassicalMapEntry(
                    qubit=qubit_index,
                    classical_bit=clbit_index,
                    register=None,
                )

    metadata_default: dict[str, str | int | float | bool] = {
        "name": circuit.name or "",
        "num_parameters": len(circuit.parameters),
        "depth": circuit.depth() or 0,
    }
    if source_metadata:
        metadata_default.update(source_metadata)

    return QuantumCircuitIR(
        contract_version="0.1.0",
        circuit_id=circuit.name or "qiskit_circuit",
        source_format=source_format,
        source_metadata=metadata_default,
        qubits=circuit.num_qubits,
        classical_bits=circuit.num_clbits,
        steps=steps,
        moments_or_steps_mode="single_gate_steps",
        classical_map=list(classical_map.values()),
        parameters={},
        metadata={"global_phase": float(circuit.global_phase)},
    )


def import_qiskit_json(payload: dict[str, Any]) -> QuantumCircuitIR:
    """Import from a qiskit-json style payload.

    The accepted payload forms are:
    - {"qasm": "OPENQASM ..."}
    - {"qasm2": "OPENQASM ..."}
    - {"circuit": "OPENQASM ..."}
    """
    qasm_text = payload.get("qasm") or payload.get("qasm2") or payload.get("circuit")
    if not isinstance(qasm_text, str):
        msg = "Unsupported qiskit JSON payload. Expected one of: qasm, qasm2, circuit"
        raise ValueError(msg)

    circuit = qasm2.loads(qasm_text)
    return import_qiskit_circuit(circuit, source_format="qiskit_json")
