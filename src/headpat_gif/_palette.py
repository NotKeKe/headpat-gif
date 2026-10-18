"""Animated GIF output that keeps hard-edged transparency.

GIF has no alpha channel: every frame is written in palette (``P``) mode and at
most one palette index may be marked transparent. Writing ``RGBA`` frames
straight to Pillow makes transparent pixels come out black and leaves ghosting
between frames, which is exactly the classic "black box around the pet" bug.

Two things are needed for a correct file:

1. each frame is converted to ``P`` mode up front with a dedicated transparent
   index (``0``), so a transparent pixel is *stored* as transparent instead of
   being flattened to black;
2. the frames use disposal method **3** ("restore to previous"), so the canvas
   is put back the way it was before each frame was drawn.

Point 2 is what makes the animation actually correct, and it is a deliberate
departure from the upstream workaround, which uses disposal 2 ("restore to
background"). Restoring to the background restores the *background colour*, and
decoders disagree about what that means when the background is the transparent
index: FFmpeg paints it opaque black, Pillow keeps the previous frame, and only
some browsers treat it as transparent. Either way the result is a black box or a
stale overlay - which nobody notices in the classic pet-pet GIFs, because there
the paw sits in the same place in every frame, but which is glaring the moment
an overlay moves or leaves. Disposal 3 gives every frame exactly the pixels that
were rendered for it, in FFmpeg, Pillow and browsers alike.

The palette half is a deterministic port of the technique published by egocarib
in https://github.com/python-pillow/Pillow/issues/4644 and used by
https://github.com/camprevail/pet-pet-gif (both MIT). See ``NOTICE``.
"""

from __future__ import annotations

import os
from itertools import chain
from typing import IO, TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PIL.Image import Image as PILImage

__all__ = ["save_transparent_gif", "to_transparent_frame"]

_PALETTE_SLOTS = frozenset(range(256))
#: One slot is reserved for the transparent index, so 255 colours remain.
_MAX_COLOURS = 255

SaveTarget = str | os.PathLike[str] | IO[bytes]


def _pick_unused_color(used: frozenset[tuple[int, int, int]]) -> tuple[int, int, int]:
    """Return a deterministic RGB triple that is not part of ``used``."""
    # Cheap deterministic probe first: a full 16.7M colour scan is only ever a
    # theoretical fallback, but it must stay deterministic for byte-identical
    # output across runs.
    for step in range(256):
        candidate = ((step * 97) % 256, (step * 53) % 256, (step * 29) % 256)
        if candidate not in used:
            return candidate
    for red in range(256):
        for green in range(256):
            for blue in range(256):
                candidate = (red, green, blue)
                if candidate not in used:
                    return candidate
    raise RuntimeError("the GIF palette has no free colour left")  # pragma: no cover


def _closest_index(parsed: dict[int, tuple[int, int, int]]) -> int:
    """Return the used palette index whose colour is closest to index 0's."""
    original = parsed[0]
    best_index = -1
    best_distance = -1
    for index in sorted(parsed):
        if index == 0:
            continue
        color = parsed[index]
        distance = sum(abs(a - b) for a, b in zip(original, color, strict=True))
        if best_index < 0 or distance < best_distance:
            best_index, best_distance = index, distance
    if best_index < 0:  # pragma: no cover - a palette always has more than one entry
        raise RuntimeError("the GIF palette only holds the transparent colour")
    return best_index


def to_transparent_frame(image: PILImage, alpha_threshold: int = 0) -> PILImage:
    """Convert one ``RGBA`` frame into a ``P`` frame with index ``0`` transparent.

    Partial alpha (``0 < alpha <= alpha_threshold`` inclusive of the threshold)
    is discarded: a pixel is either fully kept or fully transparent. GIF cannot
    express anything in between.

    Args:
        image: The frame to convert, in ``RGBA`` mode.
        alpha_threshold: Alpha at or below this value becomes transparent.

    Returns:
        A palette mode frame whose ``info`` marks index ``0`` as transparent.
    """
    rgba = image if image.mode == "RGBA" else image.convert("RGBA")
    # `convert("P")` would snap every colour onto Pillow's fixed 216 colour WEB
    # palette; an adaptive palette keeps photos and gradients recognisable.
    palette_image = rgba.convert("RGB").quantize(
        colors=_MAX_COLOURS,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.FLOYDSTEINBERG,
    )
    data = bytearray(palette_image.tobytes())

    alpha_bytes = rgba.getchannel("A").tobytes()
    transparent = {index for index, value in enumerate(alpha_bytes) if value <= alpha_threshold}

    palette = palette_image.getpalette() or []
    used = {value for index, value in enumerate(data) if index not in transparent}
    parsed = {
        index: (palette[index * 3], palette[index * 3 + 1], palette[index * 3 + 2])
        for index in used
    }

    # Index 0 has to host the transparent colour, so any real colour sitting
    # there is moved to a free slot first.
    replacements_from: list[int] = []
    replacements_to: list[int] = []
    if 0 in used:
        free_slots = sorted(_PALETTE_SLOTS - used)
        new_index = free_slots[0] if free_slots else _closest_index(parsed)
        used.add(new_index)
        replacements_from.append(0)
        replacements_to.append(new_index)
        parsed[new_index] = parsed[0]
        parsed.pop(0, None)

    sentinel = _pick_unused_color(frozenset(parsed.values()))
    parsed[0] = sentinel

    if replacements_from:
        table = bytearray.maketrans(bytes(replacements_from), bytes(replacements_to))
        data = bytearray(data.translate(table))
    for index in transparent:
        data[index] = 0

    palette_image.frombytes(bytes(data))
    palette_image.putpalette(list(chain.from_iterable(parsed.get(i, sentinel) for i in range(256))))
    palette_image.info["transparency"] = 0
    palette_image.info["background"] = 0
    return palette_image


def save_transparent_gif(
    frames: Sequence[PILImage],
    durations: int | Sequence[int],
    save_file: SaveTarget,
    *,
    loop: int = 0,
) -> None:
    """Write ``frames`` to ``save_file`` as one transparent, looping GIF.

    Args:
        frames: ``RGBA`` frames, in playback order.
        durations: Frame delay in milliseconds, either one value for every frame
            or one value per frame.
        save_file: Filename, path or binary file object to write to.
        loop: ``0`` loops forever, ``n`` plays the animation ``n`` extra times.
    """
    if not frames:
        raise ValueError("at least one frame is required")

    palette_frames = [to_transparent_frame(frame) for frame in frames]
    palette_frames[0].save(
        save_file,
        format="GIF",
        save_all=True,
        optimize=False,
        append_images=palette_frames[1:],
        duration=durations,
        # 3 = restore to previous: each frame then shows exactly the pixels that
        # were rendered for it. See the module docstring for why not 2.
        disposal=3,
        loop=loop,
    )
