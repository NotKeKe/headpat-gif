"""What the rendered frames actually look like."""

from __future__ import annotations

from typing import cast

import pytest
from PIL import Image

from headpat_gif import OverlayAnchor, petpet
from support import frame_alpha_boxes

CANVAS = 100
BOTTOM = 92  # BOTTOM_ANCHOR (0.92) of a 100px canvas


def _opaque(size: tuple[int, int] = (CANVAS, CANVAS)) -> Image.Image:
    return Image.new("RGBA", size, (200, 60, 60, 255))


def _boxes(**kwargs) -> list[tuple[int, int, int, int] | None]:
    kwargs.setdefault("duration", 1.0)
    kwargs.setdefault("max_size", CANVAS)
    kwargs.setdefault("static_overlay_ms", 500)
    gif = petpet(_opaque(), kwargs.pop("overlay"), **kwargs)
    return frame_alpha_boxes(gif.to_bytes())


def test_the_subject_never_moves_off_its_baseline(invisible: Image.Image) -> None:
    boxes = _boxes(overlay=invisible)

    bottoms = {box[3] for box in boxes if box}
    assert bottoms == {BOTTOM}


def test_the_subject_gets_wider_and_shorter_then_returns(invisible: Image.Image) -> None:
    boxes = [box for box in _boxes(overlay=invisible, duration=1.0, loop=False) if box]
    widths = [right - left for left, _, right, _ in boxes]
    heights = [bottom - top for _, top, _, bottom in boxes]

    assert max(widths) > min(widths)
    assert min(heights) < max(heights)
    # The widest pose is the shortest pose: both peak in the middle of the cycle.
    assert widths.index(max(widths)) == heights.index(min(heights))
    # ...and the last frame is back to the resting shape.
    assert (widths[-1], heights[-1]) == (widths[0], heights[0])
    assert widths[0] == heights[0] == 80  # image_scale 0.8 of a 100px canvas


def test_the_squash_peaks_in_the_middle_of_the_cycle(invisible: Image.Image) -> None:
    boxes = [box for box in _boxes(overlay=invisible) if box]
    heights = [bottom - top for _, top, _, bottom in boxes]
    cycle = heights[:13]  # 12 sampled frames of a 500ms cycle plus its last step

    assert cycle.index(min(cycle)) == len(cycle) // 2


def test_squash_zero_leaves_the_subject_completely_still(invisible: Image.Image) -> None:
    boxes = _boxes(overlay=invisible, squash=0.0)

    assert len(set(boxes)) == 1


def test_the_overlay_is_gone_once_the_cycle_has_played() -> None:
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    gif = petpet(
        transparent, square, duration=1.0, static_overlay_ms=200, max_size=60, loop=False
    )
    boxes = frame_alpha_boxes(gif.to_bytes())

    assert boxes[0] is not None  # the square is on screen during the cycle
    assert boxes[-1] is None  # ...and gone while the subject rests


def test_the_overlay_covers_the_whole_canvas_by_default() -> None:
    # The classic pet-pet look: the hand is authored for the canvas, so it fills
    # it and the subject squashes underneath.
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    gif = petpet(transparent, square, duration=0.2, static_overlay_ms=200, max_size=60)

    assert frame_alpha_boxes(gif.to_bytes())[0] == (0, 0, 60, 60)


def test_the_overlay_sits_at_the_top_by_default() -> None:
    box = _sprite_box("top")

    assert box == (15, 0, 45, 30)  # flush with the top edge, horizontally centred


def test_the_offset_moves_the_overlay_and_grows_the_canvas() -> None:
    # Only the top half of this overlay is opaque, so a vertical offset shows up
    # as the opaque band sliding down the canvas.
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    overlay.paste(Image.new("RGBA", (20, 10), (0, 200, 0, 255)), (0, 0))

    def render(offset: tuple[float, float]) -> tuple[tuple[int, int], tuple[int, int, int, int]]:
        gif = petpet(
            transparent,
            overlay,
            duration=0.2,
            static_overlay_ms=200,
            max_size=60,
            overlay_offset=offset,
        )
        box = frame_alpha_boxes(gif.to_bytes())[0]
        assert box is not None
        return gif.size, box

    rest_size, rest_box = render((0.0, 0.0))
    down_size, down_box = render((0.0, 0.5))
    up_size, up_box = render((0.0, -0.5))

    # Nothing moves and nothing grows without an offset.
    assert rest_size == (60, 60)
    assert rest_box[:3] == (0, 0, 60)
    assert rest_box[3] < 35  # the opaque band sits across the top

    # Pushing the overlay down grows the canvas downwards...
    assert down_size == (60, 90)
    assert down_box[1] >= 30

    # ...and pushing it up grows the canvas upwards, without slicing the
    # overlay: the band still starts at the very top of the picture.
    assert up_size == (60, 90)
    assert up_box[:3] == (0, 0, 60)
    assert up_box[3] == rest_box[3]


