"""GIF transparency: the thing most pet-pet implementations get wrong."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from petpet_gif import petpet
from support import count_colour, frame_rgba, frame_windows, gif_frames, pixel

CANVAS = 100
RED = b"\xff\x00\x00\xff"


def _subject_with_a_hole(size: int = CANVAS) -> Image.Image:
    image = Image.new("RGBA", (size, size), (30, 140, 220, 255))
    hole = Image.new("RGBA", (size // 5, size // 5), (0, 0, 0, 0))
    image.paste(hole, (size * 2 // 5, size * 2 // 5))
    return image


def test_index_zero_is_the_transparent_index(subject: Image.Image) -> None:
    image = Image.open(io.BytesIO(petpet(subject, duration=0.5).to_bytes()))

    assert image.info["transparency"] == 0
    assert image.info["background"] == 0


def test_every_frame_restores_the_canvas_before_the_next_one(subject: Image.Image) -> None:
    # Disposal 3 ("restore to previous") is what keeps a moving overlay from
    # leaving a trail. Disposal 2 would restore the *background colour* instead,
    # which some decoders paint opaque black and others simply ignore - see the
    # module docstring of petpet_gif._palette.
    frames = gif_frames(petpet(subject, duration=0.5).to_bytes())

    assert frames
    assert {frame.disposal for frame in frames} == {3}
    assert {frame.transparent_index for frame in frames} == {0}
    assert all(frame.width and frame.height for frame in frames)


def test_a_leaving_overlay_leaves_nothing_behind() -> None:
    # The regression this guards: the frame *after* the overlay's last visible
    # frame must be fully transparent again, not a stale copy of it.
    transparent = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    square = Image.new("RGBA", (20, 20), (0, 200, 0, 255))
    gif = petpet(
        transparent, square, duration=1.0, static_overlay_ms=200, max_size=60, loop=False
    )

    windows = frame_windows(gif.to_bytes())
    during = [frame for start, _, frame in windows if start < 200]
    after = [frame for start, _, frame in windows if start >= 200]

    assert during and all(count_colour(frame, (0, 200, 0, 255)) > 0 for frame in during)
    assert after and all(frame.getchannel("A").getbbox() is None for frame in after)


def test_pixels_outside_the_subject_stay_transparent(subject: Image.Image) -> None:
    image = Image.open(io.BytesIO(petpet(subject, duration=0.5).to_bytes()))
    for index in range(getattr(image, "n_frames", 1)):
        image.seek(index)
        assert pixel(image.convert("RGBA"), (0, 0))[3] == 0


def test_transparent_pixels_use_index_zero_in_the_encoded_palette(invisible: Image.Image) -> None:
    blank = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    image = Image.open(io.BytesIO(petpet(blank, invisible, duration=0.2).to_bytes()))

    # A fully transparent canvas: every palette index in frame 0 must be 0.
    assert set(image.tobytes()) == {0}


def test_a_hole_inside_the_subject_survives_the_round_trip(invisible: Image.Image) -> None:
    # Canvas is 100x100 and the subject sits at (10, 12)-(90, 92) when at rest,
    # so the hole lands around (42, 44)-(58, 60).
    gif = petpet(_subject_with_a_hole(), invisible, duration=0.5, max_size=CANVAS)
    frame = frame_rgba(gif.to_bytes(), 0)
    head = pixel(frame, (CANVAS // 2, CANVAS // 2))
    body = pixel(frame, (20, 20))

    assert head[3] == 0  # the hole
    assert body[3] == 255  # the body
    assert body[:3] != (0, 0, 0)  # and the body did not lose its colour


def test_transparent_areas_are_not_baked_in_as_black(subject: Image.Image) -> None:
    # The classic failure mode is transparent pixels coming out opaque black.
    gif = petpet(subject, duration=0.5)
    width, height = gif.size
    frame = frame_rgba(gif.to_bytes(), 0)

    for point in [(0, 0), (5, 5), (width - 1, 0), (width - 1, height - 1)]:
        assert pixel(frame, point)[3] == 0, f"{point} came out opaque"


def test_flattening_onto_a_colour_is_opaque(subject: Image.Image, invisible: Image.Image) -> None:
    gif = petpet(subject, invisible, duration=0.5, background=(255, 255, 255))
    frame = frame_rgba(gif.to_bytes(), 0)

    assert pixel(frame, (0, 0)) == (255, 255, 255, 255)


def test_output_is_byte_for_byte_deterministic(subject: Image.Image) -> None:
    first = petpet(subject, duration=1.0, speed=1.5).to_bytes()
    second = petpet(subject, duration=1.0, speed=1.5).to_bytes()

    assert first == second


def test_a_transparent_overlay_keeps_the_subject_untouched() -> None:
    green = (12, 200, 40, 255)
    subject = Image.new("RGBA", (CANVAS, CANVAS), green)
    invisible = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
    gif = petpet(subject, invisible, duration=0.5, max_size=CANVAS, squash=0.0)
    frame = frame_rgba(gif.to_bytes(), 0)

    # The subject's own colour must come through untouched (no overlay tint).
    assert pixel(frame, (CANVAS // 2, CANVAS // 2)) == green


def test_an_opaque_overlay_replaces_the_pixels_it_covers() -> None:
    subject = Image.new("RGBA", (CANVAS, CANVAS), (255, 255, 255, 255))
    overlay = Image.new("RGBA", (CANVAS, CANVAS), (255, 0, 0, 255))
    gif = petpet(subject, overlay, duration=0.5, max_size=CANVAS, overlay_scale=1.0, squash=0.0)
    frame = frame_rgba(gif.to_bytes(), 0)

    assert frame.tobytes().count(RED) > CANVAS * CANVAS // 4


def test_saved_file_is_the_same_bytes(work_dir: Path, subject: Image.Image) -> None:
    gif = petpet(subject, duration=0.5)
    target = gif.save(work_dir / "pet.gif")

    assert target.read_bytes() == gif.to_bytes()
