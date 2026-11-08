"""Project-relative files, immutable media imports and local run outputs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inside(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(f"expected a relative POSIX path: {name!r}")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(p in ("..", ".") for p in name.split("/")):
        raise ValueError(f"path escapes project: {name!r}")
    target = root.resolve().joinpath(*relative.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"symlink escapes project: {name!r}")
    return target


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def matches(path: Path, record: dict) -> bool:
    return path.is_file() and path.stat().st_size == record["bytes"] and digest(path) == record["sha256"]


def copy_verified(source: Path, target: Path, record: dict) -> str:
    if target.exists():
        if matches(target, record):
            return "unchanged"
        raise ValueError(f"refusing to overwrite a different file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=target.parent, prefix=".import-", delete=False) as handle:
            temporary = Path(handle.name)
            h = hashlib.sha256()
            size = 0
            with source.open("rb") as input_file:
                for chunk in iter(lambda: input_file.read(4 * 1024 * 1024), b""):
                    handle.write(chunk)
                    h.update(chunk)
                    size += len(chunk)
        if size != record["bytes"] or h.hexdigest() != record["sha256"]:
            raise ValueError(f"source does not match manifest: {source}")
        # Atomic creation without clobbering an output another process has created.
        os.link(temporary, target)
        return "copied"
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
