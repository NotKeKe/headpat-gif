"""The returned object: buffer behaviour, metadata and saving."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from petpet_gif import PetPetGif, petpet
from support import frame_delays


def test_name_defaults_to_petpet_gif(subject: Image.Image) -> None:
    assert petpet(subject, duration=0.5).name == "petpet.gif"


def test_behaves_like_a_readable_seekable_buffer(subject: Image.Image) -> None:
    # This is exactly what discord.File checks before accepting a file object.
    gif = petpet(subject, duration=0.5)

    assert gif.seekable()
    assert gif.readable()
    assert gif.tell() == 0
    assert gif.read(3) == b"GIF"
    assert gif.tell() == 3
    gif.seek(0)
    assert gif.read(6) == b"GIF89a"


def test_to_bytes_does_not_move_the_read_position(subject: Image.Image) -> None:
    gif = petpet(subject, duration=0.5)
    gif.read(10)

    assert gif.to_bytes() == gif.getvalue()
    assert gif.tell() == 10


def test_metadata_describes_the_encoded_gif(subject: Image.Image) -> None:
    gif = petpet(subject, duration=1.0)
    image = Image.open(io.BytesIO(gif.to_bytes()))

    assert gif.size == image.size
    assert gif.n_frames == getattr(image, "n_frames", 1)
    assert gif.duration_ms == sum(frame_delays(gif.to_bytes()))
    assert gif.cycle_ms <= gif.duration_ms


def test_save_writes_the_file_and_creates_parents(work_dir: Path, subject: Image.Image) -> None:
    gif = petpet(subject, duration=0.5)
    target = gif.save(work_dir / "nested" / "deeper" / "pet.gif")

    assert target == work_dir / "nested" / "deeper" / "pet.gif"
    assert target.read_bytes() == gif.to_bytes()


def test_save_accepts_a_plain_string(work_dir: Path, subject: Image.Image) -> None:
    target = petpet(subject, duration=0.5).save(str(work_dir / "pet.gif"))

    assert isinstance(target, Path)
    assert target.exists()


def test_repr_names_the_object(subject: Image.Image) -> None:
    text = repr(petpet(subject, duration=0.5))

    assert text.startswith("PetPetGif(")
    assert "petpet.gif" in text


def test_discord_py_can_rewrite_close_without_losing_the_bytes(subject: Image.Image) -> None:
    # discord.File replaces `fp.close` with a no-op; the class must not care.
    gif: PetPetGif = petpet(subject, duration=0.5)
    setattr(gif, "close", lambda: None)  # noqa: B010 - mirrors what discord.py does

    assert gif.to_bytes()[:6] == b"GIF89a"
