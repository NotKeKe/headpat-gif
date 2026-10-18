"""The classic look: a big hand covers the picture and squashes the subject.

This is what ``petpet()`` does out of the box - the overlay is authored for the
canvas, so it covers the whole picture and the subject squashes underneath it.

    uv run python examples/classic_smiley.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from headpat_gif import petpet, save

OUT = Path(__file__).parent / "out"
SIZE = 240


def smiley(size: int = SIZE) -> Image.Image:
    """A grinning face on a transparent canvas."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 30, size - 20, size - 10), fill=(250, 224, 132, 255))
    draw.ellipse((80, 90, 100, 120), fill=(60, 50, 40, 255))
    draw.ellipse((140, 90, 160, 120), fill=(60, 50, 40, 255))
    draw.arc((85, 110, 155, 175), start=20, end=160, fill=(60, 50, 40, 255), width=7)
    return image


def main() -> None:
    face = smiley()
    face.save(OUT / "smiley-input.png")

    # Default: the hand covers the whole picture.
    save(petpet(face, duration=1.0), OUT / "smiley.gif")

    # Move the hand around: fractions of the canvas, negative y is up. The
    # canvas grows to fit, so the hand is never sliced off - only the picture
    # gets taller.
    save(petpet(face, duration=1.0, overlay_offset=(0.0, -0.3)), OUT / "smiley-hand-higher.gif")
    save(petpet(face, duration=1.0, overlay_offset=(0.0, 0.2)), OUT / "smiley-hand-lower.gif")
    save(petpet(face, duration=1.0, overlay_offset=(0.15, 0.0)), OUT / "smiley-hand-right.gif")

    # Shrink the overlay when you want a small hand resting on the head instead;
    # overlay_anchor then decides where that smaller hand sits.
    save(
        petpet(face, duration=1.5, overlay_scale=0.4, overlay_anchor="top"),
        OUT / "smiley-small-hand.gif",
    )

    print(f"wrote the classic demo to {OUT}")


if __name__ == "__main__":
    main()
