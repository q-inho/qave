# ruff: noqa: E501
"""Integration tests for trace-generation workflows in the public qave API."""

from __future__ import annotations

from pathlib import Path

from qiskit import QuantumCircuit

import qave
from qave import (
    ArtifactOptions,
    SimulationOptions,
    generate_trace_from_openqasm,
    generate_trace_from_qiskit,
)


def test_generate_trace_from_qiskit_writes_expected_artifacts(tmp_path: Path) -> None:
    """Given Bell circuit input, when generating trace, then trace/result artifacts are written."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(
            algorithm_id="bell",
            mode="preview",
            measurement_mode="collapse",
            seed=11,
        ),
        artifacts=ArtifactOptions(out_dir=tmp_path, write_result_json=True),
    )

    assert result.paths.trace_json.exists()
    assert result.paths.result_json is not None and result.paths.result_json.exists()
    assert result.trace.steps
    assert result.simulation_result.status == "ok"
    assert set(result.simulation_result.outputs) == {"final_statevector", "num_steps"}
    assert result.request.contract_version == qave.CONTRACT_VERSION
    assert result.trace.contract_version == qave.CONTRACT_VERSION
    assert result.simulation_result.contract_version == qave.CONTRACT_VERSION


def test_generate_trace_uses_request_scoped_default_artifact_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """Given no artifact path override, when generating trace, then default request-scoped output dir is used."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    request_id = "tutorial_ghz3_seed42"
    monkeypatch.chdir(tmp_path)

    result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="bell", request_id=request_id),
    )

    expected = (tmp_path / "qave_artifacts" / request_id).resolve()
    assert result.paths.out_dir == expected
    assert result.paths.trace_json == expected / "trace.json"
    assert result.paths.trace_json.exists()


def test_generate_trace_uses_env_out_dir_when_explicit_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    """Given QAVE_OUT_DIR env var, when explicit out_dir is absent, then env path is selected."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    env_out_dir = tmp_path / "env_artifacts"
    monkeypatch.setenv("QAVE_OUT_DIR", str(env_out_dir))

    result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="bell", request_id="env_override"),
    )

    assert result.paths.out_dir == env_out_dir.resolve()
    assert result.paths.trace_json.exists()


def test_generate_trace_prefers_explicit_out_dir_over_env(tmp_path: Path, monkeypatch) -> None:
    """Given both env and explicit output paths, when generating trace, then explicit path wins."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    monkeypatch.setenv("QAVE_OUT_DIR", str(tmp_path / "env_artifacts"))
    explicit_out_dir = tmp_path / "explicit_artifacts"

    result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="bell", request_id="explicit_override"),
        artifacts=ArtifactOptions(out_dir=explicit_out_dir),
    )

    assert result.paths.out_dir == explicit_out_dir.resolve()
    assert result.paths.trace_json.exists()


def test_generate_trace_sanitizes_request_id_for_default_path(tmp_path: Path, monkeypatch) -> None:
    """Given separators in request ID, when using default path policy, then directory is sanitized."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    monkeypatch.chdir(tmp_path)

    result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="bell", request_id="seed 42/ghz demo"),
    )

    expected = (tmp_path / "qave_artifacts" / "seed_42_ghz_demo").resolve()
    assert result.paths.out_dir == expected
    assert result.paths.trace_json.exists()


def test_openqasm_trace_matches_qiskit_trace_statevector(tmp_path: Path) -> None:
    """Given equivalent OpenQASM and Qiskit Bell circuits, when tracing, then final states and hashes match."""
    qasm = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    h q[0];
    cx q[0],q[1];
    """
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    qiskit_result = generate_trace_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="bell", seed=7),
        artifacts=ArtifactOptions(out_dir=tmp_path / "qiskit"),
    )
    qasm_result = generate_trace_from_openqasm(
        qasm,
        options=SimulationOptions(algorithm_id="bell", seed=7),
        artifacts=ArtifactOptions(out_dir=tmp_path / "qasm"),
    )

    assert (
        qiskit_result.simulation_result.outputs["final_statevector"]
        == qasm_result.simulation_result.outputs["final_statevector"]
    )
    assert [step.boundary_checkpoint.gate_end_hash for step in qiskit_result.trace.steps] == [
        step.boundary_checkpoint.gate_end_hash for step in qasm_result.trace.steps
    ]
