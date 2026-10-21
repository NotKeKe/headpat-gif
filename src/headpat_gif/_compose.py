"""Compose the squash-and-spring canvas frames.

The subject is anchored by its bottom edge and squeezed on a triangular
envelope: untouched at the start of a cycle, widest and shortest in the middle,
untouched again at the end. Amplitude constants are the ones used by
https://github.com/camprevail/pet-pet-gif (0.8 -> 0.9 wide, 0.8 -> 0.55 tall)
so the motion feels identical to the GIFs people already know.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import ceil
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PIL.Image import Image as PILImage

__all__ = [
    "BOTTOM_ANCHOR",
    "HEIGHT_SWING",
    "MIN_DELAY_MS",
    "WIDTH_SWING",
    "Timeline",
    "canvas_size_for",
    "overlay_sprite_size",
    "plan_timeline",
    "render_frames",
]

#: Browsers and Discord clamp GIF frame delays below 20ms, so never go under it.
MIN_DELAY_MS = 20
#: Distance from the canvas bottom to the subject's bottom edge.
BOTTOM_ANCHOR = 0.92
#: Extra width, as a fraction of the canvas, at full squash.
WIDTH_SWING = 0.10
#: Lost height, as a fraction of the canvas, at full squash.
HEIGHT_SWING = 0.25

RGBA = tuple[int, int, int, int]


def round_to_10ms(milliseconds: float) -> int:
    """Round to the 10ms resolution a GIF delay is actually stored in."""
    return round(milliseconds / 10.0) * 10


def canvas_size_for(base: PILImage, max_size: int) -> tuple[int, int]:
    """Return the canvas size: ``base`` scaled down to fit a ``max_size`` square.

    The aspect ratio is preserved, so resizing the subject to a fraction of the
    canvas never distorts it.
    """
    scale = max_size / max(base.width, base.height)
    return max(1, round(base.width * scale)), max(1, round(base.height * scale))


@dataclass(frozen=True, slots=True)
class Timeline:
    """When each output frame is shown, and where in the pat it sits."""

    cycle_ms: int
    total_ms: int
    delays: tuple[int, ...]
    #: Position inside one pat, as a fraction of the overlay's own timeline.
    #: ``None`` marks the resting frame shown after the pat has finished.
    progress: tuple[float | None, ...]

    @property
    def n_frames(self) -> int:
        return len(self.delays)


def _cycle_starts(cycle_ms: int, step_ms: int) -> list[int]:
    """When each frame of one cycle starts, in milliseconds.

    The cycle is sampled every ``step_ms``, but the last frame absorbs the
    remainder so the frame delays always add up to ``cycle_ms`` exactly and no
    frame is shorter than :data:`MIN_DELAY_MS` - a short frame would be clamped
    to 100ms by GIF viewers and stretch the whole animation.
    """
    steps = max(1, ceil(cycle_ms / step_ms))
    if steps > 1 and cycle_ms - (steps - 1) * step_ms < MIN_DELAY_MS:
        steps -= 1
    starts = [index * step_ms for index in range(steps) if index * step_ms < cycle_ms]
    return starts or [0]


def _delays_for(starts: Sequence[int], end_ms: int) -> list[int]:
    """Frame delays for frames starting at ``starts`` and ending at ``end_ms``."""
    kept = [start for start in starts if start < end_ms] or [0]
    delays = [
        (kept[index + 1] if index + 1 < len(kept) else end_ms) - start
        for index, start in enumerate(kept)
    ]
    if len(delays) > 1 and delays[-1] < MIN_DELAY_MS:
        # A truncated cycle can leave a sliver; hold the previous pose instead.
        delays[-2] += delays[-1]
        delays.pop()
    return delays


def plan_timeline(
    *,
    overlay_ms: int,
    speed: float,
    duration: float | None,
    fps: int,
    repeat: bool,
) -> Timeline:
    """Lay out the output frames.

    One "pet" cycle lasts ``overlay_ms / speed``. ``duration`` is the total
    length of the returned GIF.

    * ``duration`` shorter than one cycle: the cycle is cut short.
    * ``duration`` longer, ``repeat`` set: the cycle runs again, and the total is
      divided into a whole number of cycles so the GIF loops without a visible
      jump (the cycle length is nudged by well under one frame to make that fit).
    * ``duration`` longer, ``repeat`` clear: one cycle, then a single resting
      frame holding until ``duration``.
    """
    step_ms = max(MIN_DELAY_MS, round_to_10ms(1000.0 / fps))
    cycle_ms = max(step_ms, round_to_10ms(overlay_ms / speed))
    total_ms = max(step_ms, round_to_10ms(duration * 1000.0)) if duration is not None else cycle_ms
    starts = _cycle_starts(cycle_ms, step_ms)
    fractions = [start / cycle_ms for start in starts]
    progress: list[float | None]

    if total_ms <= cycle_ms:
        pairs = [
            (start, fraction)
            for start, fraction in zip(starts, fractions, strict=True)
            if start < total_ms
        ]
        pairs = pairs or [(0, 0.0)]
        delays = _delays_for([start for start, _ in pairs], total_ms)
        progress = [fraction for _, fraction in pairs]
    elif repeat:
        cycles = max(1, round(total_ms / cycle_ms))
        scaled = total_ms / cycles
        pairs = []
        previous = -MIN_DELAY_MS
        for index in range(cycles * len(fractions)):
            cycle, position = divmod(index, len(fractions))
            # GIF stores delays in hundredths of a second, so every frame
            # boundary has to be a multiple of 10ms or the format rounds it away.
            moment = round_to_10ms((cycle + fractions[position]) * scaled)
            # Rounding must never squeeze a frame below the viewer clamp.
            moment = max(moment, previous + MIN_DELAY_MS)
            pairs.append((moment, fractions[position]))
            previous = moment
        delays = _delays_for([moment for moment, _ in pairs], total_ms)
        progress = [fraction for _, fraction in pairs]
    else:
        delays = [*_delays_for(starts, cycle_ms), total_ms - cycle_ms]
        progress = [*fractions, None]

    # `_delays_for` can drop a trailing sliver; keep both lists aligned.
    progress = progress[: len(delays)]
    return Timeline(
        cycle_ms=cycle_ms,
        total_ms=total_ms,
        delays=tuple(delays),
        progress=tuple(progress),
    )


def overlay_sprite_size(
    frame: PILImage, box: tuple[int, int], factor: float | None
) -> tuple[int, int]:
    """Size the overlay is drawn at, before any offset moves it.

    The overlay's **width** is matched to the canvas' width and its height
    follows from the overlay's own aspect ratio - the same factor on both axes,
    so a portrait hand stays a portrait hand.

    Matching the width is what keeps the hand the same size whatever shape the
    picture is. Picking whichever axis wants the bigger factor instead ("cover")
    makes a 9:16 picture scale the hand by its *height*, so the hand comes out
    1.7x wider than the frame and the picture disappears underneath it.

    ``factor`` (the caller's ``overlay_scale``) multiplies the width match;
    ``None`` uses it as-is. Height that runs past the canvas is cropped, which is
    what a hand coming down over a picture is supposed to look like.
    """
    zoom = 1.0 if factor is None else factor
    ratio = box[0] / frame.width * zoom
    return max(1, round(frame.width * ratio)), max(1, round(frame.height * ratio))


def _sized_overlay(frame: PILImage, box: tuple[int, int], factor: float | None) -> PILImage:
    return frame.resize(overlay_sprite_size(frame, box, factor), Image.Resampling.LANCZOS)


def _overlay_index(offsets: Sequence[int], moment: int) -> int:
    """Index of the overlay frame visible at ``moment`` milliseconds."""
    index = bisect_right(offsets, moment) - 1
    return min(max(index, 0), len(offsets) - 2)


def _squeeze_at(progress: float) -> float:
    """Squash amount for a position inside one pat: 0 at the ends, 1 in the middle."""
    return 1.0 - abs(2.0 * min(max(progress, 0.0), 1.0) - 1.0)


def _visible_origin(overlay: Sequence[tuple[PILImage, int]]) -> tuple[float, float]:
    """Top-left corner of the overlay's visible pixels, as a fraction of its frame.

    Measured across every frame and taking the corner that reaches furthest out,
    so an overlay whose hand travels downwards does not make the picture jitter.
    The bundled hand has a few empty rows above it, and aligning the *frame*
    instead of the pixels would leave a gap between the hand and the edge it is
    meant to touch.
    """
    boxes = [frame.getchannel("A").getbbox() for frame, _ in overlay]
    visible = [box for box in boxes if box is not None]
    if not visible:
        return (0.0, 0.0)
    first = overlay[0][0]
    return (
        min(box[0] for box in visible) / first.width,
        min(box[1] for box in visible) / first.height,
    )


def _overlay_placements(
    overlay: Sequence[tuple[PILImage, int]],
    box: tuple[int, int],
    *,
    overlay_scale: float | None,
    overlay_offset: tuple[float, float],
    overlay_position: tuple[float, float],
    origin: tuple[float, float],
) -> list[tuple[int, int, int, int]]:
    """Where each overlay frame is drawn in the un-grown canvas: left, top, w, h.

    ``overlay_position`` is the spot the overlay's visible top-left corner is
    pinned to, as a fraction of the canvas: ``(0.0, 0.0)`` is the canvas' own
    corner, which is the corner of the finished GIF - not of the picture inside
    it, because ``image_scale`` leaves a margin around that.
    """
    left = round(overlay_position[0] * box[0])
    top = round(overlay_position[1] * box[1])
    placements = []
    for frame, _ in overlay:
        width, height = overlay_sprite_size(frame, box, overlay_scale)
        placements.append(
            (
                left - round(origin[0] * width) + round(overlay_offset[0] * box[0]),
                top - round(origin[1] * height) + round(overlay_offset[1] * box[1]),
                width,
                height,
            )
        )
    return placements


def _overflow(
    placements: Sequence[tuple[int, int, int, int]], box: tuple[int, int]
) -> tuple[int, int, int, int]:
    """How far the overlay reaches past each canvas edge: left, top, right, bottom."""
    return (
        max(0, -min(left for left, _, _, _ in placements)),
        max(0, -min(top for _, top, _, _ in placements)),
        max(0, max(left + width for left, _, width, _ in placements) - box[0]),
        max(0, max(top + height for _, top, _, height in placements) - box[1]),
    )


def render_frames(
    base: PILImage,
    overlay: Sequence[tuple[PILImage, int]],
    timeline: Timeline,
    *,
    max_size: int,
    image_scale: float,
    squash: float,
    overlay_scale: float | None,
    overlay_offset: tuple[float, float],
    overlay_position: tuple[float, float],
    background: RGBA | None = None,
) -> tuple[list[PILImage], tuple[int, int]]:
    """Render every frame, and report the canvas size they ended up needing.

    The canvas is the size of the subject. Overlay that reaches past an edge is
    simply cropped - a hand pinned to the canvas' corner runs off it by design -
    except when ``overlay_offset`` is what moved it there: then the canvas grows
    by exactly the displacement, so nudging the hand still never slices it off.
    The subject keeps its size and its place near the bottom.
    """
    box = canvas_size_for(base, max_size)
    origin = _visible_origin(overlay)
    moved = _overlay_placements(
        overlay,
        box,
        overlay_scale=overlay_scale,
        overlay_offset=overlay_offset,
        overlay_position=overlay_position,
        origin=origin,
    )
    natural = _overlay_placements(
        overlay,
        box,
        overlay_scale=overlay_scale,
        overlay_offset=(0.0, 0.0),
        overlay_position=overlay_position,
        origin=origin,
    )
    # The canvas grows by the *displacement* the offset caused, not by however
    # far the overlay already reaches past the edge on its own.
    natural_overflow = _overflow(natural, box)
    moved_overflow = _overflow(moved, box)
    extra = [
        max(0, after - before)
        for after, before in zip(moved_overflow, natural_overflow, strict=True)
    ]
    shift_x, shift_y = extra[0], extra[1]
    canvas_size = (box[0] + extra[0] + extra[2], box[1] + extra[1] + extra[3])

    offsets = [0]
    for _, delay in overlay:
        offsets.append(offsets[-1] + delay)
    overlay_ms = offsets[-1]

    frames: list[PILImage] = []
    for _delay, progress in zip(timeline.delays, timeline.progress, strict=True):
        squeeze = 0.0 if progress is None else _squeeze_at(progress)
        canvas = Image.new("RGBA", canvas_size, background or (0, 0, 0, 0))

        width = max(0.01, image_scale + WIDTH_SWING * squash * squeeze)
        height = max(0.01, image_scale - HEIGHT_SWING * squash * squeeze)
        subject = base.resize(
            (max(1, round(box[0] * width)), max(1, round(box[1] * height))),
            Image.Resampling.LANCZOS,
        )
        canvas.paste(
            subject,
            (
                shift_x + (box[0] - subject.width) // 2,
                shift_y + round(box[1] * BOTTOM_ANCHOR) - subject.height,
            ),
            subject,
        )

        if progress is not None:
            index = _overlay_index(offsets, round(progress * overlay_ms))
            sprite_left, sprite_top, _, _ = moved[index]
            sprite = _sized_overlay(overlay[index][0], box, overlay_scale)
            canvas.paste(sprite, (shift_x + sprite_left, shift_y + sprite_top), sprite)

        frames.append(canvas)

    return frames, canvas_size
