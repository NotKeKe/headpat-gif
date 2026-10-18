"""Access to the GIF that ships inside the wheel."""

from __future__ import annotations

import io
from importlib.resources import files

from PIL import Image

__all__ = ["ASSET_DIR", "DEFAULT_OVERLAY_NAME", "asset_bytes", "load_default_overlay"]

#: Folder inside the package that holds the bundled artwork.
ASSET_DIR = "assets"
#: The patting-hand GIF used when the caller passes no ``overlay``.
DEFAULT_OVERLAY_NAME = "default_overlay.gif"


def asset_bytes(name: str) -> bytes:
    """Return the raw bytes of a packaged asset.

    The asset is read through :mod:`importlib.resources`, so it also resolves
    when the package is imported from a zip or a wheel without unpacking.
    """
    resource = files("headpat_gif").joinpath(ASSET_DIR).joinpath(name)
    try:
        return resource.read_bytes()
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError) as exc:
        raise FileNotFoundError(
            f"packaged asset {ASSET_DIR}/{name} is missing; the installation looks incomplete"
        ) from exc


def load_default_overlay() -> Image.Image:
    """Open the bundled patting-hand GIF."""
    return Image.open(io.BytesIO(asset_bytes(DEFAULT_OVERLAY_NAME)))
