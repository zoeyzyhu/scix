"""Template-root extraction helpers."""

from __future__ import annotations

from collections.abc import Iterable
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


def copy_template_paths(
    target_root: Path,
    relative_paths: Iterable[str | Path],
    overwrite: bool = False,
) -> list[Path]:
    """Copy a selected set of template paths into ``target_root``."""

    target_root = target_root.resolve()
    written: list[Path] = []
    root = template_root()
    for relative_path in relative_paths:
        relative = Path(relative_path)
        source = root.joinpath(*relative.parts)
        destination = target_root / relative
        if source.is_dir():
            _copy_dir(source, destination, written, overwrite=overwrite)
        else:
            _copy_file(source, destination, written, overwrite=overwrite)
    return written


def _copy_dir(source, target: Path, written: list[Path], overwrite: bool) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            _copy_dir(child, destination, written, overwrite=overwrite)
        else:
            _copy_file(child, destination, written, overwrite=overwrite)


def _copy_file(source, destination: Path, written: list[Path], overwrite: bool) -> None:
    if destination.exists() and not overwrite:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    if destination.suffix == ".sh":
        destination.chmod(0o755)
    written.append(destination)
