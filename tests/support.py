"""Helpers shared by the tests (not a test module itself)."""

from __future__ import annotations

import io
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, cast

from PIL import Image

from petpet_gif import ImageSource

#: Anything :func:`petpet` accepts, re-exported so tests do not re-declare it.
Source = ImageSource
Point = tuple[int, int]
Pixel = tuple[int, int, int, int]


def _png_bytes(size: tuple[int, int] = (120, 90)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, (10, 20, 30, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


#: A small, completely opaque PNG, built once at import time.
PNG_BYTES = _png_bytes()


def as_source(value: object) -> ImageSource:
    """Escape hatch for the tests that deliberately pass the wrong type."""
    return cast("ImageSource", value)


def _read_bytes(source: Source) -> bytes:
    if isinstance(source, Image.Image):
        raise TypeError("gif_frames needs the encoded file, not a decoded image")
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if isinstance(source, (str, os.PathLike)):
        return Path(source).read_bytes()
    return cast("IO[bytes]", source).read()


def pixel(image: Image.Image, point: Point) -> Pixel:
    """``getpixel`` with the return union narrowed so the result can be indexed."""
    return cast("Pixel", image.getpixel(point))


def count_colour(image: Image.Image, colour: Pixel) -> int:
    """How many pixels are exactly ``colour``.

    Byte-level ``bytes.count`` is not usable here: it happily matches across
    pixel boundaries, so a pure blue frame "contains" red.
    """
    data = image.tobytes()
    bands = len(image.getbands())
    target = bytes(colour)
    return sum(1 for start in range(0, len(data), bands) if data[start : start + bands] == target)


class OneShotStream(io.BytesIO):
    """A stream that refuses to seek, like an HTTP response body."""

    def seekable(self) -> bool:
        return False


@contextmanager
def _opened(source: Source) -> Generator[Image.Image, None, None]:
    """Open ``source``, keeping the handle alive only for the caller's block."""
    if isinstance(source, Image.Image):
        yield source
        return
    if isinstance(source, (bytes, bytearray)):
        with Image.open(io.BytesIO(bytes(source))) as image:
            yield image
        return
    if isinstance(source, (str, os.PathLike)):
        with Image.open(Path(source)) as image:
            yield image
        return
    # A stream the caller owns: leave it open, as petpet() does.
    yield Image.open(cast("IO[bytes]", source))


def frame_delays(source: Source) -> list[int]:
    """Frame delays in milliseconds, straight out of the encoded GIF."""
    delays = []
    with _opened(source) as image:
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            delays.append(int(image.info.get("duration") or 0))
    return delays


def frame_alpha_boxes(source: Source) -> list[tuple[int, int, int, int] | None]:
    """Bounding box of the visible pixels on every frame."""
    boxes = []
    with _opened(source) as image:
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            boxes.append(image.convert("RGBA").getchannel("A").getbbox())
    return boxes


def frame_rgba(source: Source, index: int) -> Image.Image:
    """One frame as ``RGBA``."""
    with _opened(source) as image:
        image.seek(index)
        return image.convert("RGBA")


def frame_windows(source: Source) -> list[tuple[int, int, Image.Image]]:
    """Every frame with the ``[start, end)`` millisecond window it shows for.

    Pillow merges runs of identical frames when it encodes a GIF, so this is the
    only honest way to talk about *when* something is on screen.
    """
    windows = []
    start = 0
    with _opened(source) as image:
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            delay = int(image.info.get("duration") or 0)
            windows.append((start, start + delay, image.convert("RGBA")))
            start += delay
    return windows


def frame_count(source: Source) -> int:
    with _opened(source) as image:
        return int(getattr(image, "n_frames", 1))


@dataclass(frozen=True)
class GifFrame:
    """What the file itself says about one frame."""

    left: int
    top: int
    width: int
    height: int
    disposal: int
    transparent_index: int | None
    delay_ms: int


def gif_frames(source: Source) -> list[GifFrame]:
    """Walk the GIF blocks and report each frame's graphic control extension.

    Deliberately independent of any image library's decoder: Pillow's reader
    silently ignores some disposal methods, and the whole point of these
    assertions is to check what a viewer will actually be told.
    """
    data = _read_bytes(source)

    packed = data[10]
    cursor = 13 + (3 * 2 ** ((packed & 0x07) + 1) if packed & 0x80 else 0)
    frames: list[GifFrame] = []
    disposal = 0
    transparent_index: int | None = None
    delay_ms = 0

    while cursor < len(data):
        tag = data[cursor]
        if tag == 0x3B:  # trailer
            break
        if tag == 0x21:  # extension
            label = data[cursor + 1]
            cursor += 2
            blocks = []
            while data[cursor] != 0:
                size = data[cursor]
                blocks.append(data[cursor + 1 : cursor + 1 + size])
                cursor += 1 + size
            cursor += 1
            if label == 0xF9 and blocks:
                flags = blocks[0][0]
                disposal = (flags >> 2) & 0x07
                delay_ms = int.from_bytes(blocks[0][1:3], "little") * 10
                transparent_index = blocks[0][3] if flags & 0x01 else None
            continue
        if tag == 0x2C:  # image descriptor
            left = int.from_bytes(data[cursor + 1 : cursor + 3], "little")
            top = int.from_bytes(data[cursor + 3 : cursor + 5], "little")
            width = int.from_bytes(data[cursor + 5 : cursor + 7], "little")
            height = int.from_bytes(data[cursor + 7 : cursor + 9], "little")
            frame_packed = data[cursor + 9]
            cursor += 10
            if frame_packed & 0x80:
                cursor += 3 * 2 ** ((frame_packed & 0x07) + 1)
            cursor += 1  # LZW minimum code size
            while data[cursor] != 0:
                cursor += 1 + data[cursor]
            cursor += 1
            frames.append(
                GifFrame(
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    disposal=disposal,
                    transparent_index=transparent_index,
                    delay_ms=delay_ms,
                )
            )
            continue
        raise AssertionError(f"unexpected GIF block {tag:#04x} at offset {cursor}")  # pragma: no cover

    return frames
