"""Read the many shapes of user input into plain Pillow frames."""

from __future__ import annotations

import io
import os
from contextlib import closing, contextmanager
from pathlib import Path
from typing import IO, TYPE_CHECKING, TypeAlias

from PIL import Image, ImageOps
from PIL.Image import Image as PILImage

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ["ImageSource", "load_first_frame", "load_overlay_frames"]

#: Everything :func:`petpet` accepts as an image: a path, raw bytes, a binary
#: file object or an already opened Pillow image.
ImageSource: TypeAlias = str | os.PathLike[str] | bytes | bytearray | IO[bytes] | PILImage


def _is_seekable(stream: IO[bytes]) -> bool:
    try:
        return bool(stream.seekable())
    except (AttributeError, OSError, ValueError):
        return False


def _as_seekable(stream: IO[bytes]) -> IO[bytes]:
    # Pillow needs to seek while probing the header, so one-shot streams such as
    # HTTP responses or pipes are buffered in full first.
    if _is_seekable(stream):
        return stream
    return io.BytesIO(stream.read())


def _open(source: ImageSource, *, what: str) -> PILImage:
    if isinstance(source, PILImage):
        return source
    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(bytes(source)))
    if isinstance(source, (str, os.PathLike)):
        try:
            return Image.open(Path(source))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"{what}: no such file: {source!r}") from exc
    if hasattr(source, "read"):
        return Image.open(_as_seekable(source))
    raise TypeError(
        f"{what} must be a filename, path, bytes, a binary file object or a "
        f"PIL.Image.Image, not {type(source).__name__}"
    )


@contextmanager
def _opened(source: ImageSource, *, what: str) -> Generator[PILImage, None, None]:
    """Yield ``source`` as an image, closing only a file we opened ourselves.

    A ``PIL.Image.Image`` handed in by the caller stays usable afterwards, and
    so does a stream they passed: only Pillow-owned handles are released.
    """
    if isinstance(source, PILImage):
        yield source
        return
    with closing(_open(source, what=what)) as image:
        yield image


def load_first_frame(source: ImageSource, *, what: str = "image") -> PILImage:
    """Open ``source`` and return its first frame as an upright ``RGBA`` image."""
    with _opened(source, what=what) as image:
        image.load()
        return ImageOps.exif_transpose(image).convert("RGBA")


def load_overlay_frames(
    source: ImageSource, *, what: str = "overlay"
) -> list[tuple[PILImage, int]]:
    """Open ``source`` and return every frame as ``(RGBA image, delay in ms)``.

    Static images yield a single frame with a delay of ``0``, which the caller
    replaces with the requested static duration.
    """
    frames: list[tuple[PILImage, int]] = []
    with _opened(source, what=what) as image:
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            duration = image.info.get("duration")
            frames.append((image.convert("RGBA"), int(duration) if duration else 0))
    return frames
