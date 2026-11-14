# Audio decoding

This adapter turns locally supplied NetEase Cloud Music `.ncm` containers into
playable MP3 or FLAC files before ASR, musical analysis or timeline work.

The implementation is a Python-native port of the classic NCM container flow
documented and implemented by [NCM Breaker](https://github.com/KaffuAlcaid/ncmBreaker)
(`0.4.1`, MIT). It does not log in to NetEase, download music, bypass an
account, or modify the original source file. It accepts files that the user is
allowed to process and writes decoded media to a local output directory.

For normal song selection use the [music library](../../music-library.md): it verifies and reuses prepared audio and pins the chosen versions in a project. The lower-level batch decoder remains available for imports.

Use the adapter from the project root:

```powershell
.\.venv\Scripts\python.exe -m cinema_lab audio ncm inspect source/music
.\.venv\Scripts\python.exe -m cinema_lab audio ncm decode source/music `
  --output library/music/decoded-imports --include-cover
```

The decoder checks the NCM marker, restores the embedded metadata and cover
information, detects the recovered MP3/FLAC payload, and writes a JSON receipt
containing input/output hashes, metadata, timing and failures. It never places
source recordings, decoded media or full lyric files into the public Git
history; the repository ignores `source/music/` and the generated media paths.

The adapter runs in the native Windows PowerShell environment. It requires the
Python `cryptography` package; FFmpeg remains a separate downstream tool for
media validation and analysis.
