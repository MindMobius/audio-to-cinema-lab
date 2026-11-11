"""Command line entry point for repository and project operations."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .media import audit, restore
from .ncm import decode_many, inspect_file, collect_ncm_files
from .project import create, validate
from .recipes import RECIPE_IDS
from .music import MusicLibrary
from .layout import migrate


def cmd_validate(args: argparse.Namespace) -> int:
    errors = validate(Path(args.project))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {args.project}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    root = Path(args.root).expanduser()
    if not root.is_absolute():
        root = workspace / root
    if args.music:
        library = MusicLibrary(workspace)
        if root.resolve() != workspace / "projects":
            raise ValueError("--music requires the workspace's projects directory")
        asset = library.choose(library.read(), args.music)
        if len(asset["lyrics_candidates"]) > 1:
            raise ValueError("multiple lyric versions; initialize first, then music bind --lyrics-sha256")
        # Prepare before creating the project so a failed decode or probe leaves
        # no half-initialized production directory behind.
        library.prepare(asset["id"])
    path = create(root, args.date, args.slug, args.title, args.kind, recipe=args.recipe)
    if args.music:
        library.bind(asset["id"], path)
    print(path)
    return 0


def cmd_media_audit(args: argparse.Namespace) -> int:
    result = audit(Path(args.project), args.profile)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def cmd_media_restore(args: argparse.Namespace) -> int:
    result = restore(Path(args.project), Path(args.source), args.profile)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_audio_ncm_inspect(args: argparse.Namespace) -> int:
    files = collect_ncm_files([Path(item) for item in args.inputs])
    result = [inspect_file(path).as_dict() for path in files]
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_output == "-":
        print(text, end="")
    else:
        output = Path(args.json_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    return 0 if all(item["convertible"] for item in result) else 2


def cmd_audio_ncm_decode(args: argparse.Namespace) -> int:
    output = Path(args.output)
    receipt = Path(args.receipt) if args.receipt else output / "ncm-decode.receipt.json"
    result = decode_many(
        [Path(item) for item in args.inputs],
        output,
        conflict_policy=args.conflict,
        include_cover=args.include_cover,
        receipt=receipt,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


def cmd_music(args: argparse.Namespace) -> int:
    library = MusicLibrary(Path(args.workspace))
    if args.music_command == "scan":
        result = library.scan()
    elif args.music_command == "list":
        result = library.list_assets(args.query)
        if not args.json:
            for item in result:
                print(f"{item['id'][:22]}  {item['state']:8}  {' / '.join(item['artists'])} — {item['title']}  "
                      f"[{item['format']}; lyrics={item['lyric_versions']}; projects={len(item['projects'])}]")
            return 0
    elif args.music_command == "prepare":
        result = library.prepare(args.selector)
    elif args.music_command == "bind":
        result = library.bind(args.selector, Path(args.project), lyrics_sha256=args.lyrics_sha256)
    elif args.music_command == "import-receipt":
        receipt = Path(args.receipt).expanduser()
        if not receipt.is_absolute():
            receipt = library.root / receipt
        result = library.import_receipt(receipt)
    elif args.music_command == "audit":
        result = library.audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if isinstance(result, dict) and (result.get("ok") is False or result.get("errors")) else 0


def cmd_layout(args: argparse.Namespace) -> int:
    result = migrate(Path(args.workspace), apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get("conflicts") else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cinema-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate", help="validate a project manifest and artifacts")
    validate_parser.add_argument("project")
    validate_parser.set_defaults(func=cmd_validate)

    init = sub.add_parser("init", help="create an empty dated project")
    init.add_argument("--root", default="projects")
    init.add_argument("--music", help="catalog asset ID or unambiguous song name to pin")
    init.add_argument("--workspace", default=".", help="Lab workspace containing source/music and library/music")
    init.add_argument("--recipe", choices=RECIPE_IDS, help="copy a production recipe; does not generate media")
    init.add_argument("--date", required=True)
    init.add_argument("--slug", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--kind", default="audio-driven-video")
    init.set_defaults(func=cmd_init)

    media = sub.add_parser("media", help="audit or restore local media")
    media_sub = media.add_subparsers(dest="media_command", required=True)
    audit_parser = media_sub.add_parser("audit")
    audit_parser.add_argument("project")
    audit_parser.add_argument("--profile", default="all")
    audit_parser.set_defaults(func=cmd_media_audit)
    restore_parser = media_sub.add_parser("restore")
    restore_parser.add_argument("project")
    restore_parser.add_argument("--source", required=True, help="external production workspace")
    restore_parser.add_argument("--profile", default="all")
    restore_parser.set_defaults(func=cmd_media_restore)

    audio = sub.add_parser("audio", help="audio input and decoding operations")
    audio_sub = audio.add_subparsers(dest="audio_command", required=True)
    ncm = audio_sub.add_parser("ncm", help="inspect or decode local NCM containers")
    ncm_sub = ncm.add_subparsers(dest="ncm_command", required=True)

    inspect_parser = ncm_sub.add_parser("inspect", help="inspect NCM metadata and payloads")
    inspect_parser.add_argument("inputs", nargs="+", help="NCM files or directories")
    inspect_parser.add_argument("--json-output", default="-", help="JSON output path, or - for stdout")
    inspect_parser.set_defaults(func=cmd_audio_ncm_inspect)

    decode_parser = ncm_sub.add_parser("decode", help="decode NCM files to MP3 or FLAC")
    decode_parser.add_argument("inputs", nargs="+", help="NCM files or directories")
    decode_parser.add_argument("--output", default="library/music/decoded-imports")
    decode_parser.add_argument("--receipt", help="receipt path; defaults inside the output directory")
    decode_parser.add_argument("--include-cover", action="store_true")
    decode_parser.add_argument("--conflict", choices=("rename", "skip", "overwrite"), default="rename")
    decode_parser.set_defaults(func=cmd_audio_ncm_decode)

    layout = sub.add_parser("migrate-layout", help="rewrite legacy paths and remove the obsolete workspace layout")
    layout.add_argument("--workspace", default=".")
    layout.add_argument("--apply", action="store_true")
    layout.set_defaults(func=cmd_layout)

    music = sub.add_parser("music", help="catalog, prepare and pin local music assets")
    music.add_argument("--workspace", default=".", help="Lab workspace root")
    music_sub = music.add_subparsers(dest="music_command", required=True)
    music_sub.add_parser("scan", help="index source/music; preserve lyric versions").set_defaults(func=cmd_music)
    listing = music_sub.add_parser("list", help="show songs, readiness and project usage")
    listing.add_argument("query", nargs="?", default="")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=cmd_music)
    prepare = music_sub.add_parser("prepare", help="prepare one song or verify and reuse its cached master")
    prepare.add_argument("selector")
    prepare.set_defaults(func=cmd_music)
    bind = music_sub.add_parser("bind", help="pin audio and lyric versions in an existing project")
    bind.add_argument("selector")
    bind.add_argument("project")
    bind.add_argument("--lyrics-sha256")
    bind.set_defaults(func=cmd_music)
    imports = music_sub.add_parser("import-receipt", help="adopt hash-verified outputs of a previous NCM batch")
    imports.add_argument("receipt")
    imports.set_defaults(func=cmd_music)
    music_sub.add_parser("audit", help="verify cached music and all pinned project inputs").set_defaults(func=cmd_music)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}")
        return 2
