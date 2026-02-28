"""Rendering and encoding adapters for qave animation workflows."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from qave.errors import ArtifactIOError, RenderExecutionError, RuntimeDependencyError
from qave.options import RenderOptions
from qave.results import DiagnosticEntry


def default_sketch_dir() -> Path:
    """Resolve the repository viewer sketch location."""
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "viewer" / "processing_qave"


def _resolve_processing_runner(preferred: str | None) -> tuple[str, str]:
    """Resolve an installed Processing runner binary and invocation mode."""
    if preferred:
        resolved = shutil.which(preferred) or preferred
        if shutil.which(resolved) is None and not Path(resolved).exists():
            msg = f"Processing runner not found: {preferred}"
            raise RuntimeDependencyError(msg)
        mode = "legacy" if Path(resolved).name.lower() == "processing-java" else "cli"
        return resolved, mode

    cli = shutil.which("Processing")
    if cli is not None:
        return cli, "cli"

    legacy = shutil.which("processing-java")
    if legacy is not None:
        return legacy, "legacy"

    msg = (
        "Processing CLI is required. Install Processing 4.x and expose either "
        "'processing-java' or 'Processing' on PATH."
    )
    raise RuntimeDependencyError(msg)


def _ensure_ffmpeg(bin_name: str) -> str:
    """Resolve an ffmpeg executable path or raise dependency error."""
    resolved = shutil.which(bin_name) or bin_name
    if shutil.which(resolved) is None and not Path(resolved).exists():
        msg = f"ffmpeg is required and was not found: {bin_name}"
        raise RuntimeDependencyError(msg)
    return resolved


def _resolve_processing_root(processing_runner: str) -> Path | None:
    """Resolve portable Processing root from runner path if layout matches."""
    runner_path = Path(processing_runner).resolve()
    if runner_path.name != "Processing":
        return None
    if runner_path.parent.name != "bin":
        return None
    return runner_path.parent.parent


def _parse_processing_cfg(processing_root: Path) -> tuple[str, list[str], list[str]] | None:
    """Parse Processing portable config into main class, classpath entries, and Java options."""
    cfg_path = processing_root / "lib" / "app" / "Processing.cfg"
    app_dir = processing_root / "lib" / "app"
    if not cfg_path.exists():
        return None

    section = ""
    main_class = ""
    classpath_entries: list[str] = []
    java_options: list[str] = []

    for raw_line in cfg_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.replace("$APPDIR", str(app_dir))
        if section == "Application":
            if key == "app.mainclass":
                main_class = value
            elif key == "app.classpath":
                classpath_entries.append(value)
        elif section == "JavaOptions" and key == "java-options":
            java_options.append(value)

    if not main_class or not classpath_entries:
        return None

    return main_class, classpath_entries, java_options


def _build_processing_cli_java_command(
    processing_runner: str,
    sketch_dir: Path,
    args: list[str],
) -> list[str] | None:
    """Build Processing CLI command using bundled Java runtime and Processing.cfg."""
    processing_root = _resolve_processing_root(processing_runner)
    if processing_root is None:
        return None

    parsed = _parse_processing_cfg(processing_root)
    if parsed is None:
        return None

    java_bin = processing_root / "lib" / "app" / "resources" / "jdk" / "bin" / "java"
    if not java_bin.exists():
        return None

    main_class, classpath_entries, java_options = parsed
    classpath = ":".join(classpath_entries)

    command = [
        str(java_bin),
        *java_options,
        "-cp",
        classpath,
        main_class,
        "cli",
        f"--sketch={sketch_dir}",
        "--run",
    ]
    if args:
        command.extend(["--", *args])
    return command


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    error_hint: str,
) -> DiagnosticEntry:
    """Run a subprocess and convert failures into render diagnostics.

    Args:
        command: Full command tokens to execute.
        cwd: Working directory for subprocess execution.
        error_hint: Context string used in raised failure messages.

    Returns:
        Diagnostic entry describing successful command execution.

    Raises:
        RenderExecutionError: If process start fails or exits non-zero.
    """
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        msg = f"{error_hint}. Failed to start process: {exc}"
        raise RenderExecutionError(msg) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        details = stderr if stderr else stdout
        msg = f"{error_hint}. Exit code={proc.returncode}. Output: {details}"
        raise RenderExecutionError(msg)

    return DiagnosticEntry(
        code="PROCESS_EXEC",
        message=f"ok: {' '.join(command[:3])}...",
        source="render",
    )


def _reset_frames_dir(frames_dir: Path) -> None:
    """Ensure a clean frame directory exists for rendering output."""
    try:
        shutil.rmtree(frames_dir, ignore_errors=True)
        frames_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        msg = f"Failed to prepare frame directory: {frames_dir}"
        raise ArtifactIOError(msg) from exc


def run_render_pipeline(
    *,
    trace_path: Path,
    render: RenderOptions,
    out_dir: Path,
) -> tuple[Path, Path | None, Path | None, list[DiagnosticEntry]]:
    """Render frames via Processing and optionally encode media via ffmpeg."""
    diagnostics: list[DiagnosticEntry] = []

    sketch_dir = render.sketch_dir if render.sketch_dir is not None else default_sketch_dir()
    sketch_dir = sketch_dir.resolve()
    if not sketch_dir.exists():
        msg = (
            f"Processing sketch directory was not found: {sketch_dir}. "
            "Pass RenderOptions(sketch_dir=...) to point at the QAVE Processing sketch "
            "(repo default: viewer/processing_qave)."
        )
        raise RuntimeDependencyError(msg)

    processing_runner, processing_mode = _resolve_processing_runner(render.processing_runner)

    sketch_frames_dir = sketch_dir / "exports" / "frames"
    _reset_frames_dir(sketch_frames_dir)

    args = [
        "--trace",
        str(trace_path.resolve()),
        "--autoplay",
        "true",
        "--record",
        render.record_mode,
        "--width",
        str(render.width),
        "--height",
        str(render.height),
        "--fps",
        str(render.fps),
    ]

    processing_cmd: list[str]
    if processing_mode == "legacy":
        processing_cmd = [
            processing_runner,
            f"--sketch={sketch_dir}",
            "--run",
            "--",
            *args,
        ]
    else:
        cli_java_command = _build_processing_cli_java_command(
            processing_runner=processing_runner,
            sketch_dir=sketch_dir,
            args=args,
        )
        if cli_java_command is None:
            processing_cmd = [
                processing_runner,
                "cli",
                f"--sketch={sketch_dir}",
                "--run",
                *args,
            ]
        else:
            processing_cmd = cli_java_command

    diagnostics.append(
        _run_command(
            processing_cmd,
            cwd=sketch_dir,
            error_hint="Processing render failed",
        )
    )

    frame_files = sorted(sketch_frames_dir.glob("frame-*.png"))
    if not frame_files:
        msg = "Processing completed but no frame PNG files were generated."
        raise RenderExecutionError(msg)

    output_frames_dir = out_dir / "frames"
    _reset_frames_dir(output_frames_dir)
    for frame in frame_files:
        shutil.copy2(frame, output_frames_dir / frame.name)

    mp4_path: Path | None = None
    if render.emit_mp4:
        ffmpeg_bin = _ensure_ffmpeg(render.ffmpeg_bin)
        mp4_path = out_dir / "animation.mp4"
        mp4_cmd = [
            ffmpeg_bin,
            "-y",
            "-framerate",
            str(render.fps),
            "-i",
            str(sketch_frames_dir / "frame-%06d.png"),
            "-vf",
            f"scale={render.width}:{render.height}:flags=lanczos",
            "-pix_fmt",
            "yuv420p",
            str(mp4_path),
        ]
        diagnostics.append(
            _run_command(
                mp4_cmd,
                cwd=sketch_dir,
                error_hint="ffmpeg mp4 encoding failed",
            )
        )

    gif_path: Path | None = None
    if render.emit_gif:
        ffmpeg_bin = _ensure_ffmpeg(render.ffmpeg_bin)
        gif_path = out_dir / "animation.gif"
        palette = out_dir / "palette.png"
        palette_cmd = [
            ffmpeg_bin,
            "-y",
            "-framerate",
            str(render.fps),
            "-i",
            str(sketch_frames_dir / "frame-%06d.png"),
            "-vf",
            f"fps={render.fps},scale={render.width}:{render.height}:flags=lanczos,palettegen",
            str(palette),
        ]
        gif_cmd = [
            ffmpeg_bin,
            "-y",
            "-framerate",
            str(render.fps),
            "-i",
            str(sketch_frames_dir / "frame-%06d.png"),
            "-i",
            str(palette),
            "-lavfi",
            f"fps={render.fps},scale={render.width}:{render.height}:flags=lanczos,paletteuse",
            str(gif_path),
        ]
        diagnostics.append(
            _run_command(
                palette_cmd,
                cwd=sketch_dir,
                error_hint="ffmpeg palette generation failed",
            )
        )
        diagnostics.append(
            _run_command(
                gif_cmd,
                cwd=sketch_dir,
                error_hint="ffmpeg gif encoding failed",
            )
        )
        palette.unlink(missing_ok=True)

    if not render.keep_frames:
        shutil.rmtree(output_frames_dir, ignore_errors=True)
        output_frames_dir.mkdir(parents=True, exist_ok=True)

    return output_frames_dir, mp4_path, gif_path, diagnostics
