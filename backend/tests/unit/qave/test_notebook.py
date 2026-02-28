# ruff: noqa: E501
"""Unit tests for qave notebook helper functions."""

from __future__ import annotations

import builtins
import io
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

import pytest
from PIL import Image

from qave.notebook import (
    display_animation,
    encode_gif_from_frames,
    render_animation,
    resolve_notebook_render_options,
)
from qave.options import RenderOptions
from qave.results import (
    AnimationGenerationResult,
    ArtifactPaths,
    DiagnosticEntry,
    TraceGenerationResult,
)


class _DisplayObject(Protocol):
    """Protocol for fake notebook display objects used in assertions."""

    kwargs: dict[str, Any]


def _fake_trace_result(tmp_path: Path) -> TraceGenerationResult:
    """Build a minimal trace result fixture rooted in a temporary directory."""
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    trace_path = out_dir / "trace.json"
    trace_path.write_text("{}", encoding="utf-8")
    return TraceGenerationResult(
        request="request",  # type: ignore[arg-type]
        simulation_result="simulation_result",  # type: ignore[arg-type]
        trace="trace",  # type: ignore[arg-type]
        validation=None,
        paths=ArtifactPaths(out_dir=out_dir, trace_json=trace_path),
        diagnostics=[DiagnosticEntry(code="TRACE", message="ok", source="test")],
    )


def _fake_animation_result(
    tmp_path: Path,
    *,
    with_mp4: bool = False,
    with_gif: bool = False,
) -> AnimationGenerationResult:
    """Build a minimal animation result fixture with optional media files."""
    trace_result = _fake_trace_result(tmp_path)
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame = Image.new("RGB", (16, 16), (255, 0, 0))
    frame.save(frames_dir / "frame-000000.png")

    mp4_path = tmp_path / "animation.mp4" if with_mp4 else None
    if mp4_path is not None:
        mp4_path.write_bytes(b"\x00")

    gif_path = tmp_path / "animation.gif" if with_gif else None
    if gif_path is not None:
        gif_frame = Image.new("RGB", (16, 16), (0, 255, 0))
        gif_frame.save(gif_path)

    return AnimationGenerationResult(
        request=trace_result.request,
        simulation_result=trace_result.simulation_result,
        trace=trace_result.trace,
        validation=trace_result.validation,
        paths=trace_result.paths,
        diagnostics=trace_result.diagnostics,
        frames_dir=frames_dir,
        mp4_path=mp4_path,
        gif_path=gif_path,
    )


def _install_fake_ipython(monkeypatch) -> tuple[type, type]:
    """Install fake IPython display module for deterministic display tests."""

    class FakeImage:
        """Capture NotebookImage construction arguments."""

        def __init__(self, *args, **kwargs):
            """Store args for assertions."""
            self.args = args
            self.kwargs = kwargs

    class FakeVideo:
        """Capture Video construction arguments."""

        def __init__(self, *args, **kwargs):
            """Store args for assertions."""
            self.args = args
            self.kwargs = kwargs

    display_module = ModuleType("IPython.display")
    display_module.Image = FakeImage  # type: ignore[attr-defined]
    display_module.Video = FakeVideo  # type: ignore[attr-defined]

    ipython_module = ModuleType("IPython")
    ipython_module.display = display_module  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "IPython", ipython_module)
    monkeypatch.setitem(sys.modules, "IPython.display", display_module)
    return FakeImage, FakeVideo


@pytest.mark.parametrize(
    ("fps", "max_frames", "max_width", "error_message"),
    [
        (0, 10, None, "fps"),
        (60, 0, None, "max_frames"),
        (60, 10, 0, "max_width"),
    ],
)
def test_encode_gif_from_frames_rejects_invalid_inputs(
    tmp_path: Path,
    fps: int,
    max_frames: int,
    max_width: int | None,
    error_message: str,
) -> None:
    """Given invalid GIF settings, when encoding frames, then ValueError is raised."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (8, 8), (0, 0, 0))
    image.save(frames_dir / "frame-000000.png")

    with pytest.raises(ValueError, match=error_message):
        encode_gif_from_frames(frames_dir, fps=fps, max_frames=max_frames, max_width=max_width)


def test_encode_gif_from_frames_requires_matching_pngs(tmp_path: Path) -> None:
    """Given empty frames directory, when encoding GIF, then ValueError is raised."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="No frame PNGs"):
        encode_gif_from_frames(frames_dir)


