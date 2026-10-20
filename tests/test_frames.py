"""What the rendered frames actually look like."""

from __future__ import annotations

import pytest
from PIL import Image

from headpat_gif import petpet
from headpat_gif._compose import overlay_sprite_size
from support import frame_alpha_boxes, frame_rgba, pixel

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


def test_the_overlay_covers_the_canvas_at_full_scale() -> None:
    # overlay_scale=1.0 is the cover fit itself: the hand is as big as the canvas
    # and only its overflow past the far edges is cropped.
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    gif = petpet(
        transparent, square, duration=0.2, static_overlay_ms=200, max_size=60, overlay_scale=1.0
    )

    assert frame_alpha_boxes(gif.to_bytes())[0] == (0, 0, 60, 60)


def test_the_overlay_is_scaled_uniformly_whatever_the_canvas_shape() -> None:
    # A 1:2 hand must stay 1:2 - on a wide canvas, a tall one and a square one.
    frame = Image.new("RGBA", (30, 60))

    for box in [(256, 64), (64, 256), (100, 100), (400, 100)]:
        width, height = overlay_sprite_size(frame, box, None)
        assert abs(width / height - 0.5) < 0.02, box
        # ...and the cover fit never leaves a gap along either axis.
        assert width >= box[0] - 1
        assert height >= box[1] - 1


def test_an_overlay_bigger_than_the_canvas_is_cropped_not_shrunk() -> None:
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    wide = Image.new("RGBA", (400, 50), (10, 10, 10, 255))
    tall = Image.new("RGBA", (50, 400), (10, 10, 10, 255))

    # A 200x200 overlay on a 200x25 canvas: it starts in the canvas' own corner
    # and runs off the right and bottom edges, which are cropped.
    for subject in (wide, tall):
        gif = petpet(subject, square, duration=0.2, max_size=200, overlay_scale=1.0)
        box = frame_alpha_boxes(gif.to_bytes())[0]

        assert box is not None
        assert gif.size in {(200, 25), (25, 200)}
        assert box == (0, 0, gif.size[0], gif.size[1])


def test_the_overlay_reaches_the_canvas_edges_by_default() -> None:
    # 60px canvas: a 20x20 overlay covers it (factor 3), so the default 0.8 draws
    # it at 48x48 from the very corner. Nothing is left transparent on the left.
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    gif = petpet(transparent, square, duration=0.2, static_overlay_ms=200, max_size=60)
    frame = frame_rgba(gif.to_bytes(), 0)

    assert frame_alpha_boxes(gif.to_bytes())[0] == (0, 0, 48, 48)
    assert pixel(frame, (0, 0))[3] == 255  # the hand touches the top-left corner


def test_the_overlay_position_places_the_hand() -> None:
    # A quarter-size overlay on a 60px canvas: its top-left corner lands on the
    # fraction of the canvas asked for.
    assert _sprite_box((0.0, 0.0)) == (0, 0, 15, 15)  # the canvas' corner
    assert _sprite_box((0.5, 0.5)) == (30, 30, 45, 45)  # its middle
    assert _sprite_box((0.25, 0.75)) == (15, 45, 30, 60)


def test_a_padded_overlay_still_touches_the_corner_it_is_given() -> None:
    # The bundled hand has empty rows above it: aligning the frame instead of the
    # pixels would leave a gap, so the visible corner is what gets pinned.
    padded = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    padded.paste(Image.new("RGBA", (10, 10), (0, 200, 0, 255)), (5, 5))
    gif = petpet(
        Image.new("RGBA", (60, 60), (0, 0, 0, 0)),
        padded,
        duration=0.2,
        static_overlay_ms=200,
        max_size=60,
        overlay_scale=0.25,
        overlay_position=(0.5, 0.5),
    )
    box = frame_alpha_boxes(gif.to_bytes())[0]

    assert box is not None
    assert abs(box[0] - 30) <= 2  # the middle of the canvas, not 4px right of it
    assert abs(box[1] - 30) <= 2


def test_the_overlay_offset_nudges_the_positioned_hand() -> None:
    # Pushed left by a quarter of the canvas: the object grows to keep it whole.
    assert _sprite_box((0.0, 0.0), offset=(-0.25, 0.25), size=(75, 60)) == (0, 15, 15, 30)


def test_a_non_finite_overlay_position_is_rejected() -> None:
    subject = Image.new("RGBA", (10, 10), (0, 0, 0, 0))

    with pytest.raises(ValueError, match="overlay_position"):
        petpet(subject, duration=0.2, overlay_position=(float("nan"), 0.0))


def _sprite_box(
    position: tuple[float, float],
    offset: tuple[float, float] = (0.0, 0.0),
    size: tuple[int, int] = (60, 60),
    scale: float = 0.25,
) -> tuple[int, ...]:
    """Alpha box of a square overlay pinned to ``position`` on the picture."""
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    gif = petpet(
        transparent,
        square,
        duration=0.2,
        static_overlay_ms=200,
        max_size=60,
        overlay_scale=scale,
        overlay_position=position,
        overlay_offset=offset,
    )
    box = frame_alpha_boxes(gif.to_bytes())[0]

    assert gif.size == size
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
