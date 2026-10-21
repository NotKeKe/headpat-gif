# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1b4] - 2026-10-21

### Fixed

- The overlay is scaled by the canvas' **width** instead of by whichever axis
  wanted the bigger factor. On a portrait picture such as 9:16 the old "cover"
  rule picked the *height*, so a 144x256 output drew the hand at 196x205 - 1.7x
  wider than the frame, with the picture buried underneath. Tall pictures now get
  a hand to match their width (115x121 for the same canvas), and wide and square
  pictures are unchanged.

## [0.2.1b3] - 2026-10-20

### Changed

- `overlay_offset` defaults to `(0.0, -0.15)`. The hand now hangs over the
  picture - 15% of the canvas above its top edge - instead of starting level with
  it, and the canvas grows by that amount to keep the hand whole. **The default
  output is therefore 15% taller than the input's aspect ratio**: a 256x192
  picture comes back 256x221, a 256x144 one 256x166. Pass
  `overlay_offset=(0.0, 0.0)` for the old canvas that matched the picture exactly.

## [0.2.1b2] - 2026-10-20

### Fixed

- `overlay_position` is measured against the **canvas**, not the picture inside
  it. `0.2.1b1` pinned the overlay to the subject's box, which `image_scale`
  insets by 10% on each side, so the default `(0.0, 0.0)` still left a transparent
  strip along the left edge of the finished GIF: the hand started at x=25 of 256
  instead of x=0. `(0.0, 0.0)` now puts the overlay in the corner of the GIF
  itself, so it touches the left and top edges, which is what "flush with the
  corner" means when you look at the output.
- `overlay_position=(1.0, 1.0)` now means the canvas' bottom-right corner, and a
  full cover fit (`overlay_scale=1.0`) once again covers the whole canvas.

## [0.2.1b1] - 2026-10-20

### Changed

- The overlay is drawn at 80% of the cover fit by default (`overlay_scale` is now
  `0.8` instead of `None`), which leaves more of the picture visible than the
  full cover fit while keeping the "a hand is patting this" read.
- **Breaking:** the overlay is pinned to the picture's top-left corner by
  default instead of hanging from its bottom edge. `overlay_bottom` is gone and
  `overlay_position` replaces it: the fraction of the *picture's* width and
  height where the overlay's visible top-left corner sits, `(0.0, 0.0)` (the
  default) being that corner itself. Positioning against the picture rather than
  the canvas keeps "flush with the corner" true whatever margin `image_scale`
  leaves around the picture.

## [0.2.0] - 2026-10-20

### Fixed

- The overlay no longer changes its aspect ratio with the input. It used to be
  resized straight to the canvas, so a wide picture got a horizontally stretched
  hand and a tall one got a squashed hand. It is now scaled uniformly, by a single
  factor taken from whichever canvas axis asks for the bigger one (a "cover"
  fit), so the hand is always enlarged - or shrunk - by the same amount in both
  directions, exactly like the source GIF.

### Added

- `overlay_bottom`: where the bottom edge of the visible overlay sits, as a
  fraction of the canvas height. `1.0` (the default) rests it on the bottom edge;
  `0.6` puts the hand's lower edge 60% of the way down. This is the knob that
  positions the hand - a hand drawn in the upper part of its own frame is
  positioned by where its pixels actually end, not by the frame's bounding box.

### Changed

- **Breaking:** `overlay_scale` is now a multiplier on that uniform cover fit
  instead of a "snug fit" fraction. `overlay_scale=0.4` still means "a small hand
  on the head" but is computed from the cover size, so the numbers behave
  differently from `0.1.0`.
- **Breaking:** removed `overlay_anchor`. `overlay_bottom` positions the overlay
  at any height, so a separate top/center/bottom switch was redundant.
- Overflow caused by the cover fit is now cropped instead of growing the canvas.
  The canvas still grows for `overlay_offset`, so `overlay_offset=(0.0, -0.3)`
  keeps returning an image 30% taller - it only grows for the nudge, not for the
  scaling.

## [0.1.0] - 2026-10-18

### Added

- `petpet(image, overlay=None, *, ...)` returning a `PetPetGif`.
- `PetPetGif.save()` and the module level `save()` helper.
- `PetPetGif` is an `io.BytesIO` subclass with a `.name`, so `discord.File(gif)`
  accepts it directly without touching the filesystem.
- Bundled transparent patting-hand overlay used when no `overlay` is supplied.
- Independent `duration` (total GIF seconds) and `speed` (playback rate) knobs,
  plus `loop` to repeat the cycle instead of resting.
- Tunable geometry: `fps`, `max_size`, `image_scale`, `squash`,
  `overlay_scale`, `overlay_offset`, `overlay_anchor`, `static_overlay_ms`,
  `background`.
- Deterministic transparent GIF writer (no randomness, byte-identical output).
- Test suite covering the API contract, timing, squash geometry, transparency
  and packaging; `scripts/check.ps1` / `scripts/check.sh` run ruff, ty and
  pytest in one go.
- `examples/try_yours.py`, a command line playground for patting your own image.

### Changed

- `overlay_offset` no longer crops the overlay: the canvas grows to include it,
  so pushing the hand up by `-0.3` returns an image 30% taller with the whole
  hand visible and the subject unchanged in size. `PetPetGif.size` reports the
  grown size, so `max_size` is now a starting point rather than a hard limit.
- The overlay now stretches over the whole canvas by default, so the patting
  hand covers the picture and the subject squashes underneath it - the classic
  pet-pet look. Pass `overlay_scale` (e.g. `0.4`) for a small hand on the head
  instead.
- `overlay_anchor` defaults to `"top"`; it positions the overlay when
  `overlay_scale` shrinks it.
- `loop` defaults to `True`, so `petpet(img, duration=2.0)` keeps patting
  instead of resting after a single pat. Looping now fits a whole number of
  cycles into `duration`, so the infinitely looping GIF has no visible jump.

[Unreleased]: https://github.com/NotKeKe/headpat-gif/compare/v0.2.1b4...HEAD
[0.2.1b4]: https://github.com/NotKeKe/headpat-gif/compare/v0.2.1b3...v0.2.1b4
[0.2.1b3]: https://github.com/NotKeKe/headpat-gif/compare/v0.2.1b2...v0.2.1b3
[0.2.1b2]: https://github.com/NotKeKe/headpat-gif/compare/v0.2.1b1...v0.2.1b2
[0.2.1b1]: https://github.com/NotKeKe/headpat-gif/compare/v0.2.0...v0.2.1b1
[0.2.0]: https://github.com/NotKeKe/headpat-gif/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/NotKeKe/headpat-gif/releases/tag/v0.1.0
