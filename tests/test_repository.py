from collections import Counter
from pathlib import Path
import json

from cinema_lab.project import validate

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/2026-11-08/one-last-kiss"


def test_project_manifest_is_valid():
    assert validate(PROJECT) == []
    data = json.loads((PROJECT / "project.json").read_text())
    assert data["id"] == "one-last-kiss"
    assert data["title"] == "ONE LAST KISS"
    assert data["delivery"]["audio_preserved"] is True


def test_public_project_contains_no_large_media():
    media = {".mp4", ".mov", ".webm", ".m4a", ".mp3", ".wav", ".flac"}
    assert not [p for p in PROJECT.rglob("*") if p.is_file() and p.suffix.lower() in media]
    assert not [p for p in PROJECT.rglob("*") if p.is_file() and p.stat().st_size > 100 * 1024 * 1024]


def test_opening_contract_is_explicit():
    data = json.loads((PROJECT / "verification/render-check.json").read_text())
    assert data["opening"] == {
        "title": "ONE LAST KISS",
        "visible_from_seconds": 0,
        "fade_start_seconds": 5.25,
        "fade_end_seconds": 7,
    }


def test_reused_timeline_sources_have_one_physical_registration():
    timeline = json.loads((PROJECT / "edit/timeline.json").read_text())
    manifest = json.loads((PROJECT / "media.manifest.json").read_text())
    source_counts = Counter(entry["source"] for entry in timeline["entries"])
    assert [source for source, count in source_counts.items() if count > 1] == [
        "renders/video-05.mp4",
        "renders/video-08.mp4",
        "renders/video-19.mp4",
        "renders/video-20.mp4",
    ]
    registered = {(record["source"], record["path"]) for record in manifest["files"]}
    assert len(registered) == len(manifest["files"])
    assert all((source, f".local/media/{source}") in registered for source in source_counts)


def test_public_metadata_has_no_machine_specific_paths():
    forbidden = ("/home/agent/", "/mnt/c/Users/", "C:\\\\Users\\")
    for path in PROJECT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".woff2"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert not any(value in text for value in forbidden), path
