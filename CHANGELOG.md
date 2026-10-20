# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/NotKeKe/headpat-gif/compare/v0.2.1b1...HEAD
[0.2.1b1]: https://github.com/NotKeKe/headpat-gif/compare/v0.2.0...v0.2.1b1
[0.2.0]: https://github.com/NotKeKe/headpat-gif/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/NotKeKe/headpat-gif/releases/tag/v0.1.0
