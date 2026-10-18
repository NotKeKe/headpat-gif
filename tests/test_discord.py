"""The interaction the whole library is shaped around: handing the result to discord.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from petpet_gif import PetPetGif, petpet

discord = pytest.importorskip("discord")


def test_discord_file_accepts_the_result_without_conversion(subject: Image.Image) -> None:
    gif = petpet(subject, duration=0.5)

    file = discord.File(gif)

    assert isinstance(gif, PetPetGif)
    assert file.filename == "petpet.gif"
    assert file.fp is gif
    assert file.fp.read(6) == b"GIF89a"


def test_the_filename_can_be_overridden_per_call(subject: Image.Image) -> None:
    assert discord.File(petpet(subject, duration=0.2, name="pet.gif")).filename == "pet.gif"


def test_an_explicit_filename_still_wins(subject: Image.Image) -> None:
    file = discord.File(petpet(subject, duration=0.2), filename="custom.gif")

    assert file.filename == "custom.gif"


def test_the_payload_survives_discord_closing_the_file(subject: Image.Image) -> None:
    gif = petpet(subject, duration=0.2)
    file = discord.File(gif)
    file.close()

    assert gif.to_bytes()[:6] == b"GIF89a"


def test_saving_after_being_wrapped_still_works(work_dir: Path, subject: Image.Image) -> None:
    gif = petpet(subject, duration=0.2)
    discord.File(gif)

    assert gif.save(work_dir / "pet.gif").exists()


def test_a_new_object_is_needed_per_send(subject: Image.Image) -> None:
    # discord.File is documented as single use, so make that workflow explicit.
    gif = petpet(subject, duration=0.2)
    payload = gif.to_bytes()
    reborn = PetPetGif(
        payload,
        size=gif.size,
        n_frames=gif.n_frames,
        duration_ms=gif.duration_ms,
        cycle_ms=gif.cycle_ms,
    )

    first = discord.File(gif)
    second = discord.File(reborn)

    assert first.filename == second.filename == "petpet.gif"
    assert first.fp.read(6) == second.fp.read(6) == b"GIF89a"
