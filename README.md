# headpat-gif

[![PyPI](https://img.shields.io/pypi/v/headpat-gif.svg)](https://pypi.org/project/headpat-gif/)
[![Python versions](https://img.shields.io/pypi/pyversions/headpat-gif.svg)](https://pypi.org/project/headpat-gif/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Turn any image into a "pet-pet" GIF: a hand pats the subject on the head while
the subject squashes flat and springs back, exactly like clicking a pet in the
reference demo.

```python
from headpat_gif import petpet

gif = petpet("pet.png", duration=2.0)
gif.save("pet.gif")
```

Everything is swappable: bring your own animated overlay (the thing that appears
on the head) and your own subject. The result is an `io.BytesIO` subclass, so it
goes straight into `discord.File` with no temporary file:

```python
import discord
from headpat_gif import petpet

@bot.command()
async def pet(ctx, url: str):
    await ctx.send(file=discord.File(petpet(url, duration=2.0)))
```

## Install

```bash
uv add headpat-gif          # or: pip install headpat-gif
uv add "headpat-gif[discord]"   # optional: pulls discord.py for the test suite
```

Requires Python 3.10+ and Pillow 10+. ASCII-art style GIFs are left to you; the
only runtime dependency is Pillow.

## Usage

```python
from headpat_gif import petpet, save

# One pat, as long as the overlay takes to play.
gif = petpet("pet.png")

# Two seconds of continuous patting (loop is on by default).
gif = petpet("pet.png", duration=2.0)

# Two seconds of GIF, patting at double rate.
gif = petpet("pet.png", duration=2.0, speed=2.0)

# Pat once and then rest for the remainder of the two seconds.
gif = petpet("pet.png", duration=2.0, loop=False)

# A small hand resting on the head instead of covering the picture.
gif = petpet("pet.png", overlay_scale=0.4, overlay_anchor="top")

# Move the hand: fractions of the canvas. Negative y is up, and the picture
# grows to fit rather than slicing the hand off.
gif = petpet("pet.png", overlay_offset=(0.0, -0.3))   # 30% taller, hand complete
gif = petpet("pet.png", overlay_offset=(0.1, 0.15))   # down and to the right
gif = petpet("pet.png", overlay_offset=(0.0, 0.5), overlay_scale=0.4)  # bottom third

# Your own overlay: a path, bytes, an open file or a PIL image - GIF or still.
gif = petpet("pet.png", "heart.gif")
gif = petpet("pet.png", requests.get(url, timeout=10).content)

# Tune the look.
gif = petpet(
    "pet.png",
    "heart.gif",
    duration=1.5,
    squash=1.4,                 # harder squash
    overlay_scale=0.6,          # shrink the overlay to a hop-on-the-head size
    overlay_offset=(0.0, -0.05),  # nudge it up a touch
)

save(gif, "out/pet.gif")   # or: gif.save("out/pet.gif")
```

### Images from anywhere

`image` and `overlay` accept all of these:

| Input | Example |
| --- | --- |
| Filename / path | `petpet("pet.png")`, `petpet(Path("pet.png"))` |
| Raw bytes | `petpet(requests.get(url).content)` |
| Binary file object | `petpet(open("pet.png", "rb"))`, `petpet(io.BytesIO(data))` |
| Pillow image | `petpet(Image.open("pet.png"))` |

Animated overlays (GIF, animated WebP, APNG) keep their own frame timing; the
squash is synchronised to that timeline. A still overlay is shown for
`static_overlay_ms` (500ms by default) per cycle.

## API

### `petpet(image, overlay=None, *, ...) -> PetPetGif`

| Parameter | Default | Meaning |
| --- | --- | --- |
| `image` | *required* | The subject being patted. Animated input uses its first frame. |
| `overlay` | `None` | What appears on the head. `None` uses the bundled patting hand. |
| `duration` | `None` | Total length of the GIF in seconds. `None` = exactly one cycle. |
| `speed` | `1.0` | Playback rate multiplier: `2.0` plays the pat twice as fast. |
| `loop` | `True` | Keep patting until `duration` is filled, instead of resting after one pat. |
| `fps` | `25` | Output sampling rate, 10–50. |
| `max_size` | `256` | Longest side of the canvas in pixels (aspect ratio preserved). |
| `image_scale` | `0.8` | Subject size inside the canvas once it is back to normal. |
| `squash` | `1.0` | Squash strength. `0` disables it, `1` matches the reference. |
| `overlay_scale` | `None` | Overlay size. `None` stretches it over the whole canvas (the hand covers the picture); a number scales it to that fraction of a snug fit, e.g. `0.4` for a small hand on the head. |
| `overlay_offset` | `(0.0, 0.0)` | Move the overlay, as a fraction of the canvas: `(0.0, -0.2)` up, `(0.1, 0.0)` right. The canvas **grows** to fit instead of cropping, so `(0.0, -0.3)` makes the picture 30% taller. |
| `overlay_anchor` | `"top"` | Where a *shrunken* overlay sits: `"top"`, `"center"` or `"bottom"`. |
| `static_overlay_ms` | `500` | Cycle length when `overlay` is a still image. |
| `background` | `None` | Colour to flatten transparency onto, e.g. `"white"`. |
| `name` | `"petpet.gif"` | Filename reported to Discord. |

`duration` and `speed` are independent knobs. `duration` is the total runtime of
the file; `speed` scales how long the pat itself takes inside it. So
`duration=2.0, speed=2.0` means "two seconds of GIF, patting at double rate".

With `loop=True` (the default) the total is divided into a whole number of pats,
so an infinitely looping GIF never jumps mid-pat; the cycle length is nudged by
less than one frame to make that fit. Pass `loop=False` for the one-pat-then-rest
look.

### `PetPetGif`

An `io.BytesIO` subclass holding the encoded GIF.

```python
gif.save("out.gif")     # -> pathlib.Path
gif.to_bytes()          # -> bytes, without moving the read position
gif.name                # -> "petpet.gif", the name discord.py picks up
gif.size                # -> (width, height)
gif.n_frames            # -> frame count
gif.duration_ms         # -> total runtime in milliseconds
gif.cycle_ms            # -> length of one pat cycle in milliseconds
```

`discord.File(gif)` validates `seekable()`/`readable()` and takes the attachment
name from `.name`, so the object is accepted as-is.

> **Careful:** a `discord.File` is single-use. Build a fresh `PetPetGif` for
> every send, or reuse the bytes with `io.BytesIO(gif.to_bytes())`.

### `save(gif, path) -> pathlib.Path`

Module level convenience wrapper around `PetPetGif.save`.

## How it works

1. The subject is scaled to fit a square of `max_size`, then drawn at
   `image_scale` of the canvas, anchored 92% down so its feet stay put.
2. A triangular envelope drives the squash: untouched at the start of a cycle,
   widest and shortest in the middle, untouched again at the end. The amplitude
   matches [pet-pet-gif](https://github.com/camprevail/pet-pet-gif)
   (0.8 → 0.9 wide, 0.8 → 0.55 tall), so the motion feels like the GIFs people
   already know.
3. The overlay is pasted on top, sampled against its own frame durations, and
   plays exactly once per pat. By default it is stretched over the whole canvas,
   so a patting hand covers the picture and the subject squashes underneath it -
   the classic pet-pet look. Pass `overlay_scale` to shrink it onto the head.
4. Every frame is converted to palette mode with a dedicated transparent index
   and saved with `disposal=3` ("restore to previous"). Without the palette step
   Pillow writes black boxes around transparent areas; with disposal 2 instead
   of 3, decoders restore the *background colour* and the result is either an
   opaque black box (FFmpeg) or a stale copy of the previous frame (Pillow) -
   the classic transparent GIF bug, and very visible the moment an overlay
   moves or leaves. Both halves are covered by tests.

## Housekeeping notes

- GIF frame delays below 20ms are silently clamped to 100ms by browsers and
  Discord, so `fps` tops out at 50 and every delay is at least 20ms.
- Output is byte-for-byte deterministic: no randomness is involved, which keeps
  caching and snapshot tests sane.
- Want a smaller file? Lower `max_size`, lower `duration`, or pass
  `duration=None` and `speed` to shorten the tail.
- `duration` shorter than one cycle truncates the pat mid-way; use `speed` when
  the goal is a faster pat rather than a shorter one.

## Development

```bash
uv sync                                        # environment
uvx ruff check --fix .                         # style
uvx ty check                                   # types
uv run pytest                                  # tests
```

`scripts/check.ps1` (PowerShell) and `scripts/check.sh` (bash) run all four in
order. They also redirect `UV_CACHE_DIR` / `UV_TOOL_DIR` into `.uv/`, which is
needed when working inside a sandbox that cannot write to `%APPDATA%\uv`.

> If Windows refuses to run the script with "running scripts is disabled on this
> system", either run it as
> `powershell -ExecutionPolicy Bypass -File scripts/check.ps1`, or just run the
> three commands above directly.

## License

MIT - see [LICENSE](LICENSE). Bundled artwork and ported code are credited in
[NOTICE](NOTICE).
