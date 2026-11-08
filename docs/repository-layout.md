# Repository layout

```text
projects/YYYY-MM-DD/project-slug/
```

The date is the project creation date. The slug is stable and human-readable. Do not use a render timestamp as the project identity.

Use these artifact folders:

- `audio/`: source metadata, transcript, alignment and musical analysis;
- `concept/`: creative treatment, visual direction, style and section plan;
- `assets/`: lightweight previews and asset manifests;
- `shots/`: shot plan, prompts, selection and review notes;
- `workflows/`: executed or planned tool workflows;
- `edit/`: timeline, captions and composition source;
- `verification/`: checks, reports and delivery manifest.

Raw user audio, full video renders, generated clips, model files and runtime caches belong in the local project workspace. Their paths and SHA-256 values belong in `project.json` or a dedicated manifest.
