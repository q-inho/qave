# ruff: noqa: E501
"""Unit tests for qave render pipeline helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import qave.render as render_module
from qave.errors import ArtifactIOError, RenderExecutionError, RuntimeDependencyError
from qave.options import RenderOptions


def _write_executable(path: Path) -> None:
    """Write a minimal executable file for command-path test fixtures."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def test_build_processing_cli_java_command_uses_portable_layout(tmp_path: Path) -> None:
    """Given portable Processing layout, when building CLI command, then bundled Java invocation is produced."""
    processing_root = tmp_path / "processing-portable"
    runner = processing_root / "bin" / "Processing"
    java_bin = processing_root / "lib" / "app" / "resources" / "jdk" / "bin" / "java"
    cfg_path = processing_root / "lib" / "app" / "Processing.cfg"

    _write_executable(runner)
    _write_executable(java_bin)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        "\n".join(
            [
                "[Application]",
                "app.mainclass=processing.app.ProcessingKt",
                "app.classpath=$APPDIR/a.jar",
                "app.classpath=$APPDIR/b.jar",
                "[JavaOptions]",
                "java-options=-Dfoo=bar",
            ]
        ),
        encoding="utf-8",
    )

    sketch_dir = tmp_path / "sketch"
    command = render_module._build_processing_cli_java_command(
        processing_runner=str(runner),
        sketch_dir=sketch_dir,
        args=["--trace", "trace.json"],
    )

    assert command is not None
    assert command[0] == str(java_bin)
    assert "processing.app.ProcessingKt" in command
    assert "cli" in command
    assert f"--sketch={sketch_dir}" in command
    assert "--" in command


def test_build_processing_cli_java_command_returns_none_for_nonportable_runner(
    tmp_path: Path,
) -> None:
    """Given nonportable Processing runner path, when building CLI command, then None is returned."""
    runner = tmp_path / "Processing"
    _write_executable(runner)

    command = render_module._build_processing_cli_java_command(
        processing_runner=str(runner),
        sketch_dir=tmp_path / "sketch",
        args=["--trace", "trace.json"],
    )

    assert command is None


def test_default_sketch_dir_points_to_processing_viewer() -> None:
    """Given default sketch resolution, when reading path, then viewer sketch directory suffix matches."""
    sketch_dir = render_module.default_sketch_dir()
    assert sketch_dir.name == "processing_qave"
    assert sketch_dir.parent.name == "viewer"


def test_resolve_processing_runner_prefers_explicit_legacy_path(tmp_path: Path) -> None:
    """Given explicit processing-java path, when resolving runner, then legacy mode is selected."""
    runner = tmp_path / "processing-java"
    runner.write_text("", encoding="utf-8")

    path, mode = render_module._resolve_processing_runner(str(runner))
    assert path == str(runner)
    assert mode == "legacy"


def test_resolve_processing_runner_rejects_missing_preferred_runner(monkeypatch) -> None:
    """Given missing preferred runner, when resolving runner, then dependency error is raised."""
    monkeypatch.setattr("qave.render.shutil.which", lambda _name: None)

    with pytest.raises(RuntimeDependencyError, match="not found"):
        render_module._resolve_processing_runner("/does/not/exist/Processing")


def test_resolve_processing_runner_auto_detects_cli_then_legacy(monkeypatch) -> None:
    """Given auto mode, when Processing exists, then it is preferred over processing-java."""

    def _which_cli_first(name: str) -> str | None:
        """Return deterministic fake paths for runner lookup."""
        if name == "Processing":
            return "/usr/bin/Processing"
        if name == "processing-java":
            return "/usr/bin/processing-java"
        return None

    monkeypatch.setattr("qave.render.shutil.which", _which_cli_first)
    path, mode = render_module._resolve_processing_runner(None)
    assert path == "/usr/bin/Processing"
    assert mode == "cli"

    def _which_legacy_only(name: str) -> str | None:
        """Return fake path only for legacy Processing runner."""
        if name == "processing-java":
            return "/usr/bin/processing-java"
        return None

    monkeypatch.setattr("qave.render.shutil.which", _which_legacy_only)
    path, mode = render_module._resolve_processing_runner(None)
    assert path == "/usr/bin/processing-java"
    assert mode == "legacy"


def test_resolve_processing_runner_raises_when_no_runner_is_installed(monkeypatch) -> None:
    """Given no runner on PATH, when resolving runner, then dependency error is raised."""
    monkeypatch.setattr("qave.render.shutil.which", lambda _name: None)

    with pytest.raises(RuntimeDependencyError, match="Processing CLI is required"):
        render_module._resolve_processing_runner(None)


