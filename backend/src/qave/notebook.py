"""Notebook display helpers for QAVE animation outputs.

These helpers are intentionally lightweight:
- They do not require ffmpeg.
- They are safe to import in non-notebook environments (IPython is imported lazily).
"""

from __future__ import annotations

import io
import math
import shutil
from pathlib import Path
from typing import Literal

from PIL import Image

from qave.options import RenderOptions
from qave.results import AnimationGenerationResult, TraceGenerationResult


def _lanczos() -> int:
    """Return the Pillow LANCZOS resampling constant across Pillow versions."""
    resampling = getattr(Image, "Resampling", None)
    if resampling is not None and hasattr(resampling, "LANCZOS"):
        return int(resampling.LANCZOS)
    lanczos = getattr(Image, "LANCZOS", None)
    if lanczos is None:
        msg = "Pillow LANCZOS resampling constant is unavailable."
        raise RuntimeError(msg)
    return int(lanczos)


def encode_gif_from_frames(
    frames_dir: Path,
    *,
    fps: int = 60,
    max_frames: int = 240,
    max_width: int | None = 960,
    loop: int = 0,
) -> bytes:
    """Encode an in-memory GIF from `frame-*.png` files in `frames_dir`.

    Args:
        frames_dir: Directory containing `frame-*.png` images.
        fps: Intended playback frames per second for the source frames.
        max_frames: Maximum number of frames to include in the output GIF. When exceeded,
            frames are downsampled by a constant stride and frame duration is scaled to
            approximately preserve wall-time.
        max_width: Optional maximum width in pixels for the encoded GIF. Frames wider than this
            are resized with aspect ratio preserved.
        loop: GIF loop count (0 means loop forever).

    Returns:
        GIF bytes suitable for `IPython.display.Image(data=..., format="gif")`.

    Raises:
        ValueError: If inputs are invalid or no matching frames are found.
    """
    if fps < 1:
        msg = "fps must be >= 1"
        raise ValueError(msg)
    if max_frames < 1:
        msg = "max_frames must be >= 1"
        raise ValueError(msg)
    if max_width is not None and max_width < 1:
        msg = "max_width must be >= 1 when provided"
        raise ValueError(msg)

    frame_paths = sorted(frames_dir.glob("frame-*.png"))
    if not frame_paths:
        msg = f"No frame PNGs found in frames_dir={frames_dir} (expected 'frame-*.png')"
        raise ValueError(msg)

    stride = 1
    if len(frame_paths) > max_frames:
        stride = max(1, math.ceil(len(frame_paths) / max_frames))
    selected_paths = frame_paths[::stride]
    duration_ms = max(1, round((1000.0 / float(fps)) * float(stride)))

    resample = _lanczos()
    frames: list[Image.Image] = []
    for path in selected_paths:
        with Image.open(path) as image:
            frame = image.convert("RGBA")
            if max_width is not None and frame.width > max_width:
                new_height = max(1, round(frame.height * float(max_width) / float(frame.width)))
                frame = frame.resize((max_width, new_height), resample=resample)
            frames.append(frame)

    buffer = io.BytesIO()
    first, *rest = frames
    first.save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=rest,
        duration=duration_ms,
        loop=loop,
    )
    return buffer.getvalue()


