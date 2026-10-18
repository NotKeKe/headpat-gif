"""The public entry points."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageColor

from ._assets import load_default_overlay
from ._compose import (
    ANCHORS,
    MIN_DELAY_MS,
    OverlayAnchor,
    plan_timeline,
    render_frames,
)
from ._palette import save_transparent_gif
from ._result import PetPetGif
from ._sources import ImageSource, load_first_frame, load_overlay_frames

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PIL.Image import Image as PILImage

    from ._compose import RGBA

__all__ = ["petpet", "save"]

#: Delay used for one cycle when the overlay is a still image.
DEFAULT_STATIC_OVERLAY_MS = 500

ColorLike = str | tuple[int, int, int] | tuple[int, int, int, int]


def petpet(
    image: ImageSource,
    overlay: ImageSource | None = None,
    *,
    duration: float | None = None,
    speed: float = 1.0,
    loop: bool = True,
    fps: int = 25,
    max_size: int = 256,
    image_scale: float = 0.8,
    squash: float = 1.0,
    overlay_scale: float | None = None,
    overlay_offset: tuple[float, float] = (0.0, 0.0),
    overlay_anchor: OverlayAnchor = "top",
    static_overlay_ms: int = DEFAULT_STATIC_OVERLAY_MS,
    background: ColorLike | None = None,
    name: str = "petpet.gif",
) -> PetPetGif:
    """Build a "pet-pet" GIF and return it as a sendable object.

    The subject is squashed and sprung back underneath an animated overlay that
    plays exactly once, the way clicking a pet in the reference demo behaves.

    Args:
        image: The subject being patted - a filename, path, ``bytes``, binary
            file object or ``PIL.Image.Image``. Animated input uses its first
            frame.
        overlay: What appears on the head. Any image or GIF; defaults to the
            bundled transparent patting hand.
        duration: Total length of the returned GIF in seconds. ``None`` produces
            exactly one cycle. A longer value is padded with a still resting
            frame unless ``loop`` is set; a shorter value cuts the cycle short -
            reach for ``speed`` instead when the goal is a faster pat.
        speed: Playback rate multiplier for the cycle. ``2.0`` plays the same
            pat twice as fast inside the same ``duration``.
        loop: Repeat the cycle until ``duration`` is filled instead of resting
            after one pat. On by default, so a longer ``duration`` keeps the pet
            being patted. Ignored when ``duration`` is ``None`` (one cycle) or
            already shorter than one cycle.
        fps: Output sampling rate, 10 to 50. GIF delays under 20ms are clamped
            by browsers and Discord, so 50 is the useful maximum.
        max_size: Longest side of the canvas in pixels; the aspect ratio of
            ``image`` is always preserved.
        image_scale: Size of the subject inside the canvas, as a fraction, once
            it is back to normal.
        squash: Squash strength multiplier. ``0`` disables the squash entirely,
            ``1`` matches the amplitude of the reference implementation.
        overlay_scale: Size of the overlay. ``None`` (the default) stretches it
            over the whole canvas - the overlay is authored for the canvas, so a
            patting hand covers the picture the way it does in
            https://github.com/camprevail/pet-pet-gif. A number scales it to that
            fraction of a snug, aspect preserving fit instead, e.g. ``0.4`` for a
            small hand resting on the head.
        overlay_offset: Moves the overlay, as a fraction of the canvas:
            ``(0.0, -0.3)`` pushes it up by 30% of the height, ``(0.1, 0.0)`` to
            the right. Nothing gets sliced off - if the overlay leaves the
            canvas, the canvas **grows** to include it, so pushing the hand up
            makes the returned image taller (``gif.size`` reflects that) while
            the subject keeps its size and its place near the bottom. Note that
            the bundled hand already sits in the upper part of its own frame, so
            nudging *up* shows less hand.
        overlay_anchor: Where a shrunken overlay sits in the canvas: ``"top"``
            (the default), ``"center"`` or ``"bottom"``. Only matters when
            ``overlay_scale`` makes the overlay smaller than the canvas.
        static_overlay_ms: Cycle length used when ``overlay`` is not animated.
        background: Colour to flatten transparency onto, e.g. ``"white"`` or
            ``(255, 255, 255)``. ``None`` keeps the canvas transparent.
        name: Filename reported to Discord for the attachment.

    Returns:
        A :class:`~petpet_gif.PetPetGif`, i.e. an ``io.BytesIO`` that
        ``discord.File`` accepts directly.

    Raises:
        TypeError: If ``image`` or ``overlay`` is not a supported image source.
        ValueError: If an argument is outside its documented range.
        FileNotFoundError: If a path or the packaged default asset is missing.

    Example:
        >>> from petpet_gif import petpet
        >>> gif = petpet("goat.png", duration=2.0, speed=1.5)
        >>> _ = gif.save("goat-pet.gif")
    """
    _validate(
        duration=duration,
        speed=speed,
        fps=fps,
        max_size=max_size,
        image_scale=image_scale,
        squash=squash,
        overlay_scale=overlay_scale,
        overlay_anchor=overlay_anchor,
        static_overlay_ms=static_overlay_ms,
    )

    base = load_first_frame(image, what="image")
    raw_frames = (
        load_overlay_frames(load_default_overlay(), what="overlay")
        if overlay is None
        else load_overlay_frames(overlay, what="overlay")
    )

    frames = _normalize_overlay(raw_frames, static_overlay_ms)
    overlay_ms = sum(delay for _, delay in frames)

    timeline = plan_timeline(
        overlay_ms=overlay_ms,
        speed=speed,
        duration=duration,
        fps=fps,
        repeat=loop,
    )
    rendered, canvas_size = render_frames(
        base,
        frames,
        timeline,
        max_size=max_size,
        image_scale=image_scale,
        squash=squash,
        overlay_scale=overlay_scale,
        overlay_offset=overlay_offset,
        overlay_anchor=overlay_anchor,
        background=_background_rgba(background),
    )

    buffer = io.BytesIO()
    save_transparent_gif(rendered, list(timeline.delays), buffer)
    payload = buffer.getvalue()
    return PetPetGif(
        payload,
        name=name,
        size=canvas_size,
        n_frames=_encoded_frame_count(payload),
        duration_ms=timeline.total_ms,
        cycle_ms=timeline.cycle_ms,
    )


def save(gif: PetPetGif, path: str | os.PathLike[str]) -> Path:
    """Write ``gif`` to ``path`` and return the resulting :class:`~pathlib.Path`."""
    return gif.save(path)


def _encoded_frame_count(payload: bytes) -> int:
    """Frame count of the finished file.

    Pillow merges runs of identical frames into one frame with a longer delay,
    so the number of frames that were rendered is not necessarily the number of
    frames a viewer will see. Reading the count back keeps the metadata honest.
    """
    with Image.open(io.BytesIO(payload)) as image:
        return int(getattr(image, "n_frames", 1))


def _normalize_overlay(
    frames: Sequence[tuple[PILImage, int]], static_overlay_ms: int
) -> list[tuple[PILImage, int]]:
    """Give every overlay frame a sane delay in milliseconds."""
    if len(frames) == 1:
        return [(frames[0][0], max(MIN_DELAY_MS, static_overlay_ms))]
    return [(frame, max(MIN_DELAY_MS, delay)) for frame, delay in frames]


def _background_rgba(color: ColorLike | None) -> RGBA | None:
    if color is None:
        return None
    if isinstance(color, str):
        try:
            rgb = ImageColor.getrgb(color)
        except ValueError as exc:
            raise ValueError(f"background is not a colour: {color!r}") from exc
    else:
        rgb = color
        if len(rgb) not in (3, 4) or any(channel < 0 or channel > 255 for channel in rgb):
            raise ValueError(f"background is not a colour: {color!r}")
    if len(rgb) == 3:
        return (rgb[0], rgb[1], rgb[2], 255)
    return (rgb[0], rgb[1], rgb[2], rgb[3])


def _validate(
    *,
    duration: float | None,
    speed: float,
    fps: int,
    max_size: int,
    image_scale: float,
    squash: float,
    overlay_scale: float | None,
    overlay_anchor: str,
    static_overlay_ms: int,
) -> None:
    if duration is not None and duration <= 0:
        raise ValueError(f"duration must be greater than 0 seconds, got {duration!r}")
    if speed <= 0:
        raise ValueError(f"speed must be greater than 0, got {speed!r}")
    if not 10 <= fps <= 50:
        raise ValueError(f"fps must be between 10 and 50, got {fps!r}")
    if max_size < 8:
        raise ValueError(f"max_size must be at least 8 pixels, got {max_size!r}")
    if image_scale <= 0:
        raise ValueError(f"image_scale must be greater than 0, got {image_scale!r}")
    if squash < 0:
        raise ValueError(f"squash must not be negative, got {squash!r}")
    if overlay_scale is not None and overlay_scale <= 0:
        raise ValueError(f"overlay_scale must be greater than 0, got {overlay_scale!r}")
    if overlay_anchor not in ANCHORS:
        raise ValueError(f"overlay_anchor must be one of {ANCHORS}, got {overlay_anchor!r}")
    if static_overlay_ms < MIN_DELAY_MS:
        raise ValueError(
            f"static_overlay_ms must be at least {MIN_DELAY_MS}, got {static_overlay_ms!r}"
        )