def test_ensure_ffmpeg_returns_path_or_raises(monkeypatch) -> None:
    """Given ffmpeg lookup outcomes, when resolving ffmpeg, then path or error is returned."""
    monkeypatch.setattr("qave.render.shutil.which", lambda _name: "/usr/bin/ffmpeg")
    assert render_module._ensure_ffmpeg("ffmpeg") == "/usr/bin/ffmpeg"

    monkeypatch.setattr("qave.render.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeDependencyError, match="ffmpeg is required"):
        render_module._ensure_ffmpeg("ffmpeg")


def test_run_command_success_and_failure_paths(monkeypatch, tmp_path: Path) -> None:
    """Given subprocess outcomes, when running command, then diagnostics or execution errors are emitted."""

    class _SuccessProc:
        """Successful completed-process stub."""

        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr("qave.render.subprocess.run", lambda *_a, **_k: _SuccessProc())
    diag = render_module._run_command(["echo", "ok"], cwd=tmp_path, error_hint="run failed")
    assert diag.code == "PROCESS_EXEC"

    class _FailureProc:
        """Failed completed-process stub with stderr payload."""

        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr("qave.render.subprocess.run", lambda *_a, **_k: _FailureProc())
    with pytest.raises(RenderExecutionError, match="Exit code=1"):
        render_module._run_command(["echo", "nope"], cwd=tmp_path, error_hint="run failed")

    def _raise_oserror(*_args, **_kwargs):
        """Raise deterministic process-start failure."""
        raise OSError("cannot execute")

    monkeypatch.setattr("qave.render.subprocess.run", _raise_oserror)
    with pytest.raises(RenderExecutionError, match="Failed to start process"):
        render_module._run_command(["echo", "nope"], cwd=tmp_path, error_hint="run failed")


def test_reset_frames_dir_wraps_os_errors(monkeypatch, tmp_path: Path) -> None:
    """Given mkdir failure, when resetting frames dir, then ArtifactIOError is raised."""

    def _raise(*_args, **_kwargs):
        """Raise deterministic mkdir failure."""
        raise OSError("mkdir failed")

    monkeypatch.setattr(Path, "mkdir", _raise)
    with pytest.raises(ArtifactIOError, match="Failed to prepare frame directory"):
        render_module._reset_frames_dir(tmp_path / "frames")


def test_run_render_pipeline_rejects_missing_sketch_directory(tmp_path: Path) -> None:
    """Given missing sketch path, when running render pipeline, then dependency error is raised."""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")

    render = RenderOptions(
        keep_frames=True,
        emit_mp4=False,
        emit_gif=False,
        sketch_dir=tmp_path / "missing_sketch",
    )

    with pytest.raises(RuntimeDependencyError, match="sketch directory was not found"):
        render_module.run_render_pipeline(trace_path=trace_path, render=render, out_dir=tmp_path)


def test_run_render_pipeline_raises_when_processing_emits_no_frames(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given successful process run with zero frames, when rendering, then execution error is raised."""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")
    sketch_dir = tmp_path / "sketch"
    sketch_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        render_module, "_resolve_processing_runner", lambda _p: ("Processing", "cli")
    )

    def _fake_run_command(command, *, cwd: Path, error_hint: str):
        """Return success diagnostics without producing any frames."""
        _ = (command, cwd, error_hint)
        return render_module.DiagnosticEntry(code="OK", message="ok")

    monkeypatch.setattr(render_module, "_run_command", _fake_run_command)

    render = RenderOptions(
        keep_frames=True,
        emit_mp4=False,
        emit_gif=False,
        sketch_dir=sketch_dir,
    )

    with pytest.raises(RenderExecutionError, match="no frame PNG"):
        render_module.run_render_pipeline(trace_path=trace_path, render=render, out_dir=tmp_path)


def test_run_render_pipeline_frames_only_and_keep_frames_false(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given frames-only rendering with keep_frames disabled, when pipeline completes, then output dir is empty."""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")
    sketch_dir = tmp_path / "sketch"
    sketch_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        render_module, "_resolve_processing_runner", lambda _p: ("Processing", "cli")
    )
    monkeypatch.setattr(render_module, "_ensure_ffmpeg", lambda _bin: "ffmpeg")

    def _fake_run_command(command: list[str], *, cwd: Path, error_hint: str):
        """Write fake sketch frames during Processing command execution."""
        if command[0] == "Processing":
            frames_dir = cwd / "exports" / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            for idx in range(2):
                image = Image.new("RGBA", (16, 16), (idx * 40, 0, 0, 255))
                image.save(frames_dir / f"frame-{idx:06d}.png")
        _ = error_hint
        return render_module.DiagnosticEntry(code="PROCESS_EXEC", message=f"ok: {error_hint}")

    monkeypatch.setattr(render_module, "_run_command", _fake_run_command)

    render = RenderOptions(
        keep_frames=False,
        emit_mp4=True,
        emit_gif=False,
        sketch_dir=sketch_dir,
        processing_runner="Processing",
    )

    frames_dir, mp4_path, gif_path, diagnostics = render_module.run_render_pipeline(
        trace_path=trace_path,
        render=render,
        out_dir=tmp_path / "out",
    )

    assert mp4_path == (tmp_path / "out" / "animation.mp4")
    assert gif_path is None
    assert diagnostics
    assert list(frames_dir.glob("frame-*.png")) == []


def test_run_render_pipeline_emits_mp4_and_gif_commands(tmp_path: Path, monkeypatch) -> None:
    """Given mp4 and gif enabled, when rendering pipeline runs, then ffmpeg command paths are executed."""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")
    sketch_dir = tmp_path / "sketch"
    sketch_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        render_module, "_resolve_processing_runner", lambda _p: ("processing-java", "legacy")
    )
    monkeypatch.setattr(render_module, "_ensure_ffmpeg", lambda _bin: "ffmpeg")
    seen_commands: list[list[str]] = []

    def _fake_run_command(command: list[str], *, cwd: Path, error_hint: str):
        """Record commands and create frames for Processing phase."""
        seen_commands.append(command)
        if command[0] == "processing-java":
            frames_dir = cwd / "exports" / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            image = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
            image.save(frames_dir / "frame-000000.png")
        return render_module.DiagnosticEntry(code="PROCESS_EXEC", message=f"ok: {error_hint}")

    monkeypatch.setattr(render_module, "_run_command", _fake_run_command)

    render = RenderOptions(
        keep_frames=True,
        emit_mp4=True,
        emit_gif=True,
        sketch_dir=sketch_dir,
        processing_runner="processing-java",
    )

    frames_dir, mp4_path, gif_path, diagnostics = render_module.run_render_pipeline(
        trace_path=trace_path,
        render=render,
        out_dir=tmp_path / "out",
    )

    assert frames_dir.exists()
    assert mp4_path == (tmp_path / "out" / "animation.mp4")
    assert gif_path == (tmp_path / "out" / "animation.gif")
    assert len(diagnostics) == 4
    assert any(command[0] == "processing-java" for command in seen_commands)
    assert any("palettegen" in " ".join(command) for command in seen_commands)


