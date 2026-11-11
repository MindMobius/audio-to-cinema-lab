"""Exercise publication boundaries against disposable Git indexes."""
from pathlib import Path
import runpy
import subprocess

import pytest

GUARD = runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools/check_public_tree.py"))
check_index = GUARD["check_index"]


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def put(repo, name, content=b"synthetic fixture\n"):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init")
    put(tmp_path, ".gitignore", b".local/\nprojects/\n*.mp4\n.env\n")
    put(tmp_path, "README.md")
    git(tmp_path, "add", ".gitignore", "README.md")
    return tmp_path


def test_ignored_local_production_is_not_read_or_rejected(repository):
    put(repository, ".local/projects/2026-11-11/sample/project.json")
    put(repository, "projects/2026-11-11/sample/edit/timeline.json")
    put(repository, ".env")
    put(repository, "docs/untracked.mp4")
    assert check_index(repository) == []


@pytest.mark.parametrize("name", [
    ".local/projects/2026-11-11/sample/project.json",
    "projects/2026-11-11/sample/concept/notes.md",
    "source/music/notes.txt",
    "docs/projects/2026-11-11/sample/notes.md",
    "docs/export.MP4", "docs/audio.flac", "docs/lyrics.lrc", "docs/captions.srt",
    "src/weights.safetensors", "tools/project.json", "tools/workflow.api.json",
    "tools/import_project.py", ".env", "docs/.env.example",
])
def test_forced_addition_cannot_bypass_publication_policy(repository, name):
    put(repository, name)
    git(repository, "add", "-f", "--", name)
    issues = check_index(repository)
    assert any(repr(name) in issue for issue in issues)


def test_generic_schemas_recipes_and_synthetic_examples_are_allowed(repository):
    names = ["src/cinema_lab/resources/schemas/project.schema.json",
             "src/cinema_lab/resources/recipes/example.json",
             "tests/fixtures/synthetic-metadata.json", ".env.example"]
    for name in names:
        put(repository, name)
    git(repository, "add", "--", *names)
    assert check_index(repository) == []


def test_symlink_cannot_publish_a_local_project_reference(repository):
    put(repository, ".local/private.md")
    (repository / "docs").mkdir()
    (repository / "docs/reference.md").symlink_to("../.local/private.md")
    git(repository, "add", "docs/reference.md")
    assert any("symlinks" in issue for issue in check_index(repository))


def test_size_check_reads_staged_blob_not_replacement_on_disk(repository):
    path = put(repository, "docs/oversized.md", b"x" * (GUARD["MAX_BLOB_BYTES"] + 1))
    git(repository, "add", "docs/oversized.md")
    path.write_text("small working copy\n")
    assert any("staged blob exceeds" in issue for issue in check_index(repository))
    git(repository, "add", "docs/oversized.md")
    path.write_bytes(b"x" * (GUARD["MAX_BLOB_BYTES"] + 1))
    assert check_index(repository) == []
