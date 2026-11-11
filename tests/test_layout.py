"""Migration must preserve originals, reject conflicts and retain old paths."""
from pathlib import Path

from cinema_lab.layout import migrate


def put(root, name, data=b"synthetic"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_verified_copy_merges_projects_and_keeps_compatibility(tmp_path):
    source = put(tmp_path, ".local/projects/2026-11-11/demo/new.txt")
    existing = put(tmp_path, "projects/2026-11-11/demo/existing.txt", b"existing")
    link = source.with_name("reference.txt")
    link.symlink_to(source)
    plan = migrate(tmp_path)
    assert plan["conflicts"] == []
    assert not (tmp_path / "archive").exists()
    result = migrate(tmp_path, apply=True)
    assert result["status"] == "complete"
    assert existing.read_bytes() == b"existing"
    assert source.read_bytes() == b"synthetic"
    assert (tmp_path / ".local/projects").is_symlink()
    original = tmp_path / result["archive"] / "original-local/projects/2026-11-11/demo/new.txt"
    assert original.read_bytes() == b"synthetic"
    assert (tmp_path / "projects/2026-11-11/demo/reference.txt").resolve() == (tmp_path / "projects/2026-11-11/demo/new.txt")
    assert migrate(tmp_path, apply=True)["already_migrated"] is True


def test_collision_leaves_both_versions_untouched(tmp_path):
    source = put(tmp_path, ".local/projects/2026-11-11/demo/same.txt", b"old")
    target = put(tmp_path, "projects/2026-11-11/demo/same.txt", b"new")
    result = migrate(tmp_path, apply=True)
    assert result["conflicts"]
    assert source.read_bytes() == b"old" and target.read_bytes() == b"new"
    assert not (tmp_path / "archive").exists()


def test_unknown_local_data_is_not_silently_abandoned(tmp_path):
    put(tmp_path, ".local/unrecognized/input.txt")
    result = migrate(tmp_path, apply=True)
    assert result["conflicts"]
    assert not (tmp_path / "archive").exists()
