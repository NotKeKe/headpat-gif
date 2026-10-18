"""petpet-gif - make a "pet-pet" GIF from any image.

The subject is squashed and sprung back while a hand pats it on the head, and
the result comes back as an object you can hand straight to ``discord.File``::

    from petpet_gif import petpet

    gif = petpet("pet.png", duration=2.0)
    gif.save("pet.gif")

    # in a discord.py command, without touching the disk:
    await channel.send(file=discord.File(petpet("pet.png")))

Everything is customisable: pass your own animated overlay, change how long the
GIF runs and how fast the pat plays.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from ._api import petpet, save
from ._assets import DEFAULT_OVERLAY_NAME
from ._compose import ANCHORS, MIN_DELAY_MS, OverlayAnchor
from ._result import PetPetGif
from ._sources import ImageSource

__all__ = [
    "ANCHORS",
    "DEFAULT_OVERLAY_NAME",
    "MIN_DELAY_MS",
    "ImageSource",
    "OverlayAnchor",
    "PetPetGif",
    "petpet",
    "save",
]

try:
    __version__ = version("petpet-gif")
except PackageNotFoundError:  # pragma: no cover - raw checkout without an install
    __version__ = "0.0.0"
