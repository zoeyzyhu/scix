"""Template-root extraction helpers."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def template_root():
    """Return the packaged workspace template root."""
    return files("scix.assets").joinpath("template_root")


def copy_template_root(target_root: Path, overwrite: bool = False) -> list[Path]:
    """Copy the packaged template root into ``target_root``.

    Existing files are preserved unless ``overwrite`` is true.
    """

    target_root = target_root.resolve()
    written: list[Path] = []
    _copy_dir(template_root(), target_root, written, overwrite=overwrite)
    return written


def _copy_dir(source, target: Path, written: list[Path], overwrite: bool) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            _copy_dir(child, destination, written, overwrite=overwrite)
        else:
            if destination.exists() and not overwrite:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(child.read_bytes())
            if destination.suffix == ".sh":
                destination.chmod(0o755)
            written.append(destination)
