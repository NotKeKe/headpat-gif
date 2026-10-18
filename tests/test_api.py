"""The public entry points: accepted inputs, validation and defaults."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from headpat_gif import PetPetGif, petpet, save
from support import PNG_BYTES, OneShotStream, as_source, frame_delays


def test_returns_a_headpat_gif(subject: Image.Image) -> None:
    result = petpet(subject)

    assert isinstance(result, PetPetGif)
    assert isinstance(result, io.BytesIO)
    assert result.getvalue()[:6] == b"GIF89a"


def test_uses_default_overlay_when_none_given(subject: Image.Image) -> None:
    # The bundled hand is 5 frames x 70ms, so one cycle is 350ms.
    result = petpet(subject)

    assert result.cycle_ms == 350


def test_accepts_every_documented_source(work_dir: Path, subject: Image.Image) -> None:
    path = work_dir / "subject.png"
    subject.save(path)
    with path.open("rb") as handle:
        sources = [
            path,
            str(path),
            subject,
            path.read_bytes(),
            bytearray(path.read_bytes()),
            handle,
            io.BytesIO(path.read_bytes()),
        ]

        for source in sources:
            assert isinstance(petpet(source, duration=0.2), PetPetGif)


def test_overlay_accepts_gif_still_and_path(
    work_dir: Path, subject: Image.Image, overlay_gif: bytes, still_overlay: Image.Image
) -> None:
    path = work_dir / "overlay.gif"
    path.write_bytes(overlay_gif)

    assert petpet(subject, overlay_gif).cycle_ms == 150
    assert petpet(subject, path).cycle_ms == 150
    assert petpet(subject, still_overlay, static_overlay_ms=300).cycle_ms == 300


def test_survives_a_non_seekable_stream() -> None:
    assert isinstance(petpet(OneShotStream(PNG_BYTES), duration=0.2), PetPetGif)


def test_rejects_unsupported_types(subject: Image.Image) -> None:
    with pytest.raises(TypeError, match="image must be"):
        petpet(as_source(1234))

    with pytest.raises(TypeError, match="overlay must be"):
        petpet(subject, as_source(1234))


def test_missing_file_is_reported_clearly(work_dir: Path) -> None:
    with pytest.raises(FileNotFoundError, match="no such file"):
        petpet(work_dir / "nope.png")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"duration": 0}, "duration"),
        ({"duration": -1.0}, "duration"),
        ({"speed": 0}, "speed"),
        ({"fps": 9}, "fps"),
        ({"fps": 51}, "fps"),
        ({"max_size": 4}, "max_size"),
        ({"image_scale": 0}, "image_scale"),
        ({"squash": -0.1}, "squash"),
        ({"overlay_scale": 0}, "overlay_scale"),
        ({"static_overlay_ms": 10}, "static_overlay_ms"),
    ],
)
def test_rejects_out_of_range_arguments(
    subject: Image.Image, kwargs: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        petpet(subject, **kwargs)


def test_rejects_a_bad_background_colour(subject: Image.Image) -> None:
    with pytest.raises(ValueError, match="background"):
        petpet(subject, background="not-a-colour")


def test_background_flattens_the_canvas(subject: Image.Image, invisible: Image.Image) -> None:
    gif = petpet(subject, invisible, duration=0.2, background="white")
    image = Image.open(io.BytesIO(gif.to_bytes())).convert("RGBA")

    assert image.getpixel((0, 0)) == (255, 255, 255, 255)


def test_name_reaches_the_attachment(subject: Image.Image) -> None:
    assert petpet(subject, duration=0.2, name="pet.gif").name == "pet.gif"
    assert petpet(subject, duration=0.2).name == "petpet.gif"


def test_duration_defaults_to_exactly_one_cycle(subject: Image.Image, overlay_gif: bytes) -> None:
    result = petpet(subject, overlay_gif)

    assert result.duration_ms == result.cycle_ms == 150


def test_each_call_returns_a_fresh_buffer(subject: Image.Image) -> None:
    first = petpet(subject, duration=0.2)
    second = petpet(subject, duration=0.2)

    assert first is not second
    assert first.tell() == 0
    assert first.read(6) == b"GIF89a"
    assert second.read(6) == b"GIF89a"


def test_save_helper_writes_a_decodable_file(work_dir: Path, subject: Image.Image) -> None:
    gif = petpet(subject, duration=0.5)
    target = save(gif, work_dir / "out" / "pet.gif")

    assert target == Path(work_dir / "out" / "pet.gif")
    assert target.stat().st_size == len(gif.to_bytes())
    assert sum(frame_delays(target)) == 500
