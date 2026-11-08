#!/usr/bin/env python3
"""One-time importer for the legacy ONE LAST KISS production folder.

The importer copies metadata, selected previews and executable workflow graphs. It
intentionally omits private audio, full lyrics, video renders, model outputs and
runtime caches. The omitted files remain available in the original production
workspace and are represented by manifests in the imported project.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


KEYFRAMES = ("01", "02", "07", "14", "19", "24", "31", "39")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitize_public_paths(value: object, production_parent: Path) -> object:
    """Replace local production paths with an explicit restore-time placeholder."""
    if isinstance(value, dict):
        return {key: sanitize_public_paths(item, production_parent) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_public_paths(item, production_parent) for item in value]
    if isinstance(value, str):
        prefix = production_parent.resolve().as_posix() + "/"
        if value.startswith(prefix):
            return "${LOCAL_PROJECT_ROOT}/" + value[len(prefix):]
    return value


def copy_json_sanitized(src: Path, dst: Path, production_parent: Path) -> None:
    write_json(dst, sanitize_public_paths(json.loads(src.read_text(encoding="utf-8")), production_parent))


def add_media_record(
    source_root: Path,
    records: list[dict],
    by_location: dict[tuple[str, str], dict],
    *,
    record_id: str,
    source: str,
    destination: str,
    profiles: list[str],
) -> None:
    """Register one physical file, merging profiles when a timeline reuses it."""
    source_path = source_root / source
    if not source_path.is_file():
        raise SystemExit(f"missing production media: {source_path}")
    record = {
        "id": record_id,
        "source": source,
        "path": destination,
        "bytes": source_path.stat().st_size,
        "sha256": sha256(source_path),
        "profiles": list(dict.fromkeys(profiles)),
    }
    key = (record["source"], record["path"])
    existing = by_location.get(key)
    if existing is None:
        by_location[key] = record
        records.append(record)
        return
    if (existing["bytes"], existing["sha256"]) != (record["bytes"], record["sha256"]):
        raise SystemExit(f"same media location has changed bytes: {source}")
    existing["profiles"] = list(dict.fromkeys(existing["profiles"] + record["profiles"]))


def build_media_manifest(
    source: Path,
    destination: Path,
    timeline: dict,
    source_audio: Path,
    final: Path,
    clean: Path,
) -> dict:
    records: list[dict] = []
    by_location: dict[tuple[str, str], dict] = {}

    add_media_record(
        source,
        records,
        by_location,
        record_id="audio-master",
        source=source_audio.name if source_audio.parent == source else source_audio.relative_to(source).as_posix(),
        destination=f".local/media/audio/{source_audio.name}",
        profiles=["audio", "full-production", "render"],
    )
    add_media_record(
        source,
        records,
        by_location,
        record_id="delivery-bilingual",
        source=final.name,
        destination=f".local/media/delivery/{final.name}",
        profiles=["delivery", "full-production"],
    )
    add_media_record(
        source,
        records,
        by_location,
        record_id="picture-master",
        source=clean.name,
        destination=f".local/media/picture/{clean.name}",
        profiles=["composition", "full-production", "render"],
    )

    for entry in timeline["entries"]:
        source_name = entry["source"]
        add_media_record(
            source,
            records,
            by_location,
            record_id=f"clip-{entry['id']}-source",
            source=source_name,
            destination=f".local/media/{source_name}",
            profiles=["full-production", "render"],
        )
        prepared = entry.get("prepared_source")
        if prepared:
            add_media_record(
                source,
                records,
                by_location,
                record_id=f"clip-{entry['id']}-prepared_source",
                source=prepared,
                destination=f".local/media/{prepared}",
                profiles=["full-production", "render"],
            )

    for record_id, source_name in (
        ("caption-composition", "hyperframes-bilingual/compositions/captions.html"),
        ("caption-cues", "hyperframes-bilingual/captions.json"),
        ("lyric-cues", "subtitles/cues.json"),
    ):
        add_media_record(source, records, by_location, record_id=record_id,
                         source=source_name, destination=f".local/media/{source_name}",
                         profiles=["composition", "full-production"] if record_id != "lyric-cues" else ["full-production"])

    public_files = []
    for path in sorted(destination.rglob("*")):
        if path.is_file() and not path.name.endswith(".manifest.json"):
            relative = path.relative_to(destination).as_posix()
            if relative.startswith("assets/") and path.suffix.lower() == ".png":
                public_files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
            elif relative == "verification/opening-preview.png":
                public_files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})

    return {"version": 1, "files": records, "public_files": public_files}


def build_project(source: Path, destination: Path) -> None:
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty project: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    timeline = json.loads((source / "edit/timeline.json").read_text(encoding="utf-8"))
    source_audio = source / "audio/one-last-kiss-original.m4a"
    final = source / "one-last-kiss-mv-bilingual.mp4"
    clean = source / "one-last-kiss-mv-final.mp4"

    project = {
        "id": destination.name,
        "created": "2026-11-08",
        "title": "ONE LAST KISS",
        "status": "delivered",
        "kind": "lyric-music-video",
        "revision": "opening-credits-r1",
        "audio": {
            "role": "song",
            "source_policy": "private-local",
            "source_filename": source_audio.name,
            "duration_seconds": 259.199833,
            "sample_rate": 48000,
            "channels": 2,
            "sha256": sha256(source_audio),
            "lyrics_policy": "private-local; full lyric text is omitted from the public repository",
        },
        "artifacts": {
            "creative_plan": "concept/storyboard.json",
            "audio_analysis": "audio/analysis.json",
            "beat_grid": "audio/beat-grid-fit.json",
            "character_manifest": "assets/character-source-manifest.json",
            "shot_selection": "shots/selection.json",
            "edit_timeline": "edit/timeline.json",
            "hyperframes_source": "edit/hyperframes/",
            "caption_timing": "edit/subtitles/timing.json",
            "media_manifest": "media.manifest.json",
            "verification": "verification/render-check.json",
        },
        "delivery": {
            "filename": "ONE LAST KISS - 双语字幕版.mp4",
            "source_filename": final.name,
            "sha256": sha256(final),
            "width": 1920,
            "height": 1080,
            "fps": 24,
            "frames": 6221,
            "duration_seconds": 259.208333,
            "audio_preserved": True,
        },
        "reproducibility": {
            "mode": "local-inputs-required",
            "notes": "Public repository contains metadata, selected previews, workflow graphs and HyperFrames source. Restore the private audio, lyric cues, generated clips and local ComfyUI inputs from the manifests before rendering.",
        },
        "composition": {
            "picture": "picture-master",
            "captions": "caption-composition",
            "adapter": "hyperframes", "version": "0.9.7",
            "media": {
                "assets/one-last-kiss-clean.mp4": "picture-master",
                "compositions/captions.html": "caption-composition",
                "captions.json": "caption-cues",
            },
            "source_files": [
                "edit/hyperframes/index.html",
                "edit/hyperframes/compositions/opening.html",
            ],
        },
    }
    write_json(destination / "project.json", project)

    # Preserve measured provenance while removing the producing machine's private path.
    provenance_source = source / "research/provenance.json"
    if provenance_source.exists():
        provenance = json.loads(provenance_source.read_text(encoding="utf-8"))
        source_audio_record = provenance.get("source_audio", {})
        original_path = source_audio_record.pop("original_windows_path", None)
        if original_path:
            source_audio_record["original_filename"] = original_path.rsplit("\\", 1)[-1]
        provenance["record_scope"] = "Historical picture-edit record, before bilingual subtitles and the final HyperFrames opening revision. Current delivery hashes are in project.json and media.manifest.json."
        write_json(destination / "workflows/provenance.json", sanitize_public_paths(provenance, source.parent))
    environment_source = source / "research/environment.json"
    if environment_source.exists():
        copy(environment_source, destination / "verification/environment.json")

    # Audio observations contain no lyric text.
    copy_json_sanitized(source / "audio/analysis.json", destination / "audio/analysis.json", source.parent)
    copy_json_sanitized(source / "audio/beat-grid-fit.json", destination / "audio/beat-grid-fit.json", source.parent)
    write_json(destination / "audio/source.manifest.json", {
        "filename": source_audio.name,
        "source_policy": "private-local",
        "duration_seconds": 259.199833,
        "sample_rate": 48000,
        "channels": 2,
        "sha256": sha256(source_audio),
        "restore_hint": "Run cinema-lab media restore with --profile audio; restored files are kept under ignored .local/media/.",
    })

    copy_json_sanitized(source / "storyboard.json", destination / "concept/storyboard.json", source.parent)
    (destination / "concept/README.md").write_text(
        "# Creative plan\n\nThe storyboard is the selected visual interpretation of the audio. Its prompts are production notes, not a claim that the generated result is deterministic across machines.\n",
        encoding="utf-8",
    )

    # Public previews: generated cards and a small set of selected keyframes.
    for path in sorted((source / "assets/cards").glob("*.png")):
        copy(path, destination / "assets/cards" / path.name)
    for name in KEYFRAMES:
        path = source / f"keyframes/keyframe-{name}.png"
        if path.exists():
            copy(path, destination / "assets/keyframes" / path.name)
    for name in ("character-source-manifest.json", "original-reference-manifest.json"):
        copy_json_sanitized(source / f"assets/{name}", destination / f"assets/{name}", source.parent)
    (destination / "assets/README.md").write_text(
        "# Public asset previews\n\nThe repository includes selected generated character cards and keyframes for review. Original source identity images, full character views and private inputs remain local. The manifests preserve provenance and filenames needed for restoration.\n",
        encoding="utf-8",
    )

    # Keep executable workflow graphs and prompts, but omit ComfyUI history and generated media.
    copy_json_sanitized(source / "workflows/selected-workflows.json", destination / "shots/selection.json", source.parent)
    for folder in sorted((source / "workflows").iterdir()):
        if not folder.is_dir():
            continue
        for pattern in ("workflow.api.json", "workflow.ui.json", "prompt.txt", "result.json", "submission.json"):
            path = folder / pattern
            if path.exists():
                target = destination / "workflows" / folder.name / pattern
                if path.suffix == ".json":
                    copy_json_sanitized(path, target, source.parent)
                else:
                    copy(path, target)
    (destination / "workflows/README.md").write_text(
        "# Recorded generation workflows\n\nThese graphs and prompts are the actual selected production records. They require the local ComfyUI installation, model files, custom nodes and private input references listed in the manifests. A recorded workflow is evidence of production, not a portable claim that every machine can run it unchanged.\n",
        encoding="utf-8",
    )

    # Remove lyric text from the public project while preserving frame timing.
    cues = json.loads((source / "subtitles/cues.json").read_text(encoding="utf-8"))
    timing = [{k: cue[k] for k in ("id", "reference_start", "language", "kind", "start_frame", "end_frame", "start", "end", "timing_basis")} for cue in cues]
    write_json(destination / "edit/subtitles/timing.json", {"cue_count": len(timing), "cues": timing, "text_policy": "private-local"})
    copy(source / "edit/timeline.json", destination / "edit/timeline.json")
    copy(source / "edit/one-last-kiss.otio", destination / "edit/one-last-kiss.otio")
    (destination / "edit/subtitles/README.md").write_text(
        "# Subtitle timing\n\nThe public project stores cue timing and style rules without reproducing the full copyrighted lyric text or translation. Restore the private cue file before rebuilding the bilingual caption composition.\n",
        encoding="utf-8",
    )

    # HyperFrames source: preserve the opening composition and a caption template.
    hf = source / "hyperframes-bilingual"
    for name in ("index.html", "hyperframes.json", "meta.json", "package.json", "SPEC.md", "REVIEW.md"):
        copy(hf / name, destination / "edit/hyperframes" / name)
    copy(hf / "compositions/opening.html", destination / "edit/hyperframes/compositions/opening.html")
    copy(hf / "assets/gsap.min.js", destination / "edit/hyperframes/assets/gsap.min.js")
    for font in (hf / "assets/fonts").glob("*.woff2"):
        copy(font, destination / "edit/hyperframes/assets/fonts" / font.name)
    for notice in ("NotoCJK-LICENSE.txt", "DejaVuSans-LICENSE.txt"):
        path = hf / "assets/fonts" / notice
        if path.exists():
            copy(path, destination / "edit/hyperframes/assets/fonts" / notice)
    (destination / "edit/hyperframes/compositions/captions.template.html").write_text(
        "<!-- Restore the private captions.html from the local production workspace. The public repository intentionally omits full lyric text. -->\n",
        encoding="utf-8",
    )
    (destination / "edit/hyperframes/README.md").write_text(
        "# HyperFrames source\n\nThe opening title composition is public and editable. The full bilingual caption composition and source video are private-local because they contain the supplied recording and complete lyric text. Restore them from the local production project before running HyperFrames. Third-party resources are listed in the repository-level `THIRD_PARTY_NOTICES.md`.\n",
        encoding="utf-8",
    )

    verification = json.loads((source / "subtitles/verification/final-summary.json").read_text(encoding="utf-8"))
    public_check = {
        "status": "verified",
        "video": {k: verification["final"][k] for k in ("width", "height", "fps", "frames", "video_duration", "audio_duration")},
        "checks": verification["checks"],
        "opening": {"title": "ONE LAST KISS", "visible_from_seconds": 0, "fade_start_seconds": 5.25, "fade_end_seconds": 7},
        "public_media_policy": "delivery files, source audio, full lyrics and generated video clips are omitted from Git",
    }
    write_json(destination / "verification/render-check.json", public_check)
    copy(source / "verification/opening-preview.png", destination / "verification/opening-preview.png")
    (destination / "verification/README.md").write_text(
        "# Verification\n\nThis folder contains the public technical summary and a preview of the HyperFrames opening. The complete local verification logs remain in the production workspace.\n",
        encoding="utf-8",
    )

    media_manifest = build_media_manifest(source, destination, timeline, source_audio, final, clean)
    write_json(destination / "media.manifest.json", media_manifest)

    (destination / "README.md").write_text(f'''# ONE LAST KISS\n\nFirst migrated project for Audio-to-Cinema Lab.\n\n- Created: 2026-11-08\n- Type: audio-driven lyric music video\n- Duration: 4:19.208 at 24 fps\n- Delivery: 1920×1080 with the supplied AAC audio preserved\n- Opening: `ONE LAST KISS` appears from frame 0; performer, lyricist and composer credits fade out by 7 seconds\n- Status: delivered and technically verified\n\n## What is in Git\n\nThe repository keeps the creative plan, audio observations, asset provenance, selected previews, ComfyUI workflow graphs, edit timeline, HyperFrames opening source and verification summary.\n\n## What stays private-local\n\nThe source recording, complete lyric text and translations, full generated video clips, model files, ComfyUI runtime state and machine-specific caches are intentionally omitted. This keeps the public repository smaller and avoids publishing user-supplied copyrighted material. `project.json` and the manifests preserve hashes and restoration hints.\n\n## Production source\n\nThe complete working project is retained at `${{LOCAL_PROJECT_ROOT}}/one-last-kiss-mv-20261108` on the producing machine. The public project is a documented migration, not a replacement for that private media workspace.\n''', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build_project(args.source.resolve(), args.destination.resolve())
    print(f"Imported {args.source} -> {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
