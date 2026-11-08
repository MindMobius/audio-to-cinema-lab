# Audio-to-Cinema Lab

- Run development, tests and dependency installs in Linux / WSL Ubuntu. Use a project virtual environment.
- Read README.md and docs/architecture.md before changing contracts or adapters.
- Projects live at projects/YYYY-MM-DD/<slug>/; the date is the creation date, not the latest render date. Never silently overwrite a project or an artifact.
- Audio is the master timeline. Use integer frames for editorial timing; preserve the supplied audio unless the user asks to process it.
- Separate measured audio observations, creative interpretation and selected render outputs.
- Track scripts, prompts, workflow graphs, provenance, timestamps and hashes. Keep songs, full lyrics, model weights, rendered media, secrets and machine-specific paths inside ignored .local/ directories.
- Inspect staged content before publishing. The root MIT license does not relicense third-party tools, models, recordings or other assets; retain their attribution.
- Do not invent song translations or credits. Song titles come from confirmed metadata; opening credits appear at frame 0 when requested.
- Keep tool-specific options in adapters and project config. State whether an integration is executable here, a recorded production workflow, or planned.
- Test boundary validation, overwrite protection, timeline continuity and real adapter outputs. Do not claim generation reproducibility from a metadata-only check.
- Preserve the original production folders. Migration is a verified copy, never a destructive move.
