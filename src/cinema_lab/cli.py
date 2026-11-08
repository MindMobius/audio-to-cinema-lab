"""Command line entry point for repository and project operations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .media import audit, restore
from .project import create, validate


def cmd_validate(args: argparse.Namespace) -> int:
    errors = validate(Path(args.project))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {args.project}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    path = create(Path(args.root), args.date, args.slug, args.title, args.kind)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cinema-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate", help="validate a project manifest and artifacts")
    validate_parser.add_argument("project")
    validate_parser.set_defaults(func=cmd_validate)

    init = sub.add_parser("init", help="create an empty dated project")
    init.add_argument("--root", default="projects")
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

    args = parser.parse_args(argv)
    return args.func(args)
