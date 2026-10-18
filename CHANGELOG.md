# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/NotKeKe/petpet-gif/commits/main
