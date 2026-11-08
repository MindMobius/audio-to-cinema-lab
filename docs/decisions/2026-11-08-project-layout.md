# Project layout decision — 2026-11-08

## Decision

Use `projects/YYYY-MM-DD/project-slug/`.

For the first migrated work:

```text
projects/2026-11-08/one-last-kiss/
```

## Why

`projects` remains a collection rather than becoming a sequence of differently named top-level directories. The date separates creation batches, while the slug gives the work a stable identity. A new render or correction is a revision of the same project and should not create a new date directory.

A same-day naming collision is resolved with a meaningful slug suffix such as `-director-cut`, not by overwriting an existing directory.

## Consequences

- Every project README can be found using the same path shape.
- Tool-independent documentation stays at the repository root.
- Large files can be restored into the project workspace without changing the Git path contract.
- CI can validate project paths and required manifests uniformly.