def test_a_horizontal_offset_grows_the_canvas_sideways() -> None:
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))

    def size(offset: tuple[float, float]) -> tuple[int, int]:
        gif = petpet(
            transparent,
            square,
            duration=0.2,
            static_overlay_ms=200,
            max_size=60,
            overlay_offset=offset,
        )
        return gif.size

    assert size((0.0, 0.0)) == (60, 60)
    assert size((0.5, 0.0)) == (90, 60)
    assert size((-0.5, 0.0)) == (90, 60)


def test_the_subject_keeps_its_size_when_the_canvas_grows() -> None:
    subject = Image.new("RGBA", (60, 60), (200, 60, 60, 255))
    # A transparent overlay still claims its own rectangle, so the canvas grows,
    # while the alpha box below measures the subject alone.
    invisible = Image.new("RGBA", (20, 20), (0, 0, 0, 0))

    plain = petpet(subject, invisible, duration=0.2, max_size=60, loop=False)
    taller = petpet(
        subject,
        invisible,
        duration=0.2,
        max_size=60,
        loop=False,
        overlay_offset=(0.0, 0.5),
    )
    plain_box = frame_alpha_boxes(plain.to_bytes())[0]
    taller_box = frame_alpha_boxes(taller.to_bytes())[0]

    assert plain_box is not None and taller_box is not None
    assert taller.size == (60, 90)
    # Same subject, same size: only the empty room below it changed.
    assert taller_box[3] - taller_box[1] == plain_box[3] - plain_box[1]
    assert taller_box[1] == plain_box[1]


def test_the_overlay_anchor_can_be_moved() -> None:
    assert _sprite_box("center") == (15, 15, 45, 45)
    assert _sprite_box("bottom") == (15, 30, 45, 60)


def test_the_overlay_offset_nudges_the_anchored_position() -> None:
    assert _sprite_box("top", offset=(0.0, 0.25)) == (15, 15, 45, 45)
    assert _sprite_box("top", offset=(-0.25, 0.0))[0] < 15


def test_an_unknown_anchor_is_rejected() -> None:
    subject = Image.new("RGBA", (10, 10), (0, 0, 0, 0))

    with pytest.raises(ValueError, match="overlay_anchor"):
        petpet(subject, duration=0.2, overlay_anchor=cast("OverlayAnchor", "middle"))


def _sprite_box(
    anchor: OverlayAnchor, offset: tuple[float, float] = (0.0, 0.0)
) -> tuple[int, ...]:
    """Alpha box of a half-size square overlay placed with ``anchor`` on a 60px canvas."""
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    gif = petpet(
        transparent,
        square,
        duration=0.2,
        static_overlay_ms=200,
        max_size=60,
        overlay_scale=0.5,
        overlay_anchor=anchor,
        overlay_offset=offset,
    )
    box = frame_alpha_boxes(gif.to_bytes())[0]

    assert box is not None
    return box


def test_the_canvas_keeps_the_subject_aspect_ratio(subject: Image.Image) -> None:
    assert petpet(subject, duration=0.2).size == (256, 192)
    assert petpet(subject, duration=0.2, max_size=64).size == (64, 48)


def test_a_wide_subject_gets_a_wide_canvas() -> None:
    wide = Image.new("RGBA", (400, 50), (10, 10, 10, 255))

    assert petpet(wide, duration=0.2, max_size=200).size == (200, 25)


def test_image_scale_shrinks_the_subject(invisible: Image.Image) -> None:
    boxes = [box for box in _boxes(overlay=invisible, image_scale=0.5) if box]

    left, top, right, bottom = boxes[0]
    assert (right - left, bottom - top) == (50, 50)
    assert bottom == BOTTOM
