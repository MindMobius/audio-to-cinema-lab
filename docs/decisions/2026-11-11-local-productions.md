# Concrete productions stay local — 2026-11-11

This supersedes the earlier decision to include a concrete production as the repository sample. The user's explicit direction is to iterate on the Lab while every MV engineering project remains local.

- Default new path: `.local/projects/YYYY-MM-DD/<slug>/`.
- Preserve the original date and use revisions for re-renders.
- Ignore the legacy `projects/` path; remove its existing entries from the Git index without deleting local files.
- Replace song-dependent repository tests with synthetic fixtures.
- Publish reusable code, normalized contracts, general production knowledge and neutral recipes only.
- Existing Git history is preserved; untracking is not retroactive history removal.

Recipes describe documented production methods. Until generic generation and rendering adapters exist, recipe initialization must not be described as full automated production.
