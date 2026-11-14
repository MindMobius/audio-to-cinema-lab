"""Contract tests use synthetic metadata, never concrete songs or private projects."""
from pathlib import Path
import copy
import json

import pytest

from cinema_lab.cli import main
from cinema_lab.io import write
from cinema_lab.project import create, validate
from cinema_lab.recipes import RECIPE_IDS, load_recipe


@pytest.fixture
def project(tmp_path):
    return create(tmp_path / "projects", "2026-11-11", "synthetic", "Synthetic fixture", "test")


def read(path):
    return json.loads(path.read_text())


def test_draft_accepts_unknown_duration_but_production_requires_measurement(project):
    assert validate(project) == []
    manifest = read(project / "project.json")
    manifest["status"] = "production"
    write(project / "project.json", manifest)
    assert any("duration_seconds" in issue for issue in validate(project))
    manifest["audio"]["duration_seconds"] = 1.0
    write(project / "project.json", manifest)
    assert validate(project) == []


def test_cli_defaults_to_local_root_and_copies_recipe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--date", "2026-11-11", "--slug", "demo", "--title", "Demo", "--recipe", "continuous-scroll"]) == 0
    project = tmp_path / "projects/2026-11-11/demo"
    assert project.is_dir()
    assert validate(project) == []
    manifest = read(project / "project.json")
    assert all((project / name).is_file() for name in manifest["artifacts"].values())
    copied = read(project / "concept/recipe.json")
    assert copied == load_recipe("continuous-scroll")
    assert copied["render_runner"] is None
    captions = read(project / "edit/caption-profile.json")
    assert captions["coordinate_space"] == "world"
    assert captions["active_indicator"] == "hand-drawn-short-brackets"


@pytest.mark.parametrize("recipe", RECIPE_IDS)
def test_each_recipe_initializes_without_model_dependencies(tmp_path, recipe):
    project = create(tmp_path / "projects", "2026-11-11", recipe, "Synthetic", "test", recipe=recipe)
    assert validate(project) == []
    review = read(project / "verification/review-plan.json")
    assert review["coverage"]["selected"] == []
    assert review["enforcement"] == "review-plan-only; generic-delivery-gate-not-implemented"


def test_existing_project_is_never_overwritten(project):
    before = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    with pytest.raises(FileExistsError):
        create(project.parent.parent, "2026-11-11", "synthetic", "Changed", "test", recipe="abstract-emotion")
    after = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    assert after == before


def test_invalid_recipe_has_no_filesystem_side_effect(tmp_path):
    root = tmp_path / "projects"
    with pytest.raises(ValueError, match="unknown recipe"):
        create(root, "2026-11-11", "demo", "Demo", "test", recipe="../escape")
    assert not root.exists()


def test_manifest_paths_cannot_escape(project):
    manifest = read(project / "project.json")
    manifest["artifacts"]["bad"] = "../../outside.json"
    write(project / "project.json", manifest)
    assert any("escapes project" in issue for issue in validate(project))


def test_timeline_coverage_and_caption_boundaries(project):
    manifest = read(project / "project.json")
    manifest.update(status="production", delivery={"frames": 24, "fps": 24})
    manifest["audio"]["duration_seconds"] = 1.0
    manifest["artifacts"].update(edit_timeline="edit/timeline.json", caption_timing="edit/cues.json")
    write(project / "project.json", manifest)
    files = [{"id": "audio", "source": "audio.wav", "path": "media/audio.wav", "bytes": 0, "sha256": "0" * 64, "profiles": ["all"]},
             {"id": "clip", "source": "clip.mp4", "path": "media/clip.mp4", "bytes": 0, "sha256": "1" * 64, "profiles": ["all"]}]
    write(project / "media.manifest.json", {"version": 1, "files": files})
    timeline = {"total_frames": 24, "fps": 24, "audio": {"source": "audio.wav"}, "entries": [
        {"id": "a", "timeline_in_frames": 0, "duration_frames": 12, "source": "clip.mp4", "prepared_source": "clip.mp4"},
        {"id": "b", "timeline_in_frames": 12, "duration_frames": 12, "source": "clip.mp4", "prepared_source": "clip.mp4"}]}
    cues = {"cue_count": 1, "cues": [{"id": "synthetic-cue", "start_frame": 0, "end_frame": 24}]}
    write(project / "edit/timeline.json", timeline)
    write(project / "edit/cues.json", cues)
    assert validate(project) == []
    # A physical source can be registered once and deliberately referenced twice.
    broken = copy.deepcopy(timeline)
    broken["entries"][1]["timeline_in_frames"] = 13
    write(project / "edit/timeline.json", broken)
    assert any("gap or overlap" in issue for issue in validate(project))
    write(project / "edit/timeline.json", timeline)
    cues["cues"][0]["end_frame"] = 25
    write(project / "edit/cues.json", cues)
    assert any("invalid caption interval" in issue for issue in validate(project))
