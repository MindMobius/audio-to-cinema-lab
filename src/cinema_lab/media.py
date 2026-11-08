"""Recover registered files from a user's existing production folder."""
from pathlib import Path

from .io import copy_verified, inside, load, matches


def records(project: Path, profile: str = "all") -> list[dict]:
    config = load(project / "project.json")
    items = load(inside(project, config["artifacts"]["media_manifest"]))["files"]
    return [x for x in items if profile == "all" or profile in x["profiles"]]


def audit(project: Path, profile: str = "all") -> dict:
    checked = [{"id": x["id"], "ok": matches(inside(project, x["path"]), x)} for x in records(project, profile)]
    return {"ok": all(x["ok"] for x in checked), "checked": len(checked), "missing_or_changed": [x["id"] for x in checked if not x["ok"]]}


def restore(project: Path, source: Path, profile: str) -> dict:
    items = records(project, profile)
    # Check every source and destination before starting an import.
    for item in items:
        src, dst = inside(source, item["source"]), inside(project, item["path"])
        if not src.is_file():
            raise ValueError(f"missing source asset: {item['source']}")
        if dst.exists() and not matches(dst, item):
            raise ValueError(f"refusing to overwrite modified asset: {item['path']}")
    results = [copy_verified(inside(source, x["source"]), inside(project, x["path"]), x) for x in items]
    return {"ok": True, "copied": results.count("copied"), "unchanged": results.count("unchanged")}
