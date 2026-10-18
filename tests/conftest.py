"""Shared fixtures.

Everything is built in memory so the suite never depends on files on disk or on
the network, except for the one asset that really does ship in the wheel and the
few tests that exercise saving to a path.
"""

from __future__ import annotations

import io
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from petpet_gif import petpet

if TYPE_CHECKING:
    from collections.abc import Iterator

#: A subject with a solid, easy to measure silhouette on a transparent canvas.
SUBJECT_SIZE = (120, 90)


def _subject() -> Image.Image:
    image = Image.new("RGBA", SUBJECT_SIZE, (0, 0, 0, 0))
    body = Image.new("RGBA", (60, 40), (200, 180, 140, 255))
    image.paste(body, (30, 30))
    return image


def _square(colour: tuple[int, int, int, int] = (255, 0, 0, 255)) -> Image.Image:
    return Image.new("RGBA", (20, 20), colour)


def _animated_overlay_bytes(frame_ms: int = 50) -> bytes:
    """A three frame GIF: transparent, red square, blue square.

    ``disposal=3`` matters here too: without it Pillow encodes later frames as
    deltas against the previous frame, and a decoder is free to keep the red
    square showing through the transparent half of the blue frame.
    """
    frames = [
        Image.new("RGBA", (20, 20), (0, 0, 0, 0)),
        _square(),
        Image.new("RGBA", (20, 20), (0, 0, 0, 0)),
    ]
    frames[2].paste(_square((0, 0, 255, 255)), (10, 0))
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=frame_ms,
        loop=0,
        disposal=3,
    )
    return buffer.getvalue()


@pytest.fixture
def subject() -> Image.Image:
    """A fresh opaque subject on a transparent canvas."""
    return _subject()


@pytest.fixture
def invisible() -> Image.Image:
    """A one pixel, fully transparent overlay: renders the squash on its own."""
    return Image.new("RGBA", (1, 1), (0, 0, 0, 0))


@pytest.fixture
def overlay_gif() -> bytes:
    """A three frame, 50ms per frame transparent GIF."""
    return _animated_overlay_bytes()


@pytest.fixture
def still_overlay() -> Image.Image:
    """A still image usable as an overlay."""
    return _square()


@pytest.fixture
def make_gif(subject: Image.Image):
    """Build a GIF from ``subject`` with overridable kwargs."""

    def factory(**kwargs) -> bytes:
        kwargs.setdefault("duration", 0.5)
        gif = petpet(subject, **kwargs)
        return gif.to_bytes()

    return factory


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "test"


@pytest.fixture
def work_dir(request: pytest.FixtureRequest) -> Iterator[Path]:
    """A throwaway directory for the tests that need real files on disk.

    Deliberately not pytest's ``tmp_path``: that fixture builds its base
    directory with ``mode=0o700``, and this project is developed inside the DSH
    Windows sandbox, where a directory created with that mode can no longer be
    listed - which kills the whole session at teardown. It is also why
    ``tempfile.mkdtemp`` is avoided here. Creating directories with the default
    mode behaves the same everywhere else, so tests stay portable.
    """
    root = Path(__file__).resolve().parent / "_tmp"
    root.mkdir(exist_ok=True)
    path = root / _slug(request.node.name)
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
