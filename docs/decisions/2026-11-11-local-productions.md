# Concrete productions stay local — historical decision — 2026-11-11

This historical decision superseded the earlier decision to include a concrete production as the repository sample. The user's explicit direction is to iterate on the Lab while every MV engineering project remains local.

- Historical default in this record: `.local/projects/YYYY-MM-DD/<slug>/`. The current path is `projects/YYYY-MM-DD/<slug>/`; see [the current music and projects decision](2026-11-11-music-library-and-projects.md).
- Preserve the original date and use revisions for re-renders.
- Ignore the legacy `projects/` path; remove its existing entries from the Git index without deleting local files.
- Replace song-dependent repository tests with synthetic fixtures.
- Publish reusable code, normalized contracts, general production knowledge and neutral recipes only.
- Existing Git history is preserved; untracking is not retroactive history removal.

Recipes describe documented production methods. Until generic generation and rendering adapters exist, recipe initialization must not be described as full automated production.
