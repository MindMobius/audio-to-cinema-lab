"""Check the staged Git tree without reading ignored production files."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys

PUBLIC_DIRECTORIES = {".github", "docs", "src", "tests", "tools"}
PUBLIC_ROOT_FILES = {
    ".env.example", ".gitignore", "AGENTS.md", "LICENSE", "README.md",
    "THIRD_PARTY_NOTICES.md", "pyproject.toml",
}
PRIVATE_DIRECTORIES = {
    ".local", "projects", "source", "library", "archive", "outputs", "renders", "deliveries", "models",
    ".venv", "node_modules", "__pycache__", "third_party", "build", "dist",
}
PRIVATE_FILENAMES = {
    "project.json", "media.manifest.json", "timeline.json", "submission.json",
    "workflow.api.json", "workflow.ui.json", "import_project.py",
}
PRIVATE_SUFFIXES = {
    # Source and rendered media, full lyric/subtitle files, models and archives.
    ".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".mxf",
    ".m4a", ".mp3", ".wav", ".flac", ".ncm", ".aac", ".ogg", ".opus", ".aiff",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".avif", ".exr",
    ".lrc", ".srt", ".ass", ".ssa", ".vtt", ".psd", ".blend",
    ".safetensors", ".ckpt", ".pt", ".pth", ".onnx", ".gguf", ".bin",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".xz", ".bz2", ".tgz",
    ".pem", ".key", ".p12", ".log", ".pyc",
}
MAX_BLOB_BYTES = 1024 * 1024


def git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], input=data, capture_output=True, check=True,
    ).stdout


def check_index(repo: Path) -> list[str]:
    """Inspect staged paths and blob sizes, including files added with git add -f.

    This is a structural guard, not a content classifier. Review the staged diff
    separately for concrete project data disguised as an otherwise allowed file.
    """
    root = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip())
    records = []
    for record in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if record:
            metadata, filename = record.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split()
            records.append((mode, oid, stage, filename.decode("utf-8", errors="surrogateescape")))
    oids = sorted({oid for mode, oid, stage, name in records if mode in {"100644", "100755"}})
    sizes = {}
    if oids:
        objects = git(root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                      data=("\n".join(oids) + "\n").encode("ascii"))
        for entry in objects.decode("ascii").splitlines():
            oid, kind, size = entry.split()
            if kind != "blob":
                raise ValueError("expected a regular file blob in the Git index")
            sizes[oid] = int(size)
    issues = []
    for mode, oid, stage, name in records:
        path = PurePosixPath(name)
        reasons = []
        if stage != "0":
            reasons.append("unresolved merge entry")
        if mode not in {"100644", "100755"}:
            reasons.append("symlinks and submodules are not public source files")
        if len(path.parts) == 1:
            if name not in PUBLIC_ROOT_FILES:
                reasons.append("file is outside the public root layout")
        elif path.parts[0] not in PUBLIC_DIRECTORIES:
            reasons.append("directory is outside the public layout")
        if PRIVATE_DIRECTORIES.intersection(part.lower() for part in path.parts[:-1]):
            reasons.append("concrete projects and runtime data must stay local")
        if path.name.lower() in PRIVATE_FILENAMES or path.suffix.lower() in PRIVATE_SUFFIXES:
            reasons.append("production, media, caption, model or runtime file")
        if path.name.startswith(".env") and name != ".env.example":
            reasons.append("only the root .env.example may be tracked")
        if sizes.get(oid, 0) > MAX_BLOB_BYTES:
            reasons.append(f"staged blob exceeds {MAX_BLOB_BYTES} bytes")
        if reasons:
            issues.append(f"{name!r}: {'; '.join(reasons)}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        issues = check_index(args.repo)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Cannot inspect Git index ({type(error).__name__}).", file=sys.stderr)
        return 2
    if issues:
        print("Public Git tree rejected:\n" + "\n".join(issues), file=sys.stderr)
        return 1
    print("Public Git tree passed: staged paths and blob sizes satisfy the repository policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
