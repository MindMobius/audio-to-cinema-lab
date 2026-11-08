"""Decode locally supplied classic NetEase Cloud Music NCM containers.

The container and key-stream steps follow the classic NCM implementation in
KaffuAlcaid/ncmBreaker 0.4.1.  The adapter is deliberately small and local:
it does not authenticate, download tracks or alter the source container.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


MAGIC = b"CTENFDAM"
CORE_KEY = b"hzHRAmso5kInbaxW"
METADATA_KEY = b"#14ljk_!\\]&0U<'("
KEY_PREFIX = b"neteasecloudmusic"
METADATA_PREFIX = b"163 key(Don't modify):"
JSON_PREFIX = b"music:"
BUFFER_SIZE = 1024 * 1024
MAX_CONTAINER_BLOCK = 64 * 1024 * 1024

UPSTREAM = {
    "name": "NCM Breaker",
    "version": "0.4.1",
    "commit": "8e86dc6a0ff71fd60785ae38eed23efb2f3e9253",
    "license": "MIT",
    "repository": "https://github.com/KaffuAlcaid/ncmBreaker",
}


class NcmError(ValueError):
    """An NCM container could not be inspected or decoded."""

    def __init__(self, message: str, profile: str = "damaged") -> None:
        super().__init__(message)
        self.profile = profile


@dataclass(frozen=True)
class NcmMetadata:
    title: str = ""
    artists: tuple[str, ...] = ()
    album: str = ""
    declared_format: str = ""
    raw_json: str = ""

    @property
    def artist_display(self) -> str:
        return ", ".join(self.artists)

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "artists": list(self.artists),
            "artist_display": self.artist_display,
            "album": self.album,
            "declared_format": self.declared_format,
            "raw_json": self.raw_json,
        }


@dataclass(frozen=True)
class _ParsedNcm:
    marker: bytes
    stream_key: bytes
    metadata: NcmMetadata
    cover_offset: int
    cover_size: int
    cover_frame_size: int
    cover_format: str
    audio_offset: int
    audio_size: int


@dataclass(frozen=True)
class NcmInspection:
    source: Path
    profile: str
    marker: str = ""
    audio_format: str = "unknown"
    cover_format: str = "none"
    cover_size: int = 0
    audio_size: int = 0
    source_size: int = 0
    metadata: NcmMetadata | None = None
    detail: str = ""

    @property
    def convertible(self) -> bool:
        return self.profile == "CLASSIC_NCM" and self.audio_format in {"mp3", "flac"}

    def as_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "profile": self.profile,
            "marker": self.marker,
            "audio_format": self.audio_format,
            "cover_format": self.cover_format,
            "cover_size": self.cover_size,
            "audio_size": self.audio_size,
            "source_size": self.source_size,
            "metadata": self.metadata.as_dict() if self.metadata else None,
            "detail": self.detail,
            "convertible": self.convertible,
        }


@dataclass(frozen=True)
class NcmDecodeResult:
    source: Path
    output: Path
    audio_format: str
    audio_bytes: int
    metadata: NcmMetadata
    outcome: str
    output_sha256: str | None = None
    cover: Path | None = None
    cover_sha256: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "output": str(self.output),
            "audio_format": self.audio_format,
            "audio_bytes": self.audio_bytes,
            "metadata": self.metadata.as_dict(),
            "outcome": self.outcome,
            "output_sha256": self.output_sha256,
            "cover": str(self.cover) if self.cover else None,
            "cover_sha256": self.cover_sha256,
        }


def collect_ncm_files(inputs: Sequence[Path]) -> list[Path]:
    """Collect unique NCM files in deterministic order."""
    found: dict[Path, None] = {}
    for raw in inputs:
        path = raw.expanduser().resolve()
        if not path.exists():
            raise NcmError(f"input does not exist: {raw}")
        if path.is_dir():
            candidates = path.rglob("*")
        elif path.is_file():
            candidates = (path,)
        else:
            raise NcmError(f"input is not a regular file or directory: {raw}")
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() == ".ncm":
                found[candidate.resolve()] = None
    return sorted(found, key=lambda item: item.as_posix())


def inspect_file(source: Path) -> NcmInspection:
    """Inspect one container without writing decoded media."""
    source = source.expanduser().resolve()
    try:
        parsed = _parse_container(source)
        with source.open("rb") as handle:
            header = _read_decrypted_header(handle, parsed)
        audio_format = detect_audio_format(header)
        detail = (
            "经典 NCM 容器"
            if audio_format != "unknown"
            else "经典容器可解析，但音频负载格式不受支持"
        )
        return NcmInspection(
            source=source,
            profile="CLASSIC_NCM",
            marker=parsed.marker.hex(" ").upper(),
            audio_format=audio_format,
            cover_format=parsed.cover_format,
            cover_size=parsed.cover_size,
            audio_size=parsed.audio_size,
            source_size=source.stat().st_size,
            metadata=parsed.metadata,
            detail=detail,
        )
    except NcmError as exc:
        return NcmInspection(
            source=source,
            profile=exc.profile,
            source_size=_file_size(source),
            detail=str(exc),
        )
    except OSError as exc:
        return NcmInspection(
            source=source,
            profile="DAMAGED",
            source_size=_file_size(source),
            detail=str(exc),
        )


def decode_file(
    source: Path,
    output_directory: Path,
    *,
    conflict_policy: str = "rename",
    include_cover: bool = False,
) -> NcmDecodeResult:
    """Decode one NCM file into a playable MP3 or FLAC output."""
    if conflict_policy not in {"rename", "skip", "overwrite"}:
        raise ValueError(f"unknown conflict policy: {conflict_policy}")

    source = source.expanduser().resolve()
    output_directory = output_directory.expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    parsed = _parse_container(source)
    with source.open("rb") as handle:
        header = _read_decrypted_header(handle, parsed)
    audio_format = detect_audio_format(header)
    if audio_format == "unknown":
        raise NcmError("不支持的音频负载格式", profile="UNSUPPORTED_VARIANT")

    target = _resolve_target(output_directory, source.stem, audio_format, conflict_policy)
    if target is None:
        return NcmDecodeResult(
            source=source,
            output=output_directory / f"{source.stem}.{audio_format}",
            audio_format=audio_format,
            audio_bytes=0,
            metadata=parsed.metadata,
            outcome="SKIPPED",
        )

    temporary: Path | None = None
    cover_target: Path | None = None
    cover_sha256: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output_directory, prefix=".ncm-decode-", suffix=".part", delete=False
        ) as handle:
            temporary = Path(handle.name)
            _decode_audio_stream(source, parsed, handle)
        _commit(temporary, target, overwrite=conflict_policy == "overwrite")
        temporary = None

        if include_cover and parsed.cover_size and parsed.cover_format in {"jpeg", "png"}:
            cover_ext = "jpg" if parsed.cover_format == "jpeg" else "png"
            cover_target = _resolve_target(output_directory, f"{source.stem}.cover", cover_ext, conflict_policy)
            if cover_target is not None:
                cover_temporary: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="wb", dir=output_directory, prefix=".ncm-cover-", suffix=".part", delete=False
                    ) as cover_handle:
                        cover_temporary = Path(cover_handle.name)
                        with source.open("rb") as source_handle:
                            source_handle.seek(parsed.cover_offset)
                            _copy_exact(source_handle, cover_handle, parsed.cover_size, "封面")
                    _commit(cover_temporary, cover_target, overwrite=conflict_policy == "overwrite")
                    cover_temporary = None
                    cover_sha256 = sha256(cover_target)
                finally:
                    if cover_temporary is not None:
                        cover_temporary.unlink(missing_ok=True)
        return NcmDecodeResult(
            source=source,
            output=target,
            audio_format=audio_format,
            audio_bytes=parsed.audio_size,
            metadata=parsed.metadata,
            outcome="WRITTEN",
            output_sha256=sha256(target),
            cover=cover_target,
            cover_sha256=cover_sha256,
        )
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def decode_many(
    inputs: Sequence[Path],
    output_directory: Path,
    *,
    conflict_policy: str = "rename",
    include_cover: bool = False,
    receipt: Path | None = None,
) -> dict[str, object]:
    """Decode a batch and write the adapter receipt."""
    started_at = _timestamp()
    started = time.monotonic()
    sources = collect_ncm_files(inputs)
    input_records = [
        {"path": str(source), "bytes": source.stat().st_size, "sha256": sha256(source)}
        for source in sources
    ]
    outputs: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for source in sources:
        try:
            outputs.append(
                decode_file(
                    source,
                    output_directory,
                    conflict_policy=conflict_policy,
                    include_cover=include_cover,
                ).as_dict()
            )
        except (NcmError, OSError, ValueError) as exc:
            failures.append({"source": str(source), "error": str(exc)})

    result: dict[str, object] = {
        "adapter": "audio-decoding.ncm",
        "adapter_version": "0.1.0",
        "implementation": "python-native",
        "upstream": UPSTREAM,
        "started_at": started_at,
        "finished_at": _timestamp(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "inputs": input_records,
        "output_directory": str(output_directory.expanduser().resolve()),
        "conflict_policy": conflict_policy,
        "include_cover": include_cover,
        "outputs": outputs,
        "failures": failures,
        "ok": not failures,
    }
    if receipt is not None:
        _write_json(receipt, result)
        result["receipt"] = str(receipt.expanduser().resolve())
    return result


def detect_audio_format(header: bytes) -> str:
    if header[:3] == b"ID3":
        return "mp3"
    if header[:4] == b"fLaC":
        return "flac"
    if len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0:
        return "mp3"
    return "unknown"


def detect_cover_format(header: bytes) -> str:
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    return "unknown"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_container(source: Path) -> _ParsedNcm:
    if not source.is_file():
        raise NcmError(f"source is not a regular file: {source}")
    source_size = source.stat().st_size
    if source_size < len(MAGIC) + 2:
        raise NcmError("文件短于 NCM 头部")

    with source.open("rb") as handle:
        header = _read_exact(handle, 10, "NCM 头部")
        if header[:8] != MAGIC:
            raise NcmError("固定标识不是 CTENFDAM", profile="NOT_NCM")
        marker = header[8:10]

        encrypted_key = _read_length_prefixed_block(handle, "密钥区")
        try:
            stream_key = _decode_stream_key(encrypted_key)
        except NcmError as exc:
            raise NcmError(str(exc), profile="UNSUPPORTED_VARIANT") from exc

        encrypted_metadata = _read_length_prefixed_block(handle, "元数据区")
        try:
            metadata = _decode_metadata(encrypted_metadata)
        except NcmError as exc:
            raise NcmError(str(exc), profile="UNSUPPORTED_VARIANT") from exc

        _read_exact(handle, 5, "CRC 和保留字段")
        cover_frame_size = _read_u32(handle, "封面帧长度")
        cover_size = _read_u32(handle, "封面长度")
        cover_frame_size = max(cover_frame_size, cover_size)
        cover_offset = handle.tell()
        if cover_frame_size > source_size - cover_offset:
            raise NcmError("封面帧超出文件范围")
        cover_header = b""
        if cover_size:
            cover_header = _read_exact(handle, min(cover_size, 12), "封面")
        cover_format = detect_cover_format(cover_header)
        audio_offset = cover_offset + cover_frame_size
        audio_size = source_size - audio_offset
        if audio_size <= 0:
            raise NcmError("容器中没有音频数据")

    return _ParsedNcm(
        marker=marker,
        stream_key=stream_key,
        metadata=metadata,
        cover_offset=cover_offset,
        cover_size=cover_size,
        cover_frame_size=cover_frame_size,
        cover_format=cover_format,
        audio_offset=audio_offset,
        audio_size=audio_size,
    )


def _decode_stream_key(encrypted_key: bytes) -> bytes:
    decrypted = _aes_decrypt(bytes(value ^ 0x64 for value in encrypted_key), CORE_KEY, "密钥区")
    if not decrypted.startswith(KEY_PREFIX) or len(decrypted) == len(KEY_PREFIX):
        raise NcmError("密钥区明文前缀不匹配")
    return decrypted[len(KEY_PREFIX) :]


def _decode_metadata(encrypted_metadata: bytes) -> NcmMetadata:
    encoded = bytes(value ^ 0x63 for value in encrypted_metadata)
    if not encoded.startswith(METADATA_PREFIX):
        raise NcmError("元数据区前缀不匹配")
    try:
        ciphertext = base64.b64decode(encoded[len(METADATA_PREFIX) :], validate=True)
    except (ValueError, UnicodeError) as exc:
        raise NcmError("元数据区不是有效的 Base64") from exc
    plaintext = _aes_decrypt(ciphertext, METADATA_KEY, "元数据区")
    if not plaintext.startswith(JSON_PREFIX):
        raise NcmError("元数据明文前缀不匹配")
    raw_json = plaintext[len(JSON_PREFIX) :].decode("utf-8")
    try:
        parsed = json.loads(raw_json)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NcmError("元数据 JSON 无法解析") from exc
    if not isinstance(parsed, dict):
        raise NcmError("元数据 JSON 根节点不是对象")
    return NcmMetadata(
        title=_string_value(parsed.get("musicName")),
        artists=_artist_names(parsed.get("artist")),
        album=_string_value(parsed.get("album")),
        declared_format=_string_value(parsed.get("format")).lower(),
        raw_json=raw_json,
    )


def _aes_decrypt(ciphertext: bytes, key: bytes, label: str) -> bytes:
    try:
        decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    except ValueError as exc:
        raise NcmError(f"{label}无法使用经典 AES 密钥解开") from exc


def _audio_keystream(stream_key: bytes) -> bytes:
    if not stream_key:
        raise NcmError("音频流密钥不能为空")
    box = list(range(256))
    swap_index = 0
    for index in range(256):
        swap_index = (swap_index + box[index] + stream_key[index % len(stream_key)]) & 0xFF
        box[index], box[swap_index] = box[swap_index], box[index]
    key_stream = bytearray(256)
    for offset in range(256):
        index = (offset + 1) & 0xFF
        swap_index = (box[index] + index) & 0xFF
        key_stream[offset] = box[(box[index] + box[swap_index]) & 0xFF]
    return bytes(key_stream)


def _decode_audio_stream(source: Path, parsed: _ParsedNcm, output) -> None:
    key_stream = _audio_keystream(parsed.stream_key)
    completed = 0
    with source.open("rb") as handle:
        handle.seek(parsed.audio_offset)
        remaining = parsed.audio_size
        while remaining:
            chunk = handle.read(min(BUFFER_SIZE, remaining))
            if not chunk:
                raise NcmError("音频数据长度与容器记录不一致")
            decoded = bytes(value ^ key_stream[(completed + offset) & 0xFF] for offset, value in enumerate(chunk))
            output.write(decoded)
            completed += len(chunk)
            remaining -= len(chunk)
    if completed != parsed.audio_size:
        raise NcmError("音频数据长度与容器记录不一致")


def _read_decrypted_header(handle, parsed: _ParsedNcm) -> bytes:
    handle.seek(parsed.audio_offset)
    encrypted = _read_exact(handle, min(parsed.audio_size, 16), "音频头部")
    key_stream = _audio_keystream(parsed.stream_key)
    return bytes(value ^ key_stream[offset & 0xFF] for offset, value in enumerate(encrypted))


def _read_length_prefixed_block(handle, label: str) -> bytes:
    length = _read_u32(handle, f"{label}长度")
    if length > MAX_CONTAINER_BLOCK:
        raise NcmError(f"{label}过大，拒绝读取到内存")
    return _read_exact(handle, length, label)


def _read_u32(handle, label: str) -> int:
    raw = _read_exact(handle, 4, label)
    return struct.unpack("<I", raw)[0]


def _read_exact(handle, size: int, label: str) -> bytes:
    if size < 0:
        raise NcmError(f"{label}长度无效")
    try:
        remaining = os.fstat(handle.fileno()).st_size - handle.tell()
    except (AttributeError, OSError):
        remaining = None
    if remaining is not None and size > remaining:
        raise NcmError(f"{label}超出文件范围")
    data = handle.read(size)
    if len(data) != size:
        raise NcmError(f"{label}超出文件范围")
    return data


def _copy_exact(source, target, size: int, label: str) -> None:
    remaining = size
    while remaining:
        chunk = source.read(min(BUFFER_SIZE, remaining))
        if not chunk:
            raise NcmError(f"{label}超出文件范围")
        target.write(chunk)
        remaining -= len(chunk)


def _resolve_target(directory: Path, stem: str, extension: str, conflict_policy: str) -> Path | None:
    target = directory / f"{stem}.{extension}"
    if not target.exists() or conflict_policy == "overwrite":
        return target
    if conflict_policy == "skip":
        return None
    for suffix in range(1, 1000000):
        candidate = directory / f"{stem} ({suffix}).{extension}"
        if not candidate.exists():
            return candidate
    raise NcmError(f"无法为输出文件生成唯一名称: {target}")


def _commit(temporary: Path, target: Path, *, overwrite: bool) -> None:
    if overwrite:
        os.replace(temporary, target)
        return
    try:
        os.link(temporary, target)
    except FileExistsError as exc:
        raise NcmError(f"输出文件在转换期间已存在: {target}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _artist_names(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    names: list[str] = []
    for entry in value:
        if isinstance(entry, list) and entry:
            name = _string_value(entry[0])
        elif isinstance(entry, str):
            name = entry
        else:
            name = ""
        if name.strip():
            names.append(name)
    return tuple(names)


def _string_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _write_json(path: Path, value: object) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".receipt-", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