def display_animation(
    result: AnimationGenerationResult,
    *,
    prefer: Literal["auto", "mp4", "gif"] = "auto",
    fps: int = 60,
    max_frames: int = 240,
    max_width: int | None = 960,
    loop: int = 0,
    embed: bool = True,
    width: int | None = None,
    height: int | None = None,
) -> object:
    """Return an IPython display object for an animation generation result.

    Args:
        result: `AnimationGenerationResult` produced by `qave.generate_animation_*` APIs.
        prefer: Output preference. `"auto"` chooses MP4 when available, then a GIF file,
            then a GIF encoded from frames.
        fps: Used only when encoding a GIF from PNG frames.
        max_frames: Used only when encoding a GIF from PNG frames.
        max_width: Used only when encoding a GIF from PNG frames.
        loop: Used only when encoding a GIF from PNG frames (0 means loop forever).
        embed: Whether to embed the media in notebook output.
        width: Optional display width in pixels.
        height: Optional display height in pixels.

    Returns:
        An IPython display object (`Video` for MP4, `Image` for GIF).

    Raises:
        RuntimeError: If IPython is unavailable or the requested media is not present.
        ValueError: If an invalid preference is provided or frames are missing when needed.
    """
    if prefer not in {"auto", "mp4", "gif"}:
        msg = f"Unsupported prefer={prefer!r}. Use: 'auto', 'mp4', 'gif'."
        raise ValueError(msg)

    try:
        from IPython.display import Image as NotebookImage
        from IPython.display import Video
    except ModuleNotFoundError as exc:
        msg = (
            "IPython is required to display animations in a notebook. "
            "Install Jupyter/ipykernel and run the notebook with the backend environment."
        )
        raise RuntimeError(msg) from exc

    mp4_path = result.mp4_path
    if mp4_path is not None and mp4_path.exists() and prefer in {"auto", "mp4"}:
        return Video(
            filename=str(mp4_path),
            embed=embed,
            width=width,
            height=height,
        )

    gif_path = result.gif_path
    if gif_path is not None and gif_path.exists() and prefer in {"auto", "gif"}:
        return NotebookImage(
            filename=str(gif_path),
            embed=embed,
            width=width,
            height=height,
        )

    if prefer == "mp4":
        msg = "MP4 output is not available. Set RenderOptions(emit_mp4=True) and install ffmpeg."
        raise RuntimeError(msg)

    frames_dir = result.frames_dir
    gif_bytes = encode_gif_from_frames(
        frames_dir,
        fps=fps,
        max_frames=max_frames,
        max_width=max_width,
        loop=loop,
    )
    return NotebookImage(
        data=gif_bytes,
        format="gif",
        embed=embed,
        width=width,
        height=height,
    )


def resolve_notebook_render_options(
    *,
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
    prefer_mp4: bool = True,
) -> RenderOptions:
    """Return `RenderOptions` tuned for notebook usage.

    This helper prefers emitting MP4 when `ffmpeg` is available on `PATH`. When `ffmpeg` is
    unavailable, it falls back to frames-only output so notebooks can still display an
    inline animation via `display_animation(...)`'s in-memory GIF encoding.

    Args:
        width: Rendered frame width in pixels.
        height: Rendered frame height in pixels.
        fps: Rendered frames per second.
        prefer_mp4: When True, emits MP4 only if `ffmpeg` is available.

    Returns:
        A `RenderOptions` instance that avoids failing on missing `ffmpeg` by default.
    """
    emit_mp4 = bool(prefer_mp4 and shutil.which("ffmpeg") is not None)
    keep_frames = not emit_mp4
    return RenderOptions(
        width=width,
        height=height,
        fps=fps,
        keep_frames=keep_frames,
        emit_mp4=emit_mp4,
        emit_gif=False,
    )


def render_animation(
    trace_result: TraceGenerationResult,
    *,
    render: RenderOptions | None = None,
) -> AnimationGenerationResult:
    """Render animation artifacts from an existing trace with strict failure semantics.

    This helper renders animation artifacts from an existing trace and always propagates
    runtime and execution failures to the caller.

    Args:
        trace_result: A `TraceGenerationResult` produced by `qave.generate_trace_*`.
        render: Optional `RenderOptions`. When omitted, uses
            `resolve_notebook_render_options()`.

    Returns:
        An `AnimationGenerationResult` with rendered artifact paths and merged diagnostics.

    Raises:
        RuntimeDependencyError: When required runtime tools are missing.
        RenderExecutionError: When Processing or ffmpeg execution fails.
    """
    resolved_render = render or resolve_notebook_render_options()

    from qave.render import run_render_pipeline

    frames_dir, mp4_path, gif_path, render_diags = run_render_pipeline(
        trace_path=trace_result.paths.trace_json,
        render=resolved_render,
        out_dir=trace_result.paths.out_dir,
    )

    diagnostics = [*trace_result.diagnostics, *render_diags]
    return AnimationGenerationResult(
        request=trace_result.request,
        simulation_result=trace_result.simulation_result,
        trace=trace_result.trace,
        validation=trace_result.validation,
        paths=trace_result.paths,
        diagnostics=diagnostics,
        frames_dir=frames_dir,
        mp4_path=mp4_path,
        gif_path=gif_path,
    )
