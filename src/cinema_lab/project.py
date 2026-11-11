"""Creation and validation of portable project metadata."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .io import inside, load, write
from .recipes import load_recipe, scaffold

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SCHEMAS = Path(__file__).with_name("resources") / "schemas"


def schema_errors(name: str, value) -> list[str]:
    documents = [load(p) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources((d["$id"], Resource.from_contents(d)) for d in documents)
    validator = Draft202012Validator(load(SCHEMAS / name), registry=registry, format_checker=FormatChecker())
    return [f"{'/'.join(map(str, e.absolute_path)) or '/'}: {e.message}" for e in validator.iter_errors(value)]


def create(root: Path, day: str, slug: str, title: str, kind: str, *, recipe: str | None = None) -> Path:
    if not SLUG.fullmatch(slug):
        raise ValueError("slug must contain lowercase letters, digits and single hyphens")
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("date must be YYYY-MM-DD")
    if not title.strip():
        raise ValueError("title must not be empty")
    selected_recipe = load_recipe(recipe) if recipe is not None else None
    project = inside(root, f"{day}/{slug}")
    project.parent.mkdir(parents=True, exist_ok=True)
    project.mkdir()  # Existing projects must never be overwritten.
    for folder in ("audio", "concept", "assets", "shots", "workflows", "edit", "verification"):
        (project / folder).mkdir()
        (project / folder / "README.md").write_text(f"# {folder}\n\nProject: {title}\n", encoding="utf-8")
    write(project / "media.manifest.json", {"version": 1, "files": []})
    artifacts = {"media_manifest": "media.manifest.json"}
    if selected_recipe is not None:
        artifacts.update(scaffold(project, selected_recipe))
    write(project / "project.json", {
        "id": slug, "created": day, "title": title, "kind": kind, "status": "planning", "revision": "r1",
        "audio": {"role": "unknown", "source_policy": "private-local"},
        "artifacts": artifacts,
        "reproducibility": {"mode": "local-inputs-required", "notes": "Register source audio and assets before production."},
    })
    (project / "README.md").write_text(f"# {title}\n\nCreated {day}. Audio, analysis and creative plan are pending.\n", encoding="utf-8")
    return project


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    path = path.resolve()
    if not path.is_dir():
        return [f"project directory does not exist: {path}"]
    if not (path / "README.md").is_file():
        errors.append("missing README.md")
    try:
        data = load(path / "project.json")
        errors += schema_errors("project.schema.json", data)
        if errors:
            return errors
        if path.parent.name != data["created"] or path.name != data["id"] or path.parent.parent.name != "projects":
            errors.append("path must be projects/<created-date>/<id>")
        for key, relative in data["artifacts"].items():
            if not inside(path, relative).exists():
                errors.append(f"missing artifact {key}: {relative}")
        manifest = load(inside(path, data["artifacts"]["media_manifest"]))
        problems = schema_errors("media.schema.json", manifest)
        if problems:
            return errors + problems
        ids, sources = set(), set()
        path_records: dict[str, tuple[int, str]] = {}
        for item in manifest["files"]:
            # source is resolved against the external production workspace during restore.
            inside(path, item["path"])
            if not item["path"].startswith(("media/", "audio/")):
                errors.append(f"project media must be under media/ or audio/: {item['path']}")

            # A manifest id identifies a registration and must be unique. A physical
            # destination may appear more than once in an older manifest, but only
            # when every registration describes the same bytes. Timeline entries are
            # allowed to reuse one source any number of times.
            if item["id"] in ids:
                errors.append(f"duplicate media id: {item['id']}")
            ids.add(item["id"])
            signature = (item["bytes"], item["sha256"])
            previous = path_records.get(item["path"])
            if previous is None:
                path_records[item["path"]] = signature
            elif previous != signature:
                errors.append(f"media path has conflicting hashes: {item['path']}")
            sources.add(item["source"])
        if "composition" in data:
            for key in ("picture", "captions"):
                if data["composition"][key] not in ids:
                    errors.append(f"unknown composition {key} asset")
            for relative in data["composition"].get("source_files", []):
                if not inside(path, relative).is_file():
                    errors.append(f"missing composition source: {relative}")
        if "edit_timeline" in data["artifacts"]:
            timeline = load(inside(path, data["artifacts"]["edit_timeline"]))
            cursor, clip_ids = 0, set()
            for entry in timeline["entries"]:
                if entry["id"] in clip_ids:
                    errors.append(f"duplicate clip: {entry['id']}")
                clip_ids.add(entry["id"])
                if type(entry["duration_frames"]) is not int or entry["duration_frames"] <= 0 or type(entry["timeline_in_frames"]) is not int:
                    errors.append(f"invalid frame numbers: {entry['id']}")
                    continue
                if entry["timeline_in_frames"] != cursor:
                    errors.append(f"timeline gap or overlap: {entry['id']}")
                cursor += entry["duration_frames"]
                if entry["prepared_source"] not in sources or entry["source"] not in sources:
                    errors.append(f"unregistered clip media: {entry['id']}")
            if cursor != timeline["total_frames"]:
                errors.append("timeline frame count mismatch")
            if "delivery" in data and (cursor != data["delivery"]["frames"] or timeline["fps"] != data["delivery"]["fps"]):
                errors.append("timeline does not match delivery metadata")
            if timeline["audio"]["source"] not in sources:
                errors.append("unregistered timeline audio")
        if "caption_timing" in data["artifacts"]:
            timing = load(inside(path, data["artifacts"]["caption_timing"]))
            end, cue_ids = 0, set()
            if timing["cue_count"] != len(timing["cues"]):
                errors.append("caption count mismatch")
            for cue in timing["cues"]:
                start, stop = cue["start_frame"], cue["end_frame"]
                if type(start) is not int or type(stop) is not int or not end <= start < stop <= data["delivery"]["frames"]:
                    errors.append(f"invalid caption interval: {cue['id']}")
                if cue["id"] in cue_ids:
                    errors.append(f"duplicate caption id: {cue['id']}")
                cue_ids.add(cue["id"])
                end = stop
        if "shot_selection" in data["artifacts"]:
            selection = load(inside(path, data["artifacts"]["shot_selection"]))
            for shot in selection:
                for key in ("keyframe_workflow", "video_workflow"):
                    graph = inside(path, f"workflows/{shot[key]}/workflow.api.json")
                    if not graph.is_file():
                        errors.append(f"missing selected workflow: {shot[key]}")
        if "music_selection" in data["artifacts"]:
            from .io import matches
            selection = load(inside(path, data["artifacts"]["music_selection"]))
            for kind in ("audio", "lyrics"):
                if kind in selection and not matches(inside(path, selection[kind]["path"]), selection[kind]):
                    errors.append(f"pinned music {kind} is missing or changed")
            if data["audio"].get("sha256") != selection["audio"]["sha256"]:
                errors.append("project audio does not match pinned music version")
        # Registered metadata can be checked without restoring media bytes.
        if "public_files" in manifest:
            from .io import matches
            for item in manifest["public_files"]:
                if not matches(inside(path, item["path"]), item):
                    errors.append(f"public preview hash mismatch: {item['path']}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return errors
