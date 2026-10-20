"""Command line playground: pat any image and write the GIF out.

    uv run python examples/try_yours.py pet.png
    uv run python examples/try_yours.py pet.png --duration 2 --speed 1.5 --out pat.gif
    uv run python examples/try_yours.py pet.png --overlay heart.gif --loop
    uv run python examples/try_yours.py            # no argument: uses a built-in shape

With no ``image`` argument it draws a simple stand-in pet, so you can see the
effect before pointing it at a real picture.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from headpat_gif import petpet

#: Where ``--out`` defaults to when it is not given.
DEFAULT_OUT = Path(__file__).parent / "out" / "try-yours.gif"


def demo_subject(size: tuple[int, int] = (240, 180)) -> Image.Image:
    """A simple stand-in pet, drawn so the example needs no input file."""
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    image.paste(Image.new("RGBA", (150, 90), (232, 220, 196, 255)), (45, 80))
    image.paste(Image.new("RGBA", (70, 60), (232, 220, 196, 255)), (60, 40))
    image.paste(Image.new("RGBA", (16, 16), (40, 40, 40, 255)), (70, 55))
    return image


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Make a pet-pet GIF out of an image.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("image", nargs="?", type=Path, help="the picture to pat")
    parser.add_argument("--overlay", type=Path, help="GIF or image to show on the head")
    parser.add_argument("--out", type=Path, help="where to write the GIF")
    parser.add_argument("--duration", type=float, default=2.0, help="total length in seconds")
    parser.add_argument("--speed", type=float, default=1.0, help="playback rate multiplier")
    parser.add_argument(
        "--once",
        action="store_true",
        help="pat once and rest, instead of petting over and over",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.8,
        help="size of the overlay: a multiple of the fit that covers the picture "
        "(0.8 = the default, 1.0 = it covers everything, 0.3 = a small hand)",
    )
    parser.add_argument(
        "--position",
        type=float,
        nargs=2,
        metavar=("X", "Y"),
        default=(0.0, 0.0),
        help="where the overlay's top-left corner sits on the picture, as "
        "fractions of its width and height (0 0 = its top-left corner)",
    )
    parser.add_argument(
        "--offset",
        type=float,
        nargs=2,
        metavar=("X", "Y"),
        default=(0.0, 0.0),
        help="move the overlay, as a fraction of the canvas; the picture grows "
        "to fit, so Y=-0.3 makes it 30%% taller",
    )
    parser.add_argument("--squash", type=float, default=1.0, help="0 disables the squash")
    parser.add_argument("--max-size", type=int, default=256, help="longest side in pixels")
    parser.add_argument("--name", default="petpet.gif", help="filename reported to Discord")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    subject = args.image if args.image is not None else demo_subject()
    gif = petpet(
        subject,
        args.overlay,
        duration=args.duration,
        speed=args.speed,
        loop=not args.once,
        squash=args.squash,
        max_size=args.max_size,
        overlay_scale=args.scale,
        overlay_position=tuple(args.position),
        overlay_offset=tuple(args.offset),
        name=args.name,
    )
    target = args.out or DEFAULT_OUT
    gif.save(target)

    width, height = gif.size
    print(
        f"{target}\n"
        f"  {width}x{height}, {gif.n_frames} frames, "
        f"{gif.duration_ms} ms total, {gif.cycle_ms} ms per pat, "
        f"{len(gif.to_bytes())} bytes"
    )


if __name__ == "__main__":
    main()
