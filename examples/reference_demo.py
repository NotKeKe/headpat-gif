"""Reproduce the reference animation: a goat gets patted on the head.

The goat is cropped out of the reference clip that this library was modelled on
(``docs/reference/minecraft-goat-petting.webp``), so the result can be compared
side by side with what the project set out to make.

    uv run python examples/reference_demo.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from petpet_gif import petpet, save

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "reference" / "minecraft-goat-petting.webp"
OUT = Path(__file__).parent / "out"

#: The goat in the first frame of the reference clip.
GOAT_BOX = (350, 48, 532, 212)


def main() -> None:
    clip = Image.open(SOURCE)
    clip.seek(0)
    goat = clip.convert("RGBA").crop(GOAT_BOX)
    goat.save(OUT / "goat-input.png")

    save(petpet(goat, duration=2.0), OUT / "10-goat-petted.gif")
    save(
        petpet(goat, duration=2.0, loop=False),
        OUT / "11-goat-patted-once.gif",
    )
    save(petpet(goat, duration=1.0, speed=1.5), OUT / "12-goat-faster.gif")
    print(f"wrote the reference demo to {OUT}")


if __name__ == "__main__":
    main()
