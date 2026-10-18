"""The artwork that ships inside the wheel."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from headpat_gif import DEFAULT_OVERLAY_NAME, petpet
from headpat_gif._assets import ASSET_DIR, asset_bytes, load_default_overlay
from support import frame_delays


def test_the_bundled_overlay_is_the_documented_asset() -> None:
    image = load_default_overlay()

    assert DEFAULT_OVERLAY_NAME == "default_overlay.gif"
    assert image.format == "GIF"
    assert image.size == (107, 112)
    assert getattr(image, "n_frames", 1) == 5
    assert frame_delays(io.BytesIO(asset_bytes(DEFAULT_OVERLAY_NAME))) == [70] * 5


def test_the_bundled_overlay_really_is_transparent() -> None:
    image = Image.open(io.BytesIO(asset_bytes(DEFAULT_OVERLAY_NAME))).convert("RGBA")
    alphas = image.getchannel("A").getextrema()

    assert alphas[0] == 0
    assert alphas[1] == 255


def test_the_bundled_overlay_drives_the_default_cycle(subject: Image.Image) -> None:
    assert petpet(subject).cycle_ms == 350


def test_a_missing_asset_is_reported_clearly() -> None:
    with pytest.raises(FileNotFoundError, match="packaged asset"):
        asset_bytes("not-here.gif")


def test_the_asset_lives_inside_the_package() -> None:
    # It has to sit inside the importable package for the wheel to ship it.
    from importlib.resources import files

    inside_package = files("headpat_gif").joinpath(ASSET_DIR).joinpath(DEFAULT_OVERLAY_NAME)

    assert inside_package.is_file()
    assert inside_package.read_bytes() == asset_bytes(DEFAULT_OVERLAY_NAME)
