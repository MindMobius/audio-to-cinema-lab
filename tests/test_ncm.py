import base64
import json
import struct
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from cinema_lab.ncm import (
    CORE_KEY,
    JSON_PREFIX,
    KEY_PREFIX,
    MAGIC,
    METADATA_KEY,
    METADATA_PREFIX,
    collect_ncm_files,
    decode_file,
    decode_many,
    detect_audio_format,
    inspect_file,
    _audio_keystream,
)


def _aes_encrypt(payload: bytes, key: bytes) -> bytes:
    padder = PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(payload) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def _make_ncm(path: Path) -> tuple[bytes, bytes, bytes]:
    stream_key = b"test-stream-key-for-ncm"
    metadata = {
        "musicName": "测试歌曲",
        "artist": [["测试歌手", "1"]],
        "album": "测试专辑",
        "format": "mp3",
    }
    raw_metadata = json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode()
    encoded_key = bytes(value ^ 0x64 for value in _aes_encrypt(KEY_PREFIX + stream_key, CORE_KEY))
    metadata_plain = JSON_PREFIX + raw_metadata
    metadata_payload = METADATA_PREFIX + base64.b64encode(_aes_encrypt(metadata_plain, METADATA_KEY))
    encoded_metadata = bytes(value ^ 0x63 for value in metadata_payload)

    cover = b"\xff\xd8\xff\xe0synthetic-cover"
    audio = b"ID3\x03\x00" + bytes(range(256)) * 3
    key_stream = _audio_keystream(stream_key)
    encrypted_audio = bytes(value ^ key_stream[index & 0xFF] for index, value in enumerate(audio))
    container = b"".join(
        (
            MAGIC + b"\x01\x70",
            struct.pack("<I", len(encoded_key)),
            encoded_key,
            struct.pack("<I", len(encoded_metadata)),
            encoded_metadata,
            b"\x00" * 5,
            struct.pack("<I", len(cover)),
            struct.pack("<I", len(cover)),
            cover,
            encrypted_audio,
        )
    )
    path.write_bytes(container)
    return audio, cover, raw_metadata


def test_ncm_inspection_and_decode_round_trip(tmp_path: Path):
    source = tmp_path / "测试歌曲.ncm"
    expected_audio, expected_cover, _ = _make_ncm(source)
    inspection = inspect_file(source)

    assert inspection.profile == "CLASSIC_NCM"
    assert inspection.convertible
    assert inspection.audio_format == "mp3"
    assert inspection.cover_format == "jpeg"
    assert inspection.metadata is not None
    assert inspection.metadata.title == "测试歌曲"
    assert inspection.metadata.artist_display == "测试歌手"

    result = decode_file(source, tmp_path / "decoded", include_cover=True)
    assert result.outcome == "WRITTEN"
    assert result.output.read_bytes() == expected_audio
    assert result.cover is not None
    assert result.cover.read_bytes() == expected_cover
    assert detect_audio_format(result.output.read_bytes()[:16]) == "mp3"


def test_ncm_batch_collection_and_conflict_rename(tmp_path: Path):
    source = tmp_path / "music"
    source.mkdir()
    _make_ncm(source / "song.ncm")
    (source / "ignore.txt").write_text("ignore", encoding="utf-8")
    assert collect_ncm_files([source]) == [(source / "song.ncm").resolve()]

    output = tmp_path / "decoded"
    first = decode_file(source / "song.ncm", output)
    second = decode_file(source / "song.ncm", output)
    assert first.output.name == "song.mp3"
    assert second.output.name == "song (1).mp3"


def test_ncm_inspection_rejects_non_ncm(tmp_path: Path):
    source = tmp_path / "not-ncm.bin"
    source.write_bytes(b"not an ncm file")
    inspection = inspect_file(source)
    assert inspection.profile == "NOT_NCM"
    assert not inspection.convertible


def test_ncm_batch_writes_receipt(tmp_path: Path):
    source = tmp_path / "song.ncm"
    _make_ncm(source)
    receipt = tmp_path / "receipts" / "ncm.json"
    result = decode_many([source], tmp_path / "decoded", receipt=receipt)

    assert result["ok"] is True
    assert result["outputs"][0]["outcome"] == "WRITTEN"
    assert receipt.is_file()
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    assert saved["adapter"] == "audio-decoding.ncm"
    assert saved["upstream"]["name"] == "NCM Breaker"
