"""Legacy layout migration removes aliases after verified canonicalization."""
from pathlib import Path

from cinema_lab.layout import migrate


def put(root, name, data=b"synthetic"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_verified_copy_removes_legacy_and_preserves_archive(tmp_path):
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
    assert not source.exists()
    assert not (tmp_path / ".local").exists()
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


def test_stale_compatibility_links_are_removed(tmp_path):
    canonical = tmp_path / "projects"
    canonical.mkdir(parents=True)
    legacy = tmp_path / ".local"
    legacy.mkdir()
    (legacy / "projects").symlink_to("../projects", target_is_directory=True)
    (legacy / "audio").symlink_to("../library/legacy/audio", target_is_directory=True)
    (tmp_path / "library/legacy/audio").mkdir(parents=True)
    result = migrate(tmp_path, apply=True)
    assert result["status"] == "complete"
    assert not legacy.exists()
    assert not (tmp_path / ".local").is_symlink()
