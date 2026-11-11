"""Migrate stored paths and data, then remove the obsolete workspace directory."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
import re
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile

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


# Only owned production/configuration trees are rewritten. Source recordings,
# dependency installs and archived evidence are never treated as editable text.
ACTIVE_TREES = ("projects", "library", "tools")
SKIP_DIRECTORIES = {".git", ".venv", "node_modules", "__pycache__"}
TEXT_SUFFIXES = {
    ".py", ".json", ".md", ".txt", ".log", ".stdout", ".html", ".css",
    ".js", ".mjs", ".cjs", ".sh", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".otio", ".xml",
}
RELATIVE_LEGACY = re.compile(r"(?<![A-Za-z0-9_./-])\.local/")


def canonical_path(root: Path, path: Path) -> Path:
    # Use lexical paths: resolve() would follow a compatibility link before we
    # have checked its destination, and would lose the mapping we need to make.
    for old, new in DESTINATIONS.items():
        prefix = root / ".local" / old
        if path.is_relative_to(prefix):
            return root / new / path.relative_to(prefix)
    return path


def mapped_target(root: Path, link: Path) -> str:
    value = os.readlink(link)
    absolute = Path(os.path.abspath(link.parent / value))
    mapped = canonical_path(root, absolute)
    destination = canonical_path(root, link)
    if Path(value).is_absolute():
        return str(mapped)
    return os.path.relpath(mapped, destination.parent)


def rewrite_text(root: Path, path: Path, text: str) -> str:
    for old, new in DESTINATIONS.items():
        prefix = str(root / ".local" / old)
        # A delimiter prevents accidentally matching, e.g., projects-other.
        pattern = re.escape(prefix) + r"(?=$|[/\s\"'`<>),;])"
        text = re.sub(pattern, lambda _: str(root / new), text)
        text = text.replace(prefix.replace("/", "\\/"), str(root / new).replace("/", "\\/"))
    for old, new in DESTINATIONS.items():
        # Project media destinations are relative to that project, whereas
        # shared root media belongs to the workspace library.
        if old == "media" and (path.is_relative_to(root / "projects") or path == root / "tools/import_project.py"):
            new = "media"
        pattern = r"(?<![A-Za-z0-9_./-])\.local/" + re.escape(old) + r"(?=$|[/\s\"'`<>),;])"
        text = re.sub(pattern, lambda _: new, text)
    return text


def active_entries(root: Path, *, include_legacy: bool = False):
    bases = [root / name for name in ACTIVE_TREES]
    if include_legacy:
        bases += [root / ".local" / old for old in DESTINATIONS if old != "maintenance"]
    for base in bases:
        if not base.is_dir() or base.is_symlink():
            continue
        for parent, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRECTORIES]
            for name in sorted(dirs + files):
                yield Path(parent) / name


def reference_changes(root: Path, *, include_legacy: bool = False):
    changes, conflicts = [], []
    for source in active_entries(root, include_legacy=include_legacy):
        target = canonical_path(root, source)
        if source.is_symlink():
            before, after = os.readlink(source), mapped_target(root, source)
            if before != after:
                changes.append((source, target, "symlink", before, after))
            continue
        if not source.is_file() or source.suffix.lower() not in TEXT_SUFFIXES:
            continue
        raw = source.read_bytes()
        if b".local" not in raw or b"\0" in raw:
            continue
        try:
            before = raw.decode("utf-8")
        except UnicodeDecodeError:
            conflicts.append("cannot decode a legacy reference: " + str(source.relative_to(root)))
            continue
        after = rewrite_text(root, target, before)
        # Unsupported executable spellings require an explicit edit. Prose
        # mentioning the retired layout is not a runtime dependency.
        if source.suffix.lower() != ".md" and (str(root / ".local") in after or RELATIVE_LEGACY.search(after)):
            conflicts.append("unresolved legacy reference: " + str(source.relative_to(root)))
        if before != after:
            changes.append((source, target, "text", before, after))
    return changes, conflicts


def apply_references(root: Path, archive: Path) -> list[dict]:
    changes, conflicts = reference_changes(root)
    if conflicts:
        raise ValueError("; ".join(conflicts))
    records = []
    for source, target, kind, before, after in changes:
        if source != target or not source.parent.resolve().is_relative_to(root):
            raise ValueError("reference rewrite escaped the canonical workspace")
        backup = archive / "reference-originals" / source.relative_to(root)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if kind == "symlink":
            if os.readlink(source) != before:
                raise ValueError("link changed during migration")
            backup.symlink_to(before)
            source.unlink()
            source.symlink_to(after)
            records.append({"path": str(source.relative_to(root)), "kind": kind, "before": before, "after": after})
        else:
            old, new = before.encode("utf-8"), after.encode("utf-8")
            if source.read_bytes() != old:
                raise ValueError("text changed during migration")
            backup.write_bytes(old)
            shutil.copystat(source, backup)
            temporary = None
            try:
                with NamedTemporaryFile(dir=source.parent, prefix=".path-migration-", delete=False) as out:
                    temporary = Path(out.name)
                    out.write(new)
                shutil.copystat(source, temporary)
                temporary.replace(source)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            records.append({"path": str(source.relative_to(root)), "kind": kind,
                            "before_sha256": hashlib.sha256(old).hexdigest(), "sha256": digest(source)})
        atomic_json(archive / "references.json", records)
    return records


def plan(root: Path) -> dict:
    root = root.expanduser().resolve()
    legacy = root / ".local"
    conflicts = []
    if legacy.is_symlink() or (legacy.exists() and not legacy.is_dir()):
        return {"already_migrated": False, "conflicts": ["legacy root must be a real directory"]}
    unknown = [p.name for p in legacy.iterdir() if p.name not in DESTINATIONS] if legacy.exists() else []
    conflicts.extend("unmapped legacy entry: " + name for name in unknown)
    for name in ("projects", "library", "archive", "tools"):
        if (root / name).is_symlink():
            conflicts.append("workspace root is a symlink: " + name)
    count, size, sources, links = 0, 0, [], []
    for old, new in DESTINATIONS.items():
        source = legacy / old
        if source.is_symlink():
            if source.resolve() != root / new or not source.is_dir():
                conflicts.append("unexpected legacy link: " + old)
            else:
                links.append(old)
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
    changes, reference_conflicts = reference_changes(root, include_legacy=True) if not conflicts else ([], [])
    conflicts.extend(reference_conflicts)
    return {"already_migrated": not legacy.exists() and not changes, "sources": sources,
            "remove_links": links, "files": count, "bytes": size,
            "reference_files": len(changes), "conflicts": conflicts}


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
    atomic_json(archive / "migration.json", {**result, "status": "verified; rewriting stored references"})
    references = apply_references(root, archive)
    remaining, conflicts = reference_changes(root)
    if remaining or conflicts:
        raise ValueError("active legacy references remain; old directories have not been removed")
    # Actual assets have verified canonical copies. Originals live only in the
    # audit archive; the previous working directory is removed without aliases.
    for old in result["sources"]:
        (root / ".local" / old).rename(originals / old)
    for old in result["remove_links"]:
        link = root / ".local" / old
        if not link.is_symlink() or link.resolve() != root / DESTINATIONS[old]:
            raise ValueError("legacy link changed before removal")
        link.unlink()
    if (root / ".local").exists():
        (root / ".local").rmdir()
    result.update(status="complete", archive=str(archive.relative_to(root)), verified_entries=len(records),
                  rewritten_references=len(references), removed_legacy_root=True)
    atomic_json(archive / "migration.json", result)
    return result
