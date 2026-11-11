# Audio-to-Cinema Lab

- Run development, tests and dependency installs in Linux / WSL Ubuntu. Use a project virtual environment.
- Read README.md and docs/architecture.md before changing contracts or adapters.
- Concrete projects live at ignored projects/YYYY-MM-DD/<slug>/; the date is the creation date, not the latest render date. Never silently overwrite a project or an artifact.
- Audio is the master timeline. Use integer frames for editorial timing; preserve the supplied audio unless the user asks to process it.
- Separate measured audio observations, creative interpretation and selected render outputs.
- Track scripts, prompts, workflow graphs, provenance, timestamps and hashes. Keep every concrete project (including its prompts, workflows, captions and verification records), songs, full lyrics, model weights, rendered media, secrets and machine-specific paths inside ignored source/, library/, projects/ and archive/ directories. Git contains generalized recipes, synthetic examples, reusable code and documentation.
- Keep runtime code in src/cinema_lab/, package data in src/cinema_lab/resources/, and adapter/pipeline documentation in docs/.
- Run python tools/check_public_tree.py after staging and inspect staged content before publishing. The root MIT license does not relicense third-party tools, models, recordings or other assets; retain their attribution.
- Do not invent song translations or credits. Song titles come from confirmed metadata; opening credits appear at frame 0 when requested.
- Keep tool-specific options in adapters and project config. State whether an integration is executable here, a recorded production workflow, or planned.
- Test boundary validation, overwrite protection, timeline continuity and real adapter outputs. Do not claim generation reproducibility from a metadata-only check.
- Preserve the original production folders. Migration is a verified copy, never a destructive move.

- Missing required shots must be reported; never silently substitute a still or loop to label an MV complete. Intentional held frames or loops need an explicit creative decision.
- Confirmed source LRC timing is authoritative; instrumental openings are not evidence of subtitle misalignment.
- Technical verification and visual acceptance are separate; state which time ranges were actually reviewed.

- Use source/music/ for original music and LRC; library/music/ for prepared shared assets; projects/YYYY-MM-DD/<slug>/ for productions. .local/ paths are compatibility only.
- Use music scan/prepare/bind to record versions; never match different audio masters by title alone or change confirmed LRC timing.
- Keep previews and final exports in the WSL project. Export to Windows only for a requested delivery; do not create a new Downloads folder for each experiment.
