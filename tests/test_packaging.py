"""Guards on the metadata that makes the project publishable to PyPI."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
PROJECT = PYPROJECT["project"]

WHEELS = sorted((ROOT / "dist").glob("*.whl"))
SDISTS = sorted((ROOT / "dist").glob("*.tar.gz"))


def test_metadata_is_complete_enough_to_publish() -> None:
    for field in ("name", "version", "description", "readme", "license", "authors", "urls"):
        assert PROJECT.get(field), f"pyproject.toml is missing project.{field}"
    assert PROJECT["name"] == "headpat-gif"
    assert PROJECT["keywords"]
    assert any(line.startswith("Programming Language :: Python :: 3") for line in PROJECT["classifiers"])
    assert PROJECT["dependencies"] == ["pillow>=10.0.0"]


def test_version_matches_the_changelog() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## [{PROJECT['version']}]" in changelog or "## [Unreleased]" in changelog


def test_documentation_files_exist() -> None:
    for name in ("README.md", "LICENSE", "NOTICE", "CHANGELOG.md"):
        assert (ROOT / name).is_file(), f"{name} is missing"


def test_the_wheel_targets_the_src_layout() -> None:
    wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert wheel["packages"] == ["src/headpat_gif"]
    assert (ROOT / "src" / "headpat_gif" / "py.typed").is_file()


def test_the_bundled_asset_sits_inside_the_package_directory() -> None:
    asset = ROOT / "src" / "headpat_gif" / "assets" / "default_overlay.gif"

    assert asset.is_file()
    assert asset.stat().st_size > 0


@pytest.mark.skipif(not WHEELS, reason="run `uv build` first to check the built wheel")
def test_the_built_wheel_ships_code_and_assets() -> None:
    with zipfile.ZipFile(WHEELS[-1]) as archive:
        names = set(archive.namelist())

    assert "headpat_gif/__init__.py" in names
    assert "headpat_gif/py.typed" in names
    assert "headpat_gif/assets/default_overlay.gif" in names


@pytest.mark.skipif(not SDISTS, reason="run `uv build` first to check the built sdist")
def test_the_built_sdist_ships_the_sources() -> None:
    import tarfile

    with tarfile.open(SDISTS[-1]) as archive:
        names = set(archive.getnames())

    assert any(name.endswith("src/headpat_gif/_api.py") for name in names)
    assert any(name.endswith("tests/test_api.py") for name in names)


def test_every_module_imports_through_importlib() -> None:
    # A cheap smoke test that nothing in the package depends on the working
    # directory or on a path outside the package.
    import importlib

    for module in ("headpat_gif", "headpat_gif._api", "headpat_gif._palette", "headpat_gif._compose"):
        assert importlib.import_module(module) is not None
