"""The public entry points."""

from __future__ import annotations

import io
import math
import os
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageColor

from ._assets import load_default_overlay
from ._compose import MIN_DELAY_MS, plan_timeline, render_frames
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
#: How much of the cover fit the overlay is drawn at when the caller says nothing.
DEFAULT_OVERLAY_SCALE = 0.8
#: Where the overlay sits by default: lifted a sixth of the canvas above the
#: picture's top edge, so the hand hangs over the picture instead of starting
#: level with it. The canvas grows to keep the whole hand, which is why the
#: default output is taller than the input's aspect ratio.
DEFAULT_OVERLAY_OFFSET = (0.0, -0.15)

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
    overlay_scale: float | None = DEFAULT_OVERLAY_SCALE,
    overlay_offset: tuple[float, float] = DEFAULT_OVERLAY_OFFSET,
    overlay_position: tuple[float, float] = (0.0, 0.0),
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
        overlay_scale: Size of the overlay. The overlay is always scaled
            **uniformly**, by whichever of the canvas' two dimensions asks for the
            bigger factor, so it keeps its shape on a wide or tall image. The
            default (``0.8``) draws it at 80% of that cover fit, big enough to
            dominate the picture without burying it; ``None`` or ``1.0`` is the
            full cover fit, and a small value puts the hand down in a corner of the
            canvas instead.
        overlay_offset: Moves the overlay, as a fraction of the canvas:
            ``(0.0, -0.3)`` pushes it up by 30% of the height, ``(0.1, 0.0)`` to
            the right. Overlay that the offset moves past an edge grows the
            canvas to keep it visible, so pushing the hand up makes the returned
            image taller (``gif.size`` reflects that) while the subject keeps its
            size and its place near the bottom. The default, ``(0.0, -0.15)``,
            lifts the hand so it hangs over the picture rather than starting level
            with it - which is why the default output is 15% taller than the
            input's aspect ratio. Pass ``(0.0, 0.0)`` for a canvas that matches
            the picture exactly.
        overlay_position: The spot the overlay's visible top-left corner is pinned
            to, as a fraction of the canvas: ``(0.0, 0.0)`` (the default) is the
            canvas' own corner - the corner of the finished GIF, so the overlay
            touches its left and top edges - while ``(0.5, 0.5)`` is the middle
            and ``(1.0, 1.0)`` the bottom-right corner. Overflow past the canvas
            edge is cropped.
        static_overlay_ms: Cycle length used when ``overlay`` is not animated.
        background: Colour to flatten transparency onto, e.g. ``"white"`` or
            ``(255, 255, 255)``. ``None`` keeps the canvas transparent.
        name: Filename reported to Discord for the attachment.

    Returns:
        A :class:`~headpat_gif.PetPetGif`, i.e. an ``io.BytesIO`` that
        ``discord.File`` accepts directly.

    Raises:
        TypeError: If ``image`` or ``overlay`` is not a supported image source.
        ValueError: If an argument is outside its documented range.
        FileNotFoundError: If a path or the packaged default asset is missing.

    Example:
        >>> from headpat_gif import petpet
        >>> gif = petpet("pet.png", duration=2.0, speed=1.5)
        >>> _ = gif.save("pet.gif")
    """
    _validate(
        duration=duration,
        speed=speed,
        fps=fps,
        max_size=max_size,
        image_scale=image_scale,
        squash=squash,
        overlay_scale=overlay_scale,
        overlay_position=overlay_position,
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
        overlay_position=overlay_position,
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
    overlay_position: tuple[float, float],
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
    for axis, value in zip("xy", overlay_position, strict=True):
        if not math.isfinite(value):
            raise ValueError(
                f"overlay_position {axis} must be a finite number, got {value!r}"
            )
    if static_overlay_ms < MIN_DELAY_MS:
        raise ValueError(
            f"static_overlay_ms must be at least {MIN_DELAY_MS}, got {static_overlay_ms!r}"
        )