def test_run_render_pipeline_prefers_portable_processing_java_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given portable Processing runner, when rendering pipeline runs, then bundled Java command is invoked."""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")
    sketch_dir = tmp_path / "sketch"
    sketch_dir.mkdir(parents=True, exist_ok=True)

    processing_root = tmp_path / "processing-portable"
    runner = processing_root / "bin" / "Processing"
    java_bin = processing_root / "lib" / "app" / "resources" / "jdk" / "bin" / "java"
    cfg_path = processing_root / "lib" / "app" / "Processing.cfg"
    _write_executable(runner)
    _write_executable(java_bin)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        "\n".join(
            [
                "[Application]",
                "app.mainclass=processing.app.ProcessingKt",
                "app.classpath=$APPDIR/a.jar",
            ]
        ),
        encoding="utf-8",
    )

    seen_commands: list[list[str]] = []
    monkeypatch.setattr(
        render_module, "_resolve_processing_runner", lambda _p: (str(runner), "cli")
    )

    def _fake_run_command(command: list[str], *, cwd: Path, error_hint: str):
        """Record command and synthesize one PNG frame for successful pipeline completion."""
        seen_commands.append(command)
        if command[0] == str(java_bin):
            frames_dir = cwd / "exports" / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            image = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
            image.save(frames_dir / "frame-000000.png")
        _ = error_hint
        return render_module.DiagnosticEntry(code="PROCESS_EXEC", message="ok")

    monkeypatch.setattr(render_module, "_run_command", _fake_run_command)

    render = RenderOptions(
        keep_frames=True,
        emit_mp4=False,
        emit_gif=False,
        sketch_dir=sketch_dir,
    )
    render_module.run_render_pipeline(
        trace_path=trace_path, render=render, out_dir=tmp_path / "out"
    )

    assert seen_commands
    assert seen_commands[0][0] == str(java_bin)
    assert "processing.app.ProcessingKt" in seen_commands[0]


def test_run_render_pipeline_falls_back_to_native_processing_when_cfg_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given missing portable Processing cfg, when rendering pipeline runs, then native Processing CLI command is used."""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")
    sketch_dir = tmp_path / "sketch"
    sketch_dir.mkdir(parents=True, exist_ok=True)

    runner = tmp_path / "processing-portable" / "bin" / "Processing"
    _write_executable(runner)
    seen_commands: list[list[str]] = []
    monkeypatch.setattr(
        render_module, "_resolve_processing_runner", lambda _p: (str(runner), "cli")
    )

    def _fake_run_command(command: list[str], *, cwd: Path, error_hint: str):
        """Record command and synthesize one PNG frame for successful pipeline completion."""
        seen_commands.append(command)
        if command[0] == str(runner):
            frames_dir = cwd / "exports" / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            image = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
            image.save(frames_dir / "frame-000000.png")
        _ = error_hint
        return render_module.DiagnosticEntry(code="PROCESS_EXEC", message="ok")

    monkeypatch.setattr(render_module, "_run_command", _fake_run_command)

    render = RenderOptions(
        keep_frames=True,
        emit_mp4=False,
        emit_gif=False,
        sketch_dir=sketch_dir,
    )
    render_module.run_render_pipeline(
        trace_path=trace_path, render=render, out_dir=tmp_path / "out"
    )

    assert seen_commands
    assert seen_commands[0][0] == str(runner)
    assert len(seen_commands[0]) > 1
    assert seen_commands[0][1] == "cli"
