"""Render one GIF per feature so the output can be inspected by eye.

Run it with ``uv run python examples/basic.py``; files land in
``examples/out/``.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from headpat_gif import petpet, save

OUT = Path(__file__).parent / "out"


def subject(size: tuple[int, int] = (240, 180)) -> Image.Image:
    """A simple stand-in for a pet: a body with a head, on a transparent canvas."""
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    image.paste(Image.new("RGBA", (150, 90), (232, 220, 196, 255)), (45, 80))
    image.paste(Image.new("RGBA", (70, 60), (232, 220, 196, 255)), (60, 40))
    image.paste(Image.new("RGBA", (16, 16), (40, 40, 40, 255)), (70, 55))
    return image


def main() -> None:
    pet = subject()

    save(petpet(pet), OUT / "01-one-cycle.gif")
    save(petpet(pet, duration=2.0), OUT / "02-two-seconds.gif")
    save(petpet(pet, duration=2.0, speed=2.0), OUT / "03-double-speed.gif")
    save(petpet(pet, duration=2.0, loop=False), OUT / "04-pat-once-then-rest.gif")
    save(petpet(pet, duration=1.5, squash=1.6), OUT / "05-hard-squash.gif")
    save(petpet(pet, duration=1.5, squash=0.0), OUT / "06-no-squash.gif")
    save(petpet(pet, duration=1.5, background="white"), OUT / "07-white-background.gif")
    save(
        petpet(pet, duration=1.5, overlay_bottom=0.7),
        OUT / "08-hand-lands-higher.gif",
    )

    # A caller supplied overlay: a big transparent canvas with a small heart in
    # the top left corner, which is how the upstream project expects overlays.
    canvas = Image.new("RGBA", (240, 180), (0, 0, 0, 0))
    heart = Image.new("RGBA", (60, 60), (255, 70, 120, 255))
    canvas.paste(heart, (60, 10))
    save(petpet(pet, canvas, duration=1.5, overlay_scale=1.0), OUT / "09-custom-overlay.gif")

    print(f"wrote {len(list(OUT.glob('*.gif')))} GIFs to {OUT}")


if __name__ == "__main__":
    main()
