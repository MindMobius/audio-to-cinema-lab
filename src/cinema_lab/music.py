"""Local music catalog, immutable prepared assets and pinned project inputs."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from filelock import FileLock
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

from .io import copy_verified, digest, inside, load, matches
from .ncm import UPSTREAM, decode_file, inspect_file

AUDIO_EXTENSIONS = {".ncm", ".mp3", ".flac", ".m4a", ".wav", ".ogg", ".opus", ".aac", ".aiff"}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".writing-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def probe_audio(path: Path) -> dict:
    """Measure a playable file; container metadata alone is not a successful decode."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_streams", "-show_format",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=90,
    )
    if result.returncode:
        raise ValueError(f"ffprobe could not read audio: {path.name}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise ValueError(f"no audio stream: {path.name}")
    stream = streams[0]
    duration = float(data.get("format", {}).get("duration") or stream.get("duration") or 0)
    if duration <= 0:
        raise ValueError(f"audio duration is not positive: {path.name}")
    return {"duration_seconds": duration, "sample_rate": int(stream["sample_rate"]),
            "channels": int(stream["channels"]), "codec": stream.get("codec_name"),
            "tags": data.get("format", {}).get("tags", {})}


class MusicLibrary:
    def __init__(self, workspace: Path):
        self.root = workspace.expanduser().resolve()
        self.directory = inside(self.root, "library/music")
        self.index_path = self.directory / "index.json"

    @contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.directory / ".lock")):
            yield

    def read(self) -> dict:
        if not self.index_path.exists():
            return {"version": 1, "source_root": "source/music", "assets": {}}
        data = load(self.index_path)
        if data.get("version") != 1 or not isinstance(data.get("assets"), dict):
            raise ValueError("unsupported music index; preserve it and rebuild explicitly")
        return data

    def save(self, index: dict) -> None:
        index["updated_at"] = timestamp()
        atomic_json(self.index_path, index)

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def record(self, path: Path) -> dict:
        return {"path": self.relative(path), "bytes": path.stat().st_size, "sha256": digest(path)}

    def verify(self, record: dict) -> Path:
        path = inside(self.root, record["path"])
        if not matches(path, record):
            raise ValueError(f"missing or changed asset: {record['path']}")
        return path

    def choose(self, index: dict, selector: str) -> dict:
        assets = list(index["assets"].values())
        if selector in index["assets"]:
            return index["assets"][selector]
        query = selector.casefold()
        exact = [a for a in assets if query in {a["title"].casefold(), *(Path(p).name.casefold() for p in a["source_paths"])}]
        found = exact or [a for a in assets if a["id"].startswith(selector)
                          or query in (a["title"] + " " + " ".join(a["artists"])).casefold()]
        if len(found) != 1:
            choices = ", ".join(a["id"][:22] + " " + a["title"] for a in found)
            raise ValueError(f"select exactly one asset ({len(found)} matches): {choices}")
        return found[0]

    def scan(self) -> dict:
        source = inside(self.root, "source/music")
        if not source.is_dir():
            raise ValueError("source/music does not exist")
        with self.locked():
            index = self.read()
            for asset in index["assets"].values():
                asset["source_present"] = False
                asset["source_paths"] = []
                asset["lyrics_candidates"] = []
            errors, scanned = [], 0
            for path in sorted(source.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                    continue
                relative = self.relative(path)
                inside(self.root, relative)
                fingerprint = digest(path)
                asset_id = "music-" + fingerprint
                scanned += 1
                asset = index["assets"].get(asset_id)
                if asset is None:
                    artist, separator, title = path.stem.partition(" - ")
                    asset = {"id": asset_id, "source_sha256": fingerprint,
                             "source_bytes": path.stat().st_size, "source_format": path.suffix.lower()[1:],
                             "title": title if separator else path.stem, "artists": [artist] if separator else [],
                             "metadata_origin": "filename", "created_at": timestamp(),
                             "source_paths": [], "source_history": [], "lyrics_candidates": [],
                             "lyrics_versions": {}, "preparation": {"state": "pending"}}
                    if path.suffix.lower() == ".ncm":
                        inspection = inspect_file(path)
                        asset["ncm_profile"] = inspection.profile
                        if inspection.metadata:
                            asset.update(title=inspection.metadata.title or asset["title"],
                                         artists=list(inspection.metadata.artists) or asset["artists"],
                                         album=inspection.metadata.album, metadata_origin="ncm")
                        if not inspection.convertible:
                            asset["preparation"] = {"state": "failed", "error": inspection.detail}
                            errors.append({"source": relative, "error": inspection.detail})
                    index["assets"][asset_id] = asset
                asset["source_present"] = True
                asset["source_paths"].append(relative)
                if relative not in asset["source_history"]:
                    asset["source_history"].append(relative)
                for lyric in sorted(path.parent.iterdir()):
                    if lyric.is_file() and lyric.stem == path.stem and lyric.suffix.lower() == ".lrc":
                        original = self.record(lyric)
                        snapshot = inside(self.directory, f"{asset_id}/lyrics/{original['sha256']}.lrc")
                        copy_verified(lyric, snapshot, original)
                        version = {**self.record(snapshot), "original_path": original["path"],
                                   "timing_policy": "preserve-source; no-automatic-shift"}
                        asset["lyrics_versions"][version["sha256"]] = version
                        if version["sha256"] not in asset["lyrics_candidates"]:
                            asset["lyrics_candidates"].append(version["sha256"])
                if asset["preparation"]["state"] == "ready":
                    try:
                        self.verify(asset["preparation"]["audio"])
                    except ValueError as error:
                        asset["preparation"].update(state="corrupt", error=str(error))
            self.save(index)
            return {"scanned_files": scanned, "present_assets": sum(a["source_present"] for a in index["assets"].values()),
                    "catalog_assets": len(index["assets"]), "errors": errors}

    def current_source(self, asset: dict) -> Path:
        for relative in asset["source_paths"]:
            path = inside(self.root, relative)
            if path.is_file() and digest(path) == asset["source_sha256"]:
                return path
        raise ValueError("source missing or changed; run music scan before preparing this version")

    def install_prepared(self, asset: dict, source: Path, method: dict, cover: Path | None = None) -> dict:
        record = self.record(source)
        measurement = probe_audio(source)
        target = inside(self.directory, f"{asset['id']}/audio/{record['sha256']}{source.suffix.lower()}")
        copy_verified(source, target, record)
        prepared = {"state": "ready", "audio": self.record(target), "measurement": measurement,
                    "method": method, "prepared_at": timestamp(), "source_sha256": asset["source_sha256"]}
        if cover is not None:
            cover_record = self.record(cover)
            dst = inside(self.directory, f"{asset['id']}/covers/{cover_record['sha256']}{cover.suffix.lower()}")
            copy_verified(cover, dst, cover_record)
            prepared["cover"] = self.record(dst)
        receipt = inside(self.directory, f"{asset['id']}/receipts/{uuid.uuid4().hex}.json")
        atomic_json(receipt, {"asset_id": asset["id"], **prepared})
        prepared["receipt"] = self.relative(receipt)
        asset["preparation"] = prepared
        return prepared

    def prepare(self, selector: str) -> dict:
        with self.locked():
            index = self.read()
            asset = self.choose(index, selector)
            prepared = asset["preparation"]
            try:
                if prepared["state"] == "ready":
                    self.verify(prepared["audio"])
                    return {"asset_id": asset["id"], "reused": True, **prepared}
                if prepared["state"] == "corrupt":
                    raise ValueError("cached media is corrupt; restore its recorded bytes before reuse")
                source = self.current_source(asset)
                if source.suffix.lower() == ".ncm":
                    # Keep staging inside the ignored library; never overwrite originals.
                    with tempfile.TemporaryDirectory(prefix=".decode-", dir=self.directory) as temporary:
                        result = decode_file(source, Path(temporary), include_cover=True)
                        if digest(source) != asset["source_sha256"]:
                            raise ValueError("source changed during NCM decode")
                        prepared = self.install_prepared(asset, result.output,
                            {"adapter": "audio-decoding.ncm", "adapter_version": "0.1.0", "upstream": UPSTREAM}, result.cover)
                else:
                    prepared = self.install_prepared(asset, source, {"adapter": "verified-copy", "transcoded": False})
                    if prepared["audio"]["sha256"] != asset["source_sha256"]:
                        raise ValueError("source changed while preparing audio")
                self.save(index)
                return {"asset_id": asset["id"], "reused": False, **prepared}
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                asset["preparation"] = {**asset["preparation"], "state": "corrupt" if "audio" in asset["preparation"] else "failed", "error": str(error)}
                self.save(index)
                raise

    def import_receipt(self, receipt_path: Path) -> dict:
        receipt = load(receipt_path)
        if receipt.get("adapter") != "audio-decoding.ncm":
            raise ValueError("expected an NCM decode receipt")
        inputs = {str(Path(i["path"]).resolve()): i for i in receipt["inputs"]}
        imported, skipped = [], []
        with self.locked():
            index = self.read()
            for item in receipt["outputs"]:
                original = inputs.get(str(Path(item["source"]).resolve()))
                asset = index["assets"].get("music-" + original["sha256"]) if original else None
                if asset is None or item.get("outcome") != "WRITTEN":
                    skipped.append(item["source"])
                    continue
                self.current_source(asset)
                output = Path(item["output"]).resolve()
                if not output.is_file() or digest(output) != item.get("output_sha256"):
                    raise ValueError(f"legacy output does not match receipt: {output.name}")
                if asset["preparation"]["state"] == "ready":
                    self.verify(asset["preparation"]["audio"])
                    continue
                cover = Path(item["cover"]).resolve() if item.get("cover") else None
                if cover is not None and (not cover.is_file() or digest(cover) != item.get("cover_sha256")):
                    raise ValueError("legacy cover does not match receipt")
                self.install_prepared(asset, output, {"adapter": "verified-legacy-ncm-output", "upstream": receipt.get("upstream"),
                                                     "receipt_sha256": digest(receipt_path)}, cover)
                imported.append(asset["id"])
                self.save(index)
        return {"imported": imported, "skipped_sources": skipped}

    def bind(self, selector: str, project: Path, *, lyrics_sha256: str | None = None) -> dict:
        project = project.expanduser()
        if not project.is_absolute():
            project = self.root / project
        project = project.resolve()
        relative = project.relative_to(self.root).as_posix()
        if not relative.startswith("projects/") or len(Path(relative).parts) != 3 or not project.is_dir():
            raise ValueError("project must be an existing projects/YYYY-MM-DD/slug directory")
        if date.fromisoformat(project.parent.name).isoformat() != project.parent.name:
            raise ValueError("project date must be YYYY-MM-DD")
        prepared = self.prepare(selector)
        with self.locked():
            index = self.read()
            asset = self.choose(index, prepared["asset_id"])
            candidates = asset["lyrics_candidates"]
            if lyrics_sha256 is None:
                if len(candidates) > 1:
                    raise ValueError("multiple lyric versions: select one explicitly with --lyrics-sha256")
                lyrics_sha256 = candidates[0] if candidates else None
            lyric = asset["lyrics_versions"].get(lyrics_sha256) if lyrics_sha256 else None
            if lyrics_sha256 and lyric is None:
                raise ValueError("lyric version does not belong to this audio asset")
            selection_path = inside(project, "audio/music-selection.json")
            manifest_path = inside(project, "project.json")
            manifest = load(manifest_path) if manifest_path.exists() else None
            if manifest:
                existing_hash = manifest.get("audio", {}).get("sha256") or manifest.get("source_audio_sha256")
                if existing_hash and existing_hash != prepared["audio"]["sha256"]:
                    raise ValueError("selected audio differs from the project's recorded master; create a new revision")
            if selection_path.exists():
                old = load(selection_path)
                if old["asset_id"] != asset["id"] or old["audio"]["sha256"] != prepared["audio"]["sha256"] or old.get("lyrics", {}).get("sha256") != lyrics_sha256:
                    raise ValueError("project already pins another audio or lyric version; preserve it and create a new revision")
                self.verify({**old["audio"], "path": relative + "/" + old["audio"]["path"]})
                if old.get("lyrics"):
                    self.verify({**old["lyrics"], "path": relative + "/" + old["lyrics"]["path"]})
                self.update_manifest(manifest_path, manifest, old)
                return old
            source = self.verify(prepared["audio"])
            target = inside(project, "audio/inputs/" + source.name)
            copy_verified(source, target, prepared["audio"])
            selection = {"version": 1, "asset_id": asset["id"], "source_sha256": asset["source_sha256"],
                         "title": asset["title"], "artists": asset["artists"], "selected_at": timestamp(),
                         "library_audio": prepared["audio"], "audio": {**prepared["audio"], "path": target.relative_to(project).as_posix()},
                         "measurement": prepared["measurement"], "timing_policy": "preserve-source; no-automatic-shift"}
            if lyric:
                source_lyric = self.verify(lyric)
                target_lyric = inside(project, "audio/inputs/" + source_lyric.name)
                copy_verified(source_lyric, target_lyric, lyric)
                selection["lyrics"] = {**lyric, "path": target_lyric.relative_to(project).as_posix()}
            atomic_json(selection_path, selection)
            self.update_manifest(manifest_path, manifest, selection)
            return selection

    @staticmethod
    def update_manifest(path: Path, manifest: dict | None, selection: dict) -> None:
        if manifest is None:
            return
        audio = manifest.setdefault("audio", {})
        audio.update({
            "role": "song",
            "source_policy": "private-local",
            "library_asset_id": selection["asset_id"],
            "sha256": selection["audio"]["sha256"],
            "source_path": selection["audio"]["path"],
            "duration_seconds": selection["measurement"]["duration_seconds"],
            "sample_rate": selection["measurement"]["sample_rate"],
            "channels": selection["measurement"]["channels"],
        })
        if selection.get("lyrics"):
            audio["lrc_path"] = selection["lyrics"]["path"]
        manifest.setdefault("artifacts", {})["music_selection"] = "audio/music-selection.json"
        atomic_json(path, manifest)

    def usage(self) -> dict:
        usage = {}
        for path in sorted((self.root / "projects").glob("*/*/audio/music-selection.json")):
            selection = load(path)
            usage.setdefault(selection["asset_id"], []).append(self.relative(path.parent.parent))
        return usage

    def list_assets(self, query: str = "") -> list[dict]:
        usage = self.usage()
        return [{"id": a["id"], "title": a["title"], "artists": a["artists"], "format": a["source_format"],
                 "state": a["preparation"]["state"], "source_present": a["source_present"],
                 "lyric_versions": len(a["lyrics_versions"]), "projects": usage.get(a["id"], [])}
                for a in self.read()["assets"].values()
                if query.casefold() in (a["title"] + " " + " ".join(a["artists"])).casefold()]

    def audit(self) -> dict:
        errors, checked = [], 0
        index = self.read()
        for asset in index["assets"].values():
            records = list(asset["lyrics_versions"].values())
            if asset["preparation"].get("cover"):
                records.append(asset["preparation"]["cover"])
            if asset["preparation"].get("audio"):
                records.append(asset["preparation"]["audio"])
            for record in records:
                checked += 1
                try:
                    self.verify(record)
                except ValueError as error:
                    errors.append(str(error))
        for path in sorted((self.root / "projects").glob("*/*/audio/music-selection.json")):
            selection = load(path)
            for key in ["audio", "lyrics"]:
                if key in selection:
                    checked += 1
                    try:
                        project = path.parent.parent
                        record = selection[key]
                        target = inside(project, record["path"])
                        if not matches(target, record):
                            raise ValueError(f"project input changed: {self.relative(target)}")
                    except ValueError as error:
                        errors.append(str(error))
        return {"ok": not errors, "checked": checked, "errors": errors}
