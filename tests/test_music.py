"""Music identity, cache reuse and immutable project-input boundary tests."""
import json
from pathlib import Path
import wave

import pytest

from cinema_lab.cli import main
from cinema_lab.io import digest, load
from cinema_lab.music import MusicLibrary
from cinema_lab.project import create, validate
from test_ncm import _make_ncm


def make_wave(path: Path, frames=8000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\0\0" * frames)


@pytest.fixture
def library(tmp_path):
    source = tmp_path / "source/music"
    make_wave(source / "Artist - Song.wav")
    (source / "Artist - Song.lrc").write_text("[00:00.50]Synthetic cue\n")
    library = MusicLibrary(tmp_path)
    library.scan()
    return library


def test_scan_deduplicates_content_and_preserves_versions(library):
    source = library.root / "source/music/Artist - Song.wav"
    original_id = library.list_assets()[0]["id"]
    renamed = source.with_name("Renamed.wav")
    renamed.write_bytes(source.read_bytes())
    assert library.scan()["present_assets"] == 1
    source.unlink()
    library.scan()
    assert library.list_assets()[0]["id"] == original_id
    make_wave(renamed, frames=16000)
    assert library.scan()["catalog_assets"] == 2
    assert library.read()["assets"][original_id]["source_present"] is False


def test_ready_cache_is_reused_without_reprocessing(library, monkeypatch):
    first = library.prepare("Song")
    monkeypatch.setattr("cinema_lab.music.probe_audio", lambda _: pytest.fail("should not reprobe a verified ready asset"))
    second = library.prepare("Song")
    assert second["reused"] is True
    assert first["audio"] == second["audio"]
    assert len(list((library.directory / first["asset_id"] / "audio").iterdir())) == 1


def test_corrupt_cache_is_not_silently_replaced(library):
    first = library.prepare("Song")
    cached = library.root / first["audio"]["path"]
    cached.write_bytes(b"modified")
    with pytest.raises(ValueError, match="missing or changed"):
        library.prepare("Song")
    assert cached.read_bytes() == b"modified"
    assert library.list_assets()[0]["state"] == "corrupt"
    assert library.audit()["ok"] is False


def test_bind_pins_lyrics_and_keeps_existing_project_stable(library):
    project = create(library.root / "projects", "2026-11-11", "demo", "Synthetic", "test")
    selected = library.bind("Song", project)
    assert validate(project) == []
    original = (project / selected["lyrics"]["path"]).read_bytes()
    (library.root / "source/music/Artist - Song.lrc").write_text("[00:01.00]Changed synthetic cue\n")
    library.scan()
    assert (project / selected["lyrics"]["path"]).read_bytes() == original
    with pytest.raises(ValueError, match="already pins"):
        library.bind("Song", project)
    assert library.bind("Song", project, lyrics_sha256=selected["lyrics"]["sha256"]) == selected
    manifest = load(project / "project.json")
    assert manifest["audio"]["source_path"] == selected["audio"]["path"]
    assert manifest["audio"]["lrc_path"] == selected["lyrics"]["path"]
    assert library.usage()[selected["asset_id"]] == ["projects/2026-11-11/demo"]
    assert library.audit()["ok"] is True


def test_bind_refuses_an_existing_different_audio_master(library):
    project = create(library.root / "projects", "2026-11-11", "demo", "Synthetic", "test")
    manifest = load(project / "project.json")
    manifest["audio"]["sha256"] = "f" * 64
    (project / "project.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="differs"):
        library.bind("Song", project)
    assert not (project / "audio/music-selection.json").exists()


def test_multiple_current_lyrics_need_explicit_selection(library):
    source = library.root / "source/music"
    (source / "Other.wav").write_bytes((source / "Artist - Song.wav").read_bytes())
    (source / "Other.lrc").write_text("[00:00.10]Alternative synthetic cue\n")
    library.scan()
    project = create(library.root / "projects", "2026-11-11", "demo", "Synthetic", "test")
    with pytest.raises(ValueError, match="multiple lyric"):
        library.bind("Song", project)
    assert not (project / "audio/music-selection.json").exists()


def test_tampering_with_pinned_audio_fails_project_validation(library):
    project = create(library.root / "projects", "2026-11-11", "demo", "Synthetic", "test")
    selected = library.bind("Song", project)
    (project / selected["audio"]["path"]).write_bytes(b"different")
    assert any("pinned music audio" in error for error in validate(project))
    with pytest.raises(ValueError, match="missing or changed"):
        library.bind("Song", project)


def test_changed_source_cannot_be_decoded_under_previous_id(library):
    make_wave(library.root / "source/music/Artist - Song.wav", frames=16000)
    with pytest.raises(ValueError, match="source missing or changed"):
        library.prepare("Song")
    assert library.list_assets()[0]["state"] == "failed"


def test_ambiguous_title_does_not_choose_arbitrarily(library):
    make_wave(library.root / "source/music/Other Artist - Song.wav", frames=16000)
    library.scan()
    with pytest.raises(ValueError, match="2 matches"):
        library.prepare("Song")


def test_native_ncm_decode_runs_once_and_preserves_source(tmp_path, monkeypatch):
    source = tmp_path / "source/music"
    source.mkdir(parents=True)
    ncm = source / "Synthetic.ncm"
    expected, _, _ = _make_ncm(ncm)
    original_hash = digest(ncm)
    # The NCM fixture intentionally contains synthetic MP3 bytes, not a real recording.
    monkeypatch.setattr("cinema_lab.music.probe_audio", lambda _: {"duration_seconds": 1, "sample_rate": 8000, "channels": 1})
    library = MusicLibrary(tmp_path)
    library.scan()
    prepared = library.prepare("测试歌曲")
    assert (tmp_path / prepared["audio"]["path"]).read_bytes() == expected
    assert digest(ncm) == original_hash
    monkeypatch.setattr("cinema_lab.music.decode_file", lambda *a, **k: pytest.fail("NCM must not decode twice"))
    assert library.prepare("测试歌曲")["reused"] is True


def test_cli_init_selects_catalog_music(library, monkeypatch):
    monkeypatch.chdir(library.root)
    assert main(["init", "--date", "2026-11-11", "--slug", "demo", "--title", "Demo", "--music", "Song"]) == 0
    assert validate(library.root / "projects/2026-11-11/demo") == []


def test_legacy_receipt_rejects_modified_output(tmp_path):
    from cinema_lab.ncm import decode_many
    source = tmp_path / "source/music"
    source.mkdir(parents=True)
    ncm = source / "Synthetic.ncm"
    _make_ncm(ncm)
    receipt = tmp_path / "old/receipt.json"
    decoded = decode_many([ncm], tmp_path / "old/decoded", receipt=receipt)
    Path(decoded["outputs"][0]["output"]).write_bytes(b"changed")
    library = MusicLibrary(tmp_path)
    library.scan()
    with pytest.raises(ValueError, match="does not match receipt"):
        library.import_receipt(receipt)


def test_cli_external_workspace_does_not_create_projects_in_cwd(library, monkeypatch, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    assert main(["init", "--workspace", str(library.root), "--date", "2026-11-11", "--slug", "remote-cwd",
                 "--title", "Synthetic", "--music", "Song"]) == 0
    assert not (other / "projects").exists()
    assert validate(library.root / "projects/2026-11-11/remote-cwd") == []
    assert main(["music", "--workspace", str(library.root), "bind", "Song", "projects/2026-11-11/remote-cwd"]) == 0


def test_missing_selection_does_not_leave_an_empty_project(library, monkeypatch):
    monkeypatch.chdir(library.root)
    assert main(["init", "--date", "2026-11-11", "--slug", "missing", "--title", "Synthetic", "--music", "missing-song"]) == 2
    assert not (library.root / "projects/2026-11-11/missing").exists()


def test_failed_probe_preserves_source_and_records_failure(library, monkeypatch):
    original = digest(library.root / "source/music/Artist - Song.wav")
    def fail(_):
        raise ValueError("synthetic probe failure")
    monkeypatch.setattr("cinema_lab.music.probe_audio", fail)
    with pytest.raises(ValueError, match="probe failure"):
        library.prepare("Song")
    assert digest(library.root / "source/music/Artist - Song.wav") == original
    assert library.list_assets()[0]["state"] == "failed"
    assert not list(library.directory.glob("*/audio/*"))


def test_binding_cannot_follow_input_symlink_outside_project(library, tmp_path):
    project = create(library.root / "projects", "2026-11-11", "demo", "Synthetic", "test")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (project / "audio/inputs").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable")
        raise
    with pytest.raises(ValueError, match="symlink escapes"):
        library.bind("Song", project)
    assert list(outside.iterdir()) == []
