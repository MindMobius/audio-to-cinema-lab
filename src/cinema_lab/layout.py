"""Verified, non-destructive migration of the previous .local directory layout."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil

from .io import digest
from .music import atomic_json

DESTINATIONS = {
    "projects": "projects",
    "audio": "library/legacy/audio",
    "media": "library/legacy/media",
    "experiments": "library/legacy/experiments",
    "workflow-output": "library/legacy/workflow-output",
    "quality-audit": "library/legacy/quality-audit",
    "maintenance": "archive/maintenance",
}


def entries(root: Path):
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            yield Path(parent) / name


def mapped_target(root: Path, link: Path) -> str:
    target = os.readlink(link)
    for old, new in DESTINATIONS.items():
        prefix = str(root / ".local" / old)
        if target == prefix or target.startswith(prefix + "/"):
            return str(root / new) + target[len(prefix):]
    return target


def plan(root: Path) -> dict:
    root = root.expanduser().resolve()
    legacy = root / ".local"
    if not legacy.exists():
        return {"already_migrated": True, "files": 0, "bytes": 0, "conflicts": []}
    unknown = [p.name for p in legacy.iterdir() if p.name not in DESTINATIONS]
    conflicts = ["unmapped legacy entry: " + name for name in unknown]
    count, size, sources = 0, 0, []
    for old, new in DESTINATIONS.items():
        source = legacy / old
        if source.is_symlink():
            if source.resolve() != (root / new).resolve():
                conflicts.append("unexpected compatibility link: " + old)
            continue
        if not source.exists():
            continue
        sources.append(old)
        target_root = root / new
        if target_root.is_symlink():
            conflicts.append("destination root is a symlink: " + new)
            continue
        for path in entries(source):
            target = target_root / path.relative_to(source)
            if not target.parent.resolve().is_relative_to(root):
                conflicts.append("destination escapes workspace: " + str(target.relative_to(root)))
                continue
            if path.is_symlink():
                if os.path.lexists(target) and (not target.is_symlink() or os.readlink(target) != mapped_target(root, path)):
                    conflicts.append("link collision: " + str(target.relative_to(root)))
            elif path.is_dir():
                if os.path.lexists(target) and (target.is_symlink() or not target.is_dir()):
                    conflicts.append("directory collision: " + str(target.relative_to(root)))
            elif path.is_file():
                count += 1
                size += path.stat().st_size
                if os.path.lexists(target) and (target.is_symlink() or not target.is_file()
                                               or path.stat().st_size != target.stat().st_size or digest(path) != digest(target)):
                    conflicts.append("file collision: " + str(target.relative_to(root)))
            else:
                conflicts.append("unsupported legacy filesystem entry: " + str(path.relative_to(root)))
    return {"already_migrated": not sources, "sources": sources, "files": count, "bytes": size, "conflicts": conflicts}


def migrate(root: Path, *, apply: bool = False) -> dict:
    root = root.expanduser().resolve()
    result = plan(root)
    if result["conflicts"] or not apply or result["already_migrated"]:
        return result
    if shutil.disk_usage(root).free < result["bytes"] + 64 * 1024 * 1024:
        raise ValueError("insufficient free space for a verified copy; originals will not be moved")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = root / "archive" / ("layout-" + stamp)
    archive.mkdir(parents=True)
    originals = archive / "original-local"
    originals.mkdir()
    records = []
    atomic_json(archive / "migration.json", {**result, "status": "copying"})
    for old in result["sources"]:
        source = root / ".local" / old
        destination = root / DESTINATIONS[old]
        destination.mkdir(parents=True, exist_ok=True)
        for path in entries(source):
            target = destination / path.relative_to(source)
            if path.is_symlink():
                expected = mapped_target(root, path)
                if not os.path.lexists(target):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(expected)
                if not target.is_symlink() or os.readlink(target) != expected:
                    raise ValueError("copied link does not match the migration plan")
                records.append({"source": str(path.relative_to(root)), "target": str(target.relative_to(root)),
                                "kind": "symlink", "original_link": os.readlink(path), "new_link": expected})
            elif path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                before = digest(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    # Exclusive creation: a concurrent edit must never be overwritten.
                    with path.open("rb") as inp, target.open("xb") as out:
                        shutil.copyfileobj(inp, out, 4 * 1024 * 1024)
                    shutil.copystat(path, target)
                if digest(target) != before or digest(path) != before:
                    raise ValueError(f"migration checksum mismatch: {path.relative_to(root)}")
                records.append({"source": str(path.relative_to(root)), "target": str(target.relative_to(root)),
                                "kind": "file", "bytes": path.stat().st_size, "sha256": before})
    # All copies are verified before any original directory changes location.
    atomic_json(archive / "files.json", records)
    atomic_json(archive / "migration.json", {**result, "status": "verified; switching compatibility links"})
    for old in result["sources"]:
        source = root / ".local" / old
        source.rename(originals / old)
        source.symlink_to(Path("..") / DESTINATIONS[old], target_is_directory=True)
    result.update(status="complete", archive=str(archive.relative_to(root)), verified_entries=len(records),
                  compatibility_links={old: DESTINATIONS[old] for old in result["sources"]})
    atomic_json(archive / "migration.json", result)
    return result