def test_encode_gif_from_frames_downsamples_when_max_frames_is_small(tmp_path: Path) -> None:
    """Given many PNG frames, when max_frames is smaller, then GIF frame count is bounded."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(10):
        image = Image.new("RGB", (40, 20), (idx * 20, 0, 0))
        image.save(frames_dir / f"frame-{idx:06d}.png")

    gif_bytes = encode_gif_from_frames(frames_dir, fps=60, max_frames=3, max_width=20)

    with Image.open(io.BytesIO(gif_bytes)) as gif:
        assert int(getattr(gif, "n_frames", 1)) <= 3
        assert gif.size[0] == 20


def test_display_animation_rejects_invalid_preference(tmp_path: Path) -> None:
    """Given invalid display preference, when rendering notebook media, then ValueError is raised."""
    result = _fake_animation_result(tmp_path)
    with pytest.raises(ValueError, match="Unsupported prefer"):
        display_animation(result, prefer="webm")  # type: ignore[arg-type]


def test_display_animation_raises_when_ipython_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    """Given missing IPython dependency, when displaying animation, then RuntimeError is raised."""
    original_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        """Raise module import error only for IPython packages."""
        if name.startswith("IPython"):
            raise ModuleNotFoundError("No module named 'IPython'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    result = _fake_animation_result(tmp_path)

    with pytest.raises(RuntimeError, match="IPython is required"):
        display_animation(result)


def test_display_animation_prefers_mp4_when_available(tmp_path: Path, monkeypatch) -> None:
    """Given MP4 output exists, when preference is auto, then Video display object is used."""
    _, fake_video = _install_fake_ipython(monkeypatch)
    result = _fake_animation_result(tmp_path, with_mp4=True)

    output = display_animation(result, prefer="auto", width=640, height=360)
    assert isinstance(output, fake_video)
    typed_output = cast(_DisplayObject, output)
    assert typed_output.kwargs["filename"].endswith("animation.mp4")


def test_display_animation_uses_gif_file_when_requested(tmp_path: Path, monkeypatch) -> None:
    """Given GIF output exists, when preference is gif, then Image display object is used."""
    fake_image, _ = _install_fake_ipython(monkeypatch)
    result = _fake_animation_result(tmp_path, with_gif=True)

    output = display_animation(result, prefer="gif")
    assert isinstance(output, fake_image)
    typed_output = cast(_DisplayObject, output)
    assert typed_output.kwargs["filename"].endswith("animation.gif")


def test_display_animation_encodes_gif_from_frames_when_media_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Given no MP4/GIF files, when displaying animation, then frames are encoded into GIF bytes."""
    fake_image, _ = _install_fake_ipython(monkeypatch)
    result = _fake_animation_result(tmp_path, with_mp4=False, with_gif=False)

    output = display_animation(result, prefer="auto", max_frames=5)
    assert isinstance(output, fake_image)
    typed_output = cast(_DisplayObject, output)
    assert typed_output.kwargs["format"] == "gif"
    assert isinstance(typed_output.kwargs["data"], bytes)


def test_display_animation_raises_for_mp4_preference_without_mp4(
    tmp_path: Path, monkeypatch
) -> None:
    """Given MP4 preference without MP4 file, when displaying animation, then RuntimeError is raised."""
    _install_fake_ipython(monkeypatch)
    result = _fake_animation_result(tmp_path, with_mp4=False, with_gif=True)

    with pytest.raises(RuntimeError, match="MP4 output is not available"):
        display_animation(result, prefer="mp4")


def test_resolve_notebook_render_options_toggles_mp4_based_on_ffmpeg(monkeypatch) -> None:
    """Given ffmpeg availability changes, when resolving notebook options, then mp4 toggles correctly."""
    monkeypatch.setattr("qave.notebook.shutil.which", lambda _name: None)
    no_ffmpeg = resolve_notebook_render_options(width=1280, height=720, fps=60)
    assert no_ffmpeg.emit_mp4 is False
    assert no_ffmpeg.keep_frames is True

    monkeypatch.setattr("qave.notebook.shutil.which", lambda _name: "/usr/bin/ffmpeg")
    with_ffmpeg = resolve_notebook_render_options()
    assert with_ffmpeg.emit_mp4 is True
    assert with_ffmpeg.keep_frames is False


def test_render_animation_runs_pipeline_and_merges_diagnostics(tmp_path: Path, monkeypatch) -> None:
    """Given trace result and render pipeline output, when rendering animation, then diagnostics are merged."""
    trace_result = _fake_trace_result(tmp_path)
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    expected_render = RenderOptions(
        width=320,
        height=240,
        fps=30,
        keep_frames=True,
        emit_mp4=False,
        emit_gif=False,
        sketch_dir=tmp_path / "sketch",
    )

    def _fake_run_render_pipeline(*, trace_path: Path, render: RenderOptions, out_dir: Path):
        """Return deterministic render outputs for notebook rendering tests."""
        assert trace_path == trace_result.paths.trace_json
        assert render == expected_render
        assert out_dir == trace_result.paths.out_dir
        return frames_dir, None, None, [DiagnosticEntry(code="RENDER", message="ok")]

    monkeypatch.setattr("qave.render.run_render_pipeline", _fake_run_render_pipeline)

    anim = render_animation(trace_result, render=expected_render)
    assert anim.frames_dir == frames_dir
    assert [item.code for item in anim.diagnostics] == ["TRACE", "RENDER"]
