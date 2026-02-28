# ruff: noqa: E501
"""Integration tests for public animation-generation API workflows."""

from __future__ import annotations

from pathlib import Path

from qiskit import QuantumCircuit

from qave import ArtifactOptions, RenderOptions, SimulationOptions, generate_animation_from_qiskit


def test_generate_animation_from_qiskit_uses_render_pipeline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given Bell circuit input, when animation is requested, then render pipeline outputs are returned."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    frames_dir = tmp_path / "frames"
    mp4_path = tmp_path / "animation.mp4"
    frames_dir.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"")

    def _fake_run_render_pipeline(*, trace_path: Path, render: RenderOptions, out_dir: Path):
        """Validate render arguments and return deterministic fake outputs."""
        assert trace_path.exists()
        assert render.width == 1920
        assert render.height == 1080
        assert render.fps == 60
        assert out_dir == tmp_path
        return frames_dir, mp4_path, None, []

    monkeypatch.setattr("qave.api.run_render_pipeline", _fake_run_render_pipeline)

    result = generate_animation_from_qiskit(
        circuit,
        options=SimulationOptions(algorithm_id="bell"),
        artifacts=ArtifactOptions(out_dir=tmp_path),
    )

    assert result.paths.trace_json.exists()
    assert result.frames_dir == frames_dir
    assert result.mp4_path == mp4_path
    assert result.gif_path is None
