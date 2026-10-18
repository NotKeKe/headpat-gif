"""The in-memory GIF object handed back to callers."""

from __future__ import annotations

import io
import os
from pathlib import Path

__all__ = ["PetPetGif"]


class PetPetGif(io.BytesIO):
    """A finished pet-pet GIF held in memory.

    This is a plain :class:`io.BytesIO` subclass, which is exactly what
    ``discord.File`` accepts::

        await channel.send(file=discord.File(petpet("pet.png")))

    ``discord.File`` validates ``seekable()``/``readable()`` and takes the
    attachment name from the ``name`` attribute, so the object can be sent
    without any conversion step.

    Note:
        A ``discord.File`` (and therefore the file object inside it) is
        single-use. Build a fresh :class:`PetPetGif` for every send, or keep the
        bytes with :meth:`to_bytes` and wrap them in a new
        :class:`io.BytesIO`.
    """

    def __init__(
        self,
        data: bytes,
        *,
        name: str = "petpet.gif",
        size: tuple[int, int],
        n_frames: int,
        duration_ms: int,
        cycle_ms: int,
    ) -> None:
        super().__init__(data)
        self.name = name
        self.size = size
        self.n_frames = n_frames
        self.duration_ms = duration_ms
        self.cycle_ms = cycle_ms

    def to_bytes(self) -> bytes:
        """Return a copy of the encoded GIF without moving the read position."""
        return self.getvalue()

    def save(self, path: str | os.PathLike[str]) -> Path:
        """Write the GIF to ``path``, creating parent directories as needed.

        Returns:
            The written path.
        """
        target = Path(path)
        if target.parent != Path():
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.getvalue())
        return target

    def __repr__(self) -> str:
        return (
            f"PetPetGif(name={self.name!r}, size={self.size!r}, "
            f"n_frames={self.n_frames}, duration_ms={self.duration_ms})"
        )
