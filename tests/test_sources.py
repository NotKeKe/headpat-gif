"""Reading overlays and subjects out of every supported container."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from headpat_gif import petpet
from support import (
    OneShotStream,
    Pixel,
    as_source,
    count_colour,
    frame_rgba,
    frame_windows,
    pixel,
)

RED: Pixel = (255, 0, 0, 255)
BLUE: Pixel = (0, 0, 255, 255)


def _two_frame_gif() -> bytes:
    first = Image.new("RGBA", (40, 40), (255, 0, 0, 255))
    second = Image.new("RGBA", (40, 40), (0, 0, 255, 255))
    buffer = io.BytesIO()
    first.save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=[second],
        duration=100,
        loop=0,
    )
    return buffer.getvalue()


def test_an_animated_overlay_plays_on_its_own_timeline(overlay_gif: bytes) -> None:
    transparent = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    gif = petpet(transparent, overlay_gif, fps=50, max_size=40)
    windows = frame_windows(gif.to_bytes())

    # The fixture is empty (0-50ms), red (50-100ms) and blue (100-150ms); the
    # overlay plays exactly once, so nothing shows once the cycle has ended.
    assert gif.cycle_ms == 150
    assert [start for start, _, frame in windows if count_colour(frame, RED)] == [60]
    assert [start for start, _, frame in windows if count_colour(frame, BLUE)] == [100]
    assert windows[-1][1] == 150


def test_a_still_overlay_holds_for_the_configured_cycle(still_overlay: Image.Image) -> None:
    subject = Image.new("RGBA", (40, 40), (255, 255, 255, 255))

    assert petpet(subject, still_overlay, static_overlay_ms=250).cycle_ms == 250
    assert petpet(subject, still_overlay).cycle_ms == 500


def test_an_animated_subject_uses_its_first_frame() -> None:
    # A transparent overlay keeps the subject itself visible in the middle.
    invisible = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    gif = petpet(_two_frame_gif(), invisible, duration=0.2, max_size=40)
    middle = pixel(frame_rgba(gif.to_bytes(), 0), (20, 20))

    assert middle[0] > 200
    assert middle[2] < 60


def test_a_still_overlay_survives_a_non_seekable_stream(still_overlay: Image.Image) -> None:
    buffer = io.BytesIO()
    still_overlay.save(buffer, format="PNG")
    subject = Image.new("RGBA", (40, 40), (255, 255, 255, 255))

    gif = petpet(subject, OneShotStream(buffer.getvalue()), duration=0.2)

    assert gif.n_frames > 0


def test_an_unsupported_overlay_reports_the_parameter_name(subject: Image.Image) -> None:
    with pytest.raises(TypeError, match="overlay"):
        petpet(subject, as_source(object()))


def test_a_missing_overlay_file_is_reported(work_dir: Path, subject: Image.Image) -> None:
    with pytest.raises(FileNotFoundError, match="overlay"):
        petpet(subject, work_dir / "missing.gif")


@pytest.mark.parametrize("mode", ["RGB", "L", "LA", "P", "CMYK"])
def test_any_pillow_mode_is_accepted(mode: str) -> None:
    source = Image.new(mode, (30, 30))

    assert petpet(source, duration=0.2).n_frames > 0


def test_exif_rotation_is_applied(work_dir: Path) -> None:
    # Orientation 6 = rotate 90 degrees clockwise when displaying.
    source = Image.new("RGB", (40, 20), (255, 0, 0))
    exif = Image.Exif()
    exif[274] = 6
    path = work_dir / "rotated.jpg"
    source.save(path, exif=exif)

    assert petpet(path, duration=0.2, max_size=40, overlay_offset=(0.0, 0.0)).size == (20, 40)
