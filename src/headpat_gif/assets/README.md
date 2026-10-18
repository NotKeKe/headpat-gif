# Bundled assets

| File | Role |
| --- | --- |
| `default_overlay.gif` | The patting hand shown on the head when `petpet()` is called without `overlay`. 107x112, 5 frames x 70ms, transparent. |

Used through `headpat_gif._assets`, which reads the file with
`importlib.resources` so it resolves from a wheel, an sdist install or a zipped
package alike.

`overlay = None` picks this asset up automatically. It is authored for the
canvas, so it is stretched over the whole picture by default: the hand covers
the image and whatever is underneath gets squashed. Pass `overlay_scale` (its
own frame is 107x112) to shrink it down onto the head instead - around `0.4`
reads as a small hand resting on top - and `overlay_anchor` to say where that
smaller hand sits.

Provenance and licensing for this file are recorded in the repository root
`NOTICE`.
