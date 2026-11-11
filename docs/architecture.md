# Architecture

Audio-to-Cinema Lab is organized around artifacts and contracts rather than around a vendor-specific tool chain.

## Artifact graph

```text
AudioMaster
  ├── TextTrack (optional)
  ├── AudioAnalysis
  └── MusicStructure
          ↓
CreativePlan ──→ AssetManifest
          ↓             ↓
       ShotPlan ───→ ShotArtifact(s)
          ↓             ↓
        EditTimeline ─→ CompositionProject ─→ Delivery
```

Every arrow is an explicit reference in JSON or a project document. A shot should be possible to trace back to its audio interval, creative intent, asset references, prompt, workflow, selected output and review decision.

## Layer boundaries

### 1. Input layer

The input layer accepts an audio file or a generated audio artifact. It records source metadata, duration, sample rate, channel layout, origin and SHA-256. The original recording is not silently normalized, trimmed or re-encoded.

### 2. Analysis layer

Analysis produces observations:

- transcript segments and word or phrase timing;
- forced-alignment evidence and confidence;
- sections, beats, onsets, RMS or loudness changes;
- optional stem or vocal envelope used only for alignment;
- warnings where the analysis is uncertain.

An analysis result is not a story. Creative interpretation is stored separately.

### 3. Creative layer

The creative plan turns observations into a chosen visual direction. It can contain several proposals before one is selected. A plan names the visual medium, palette, character requirement, scene grammar, recurring motifs, shot density and transition logic.

### 4. Asset layer

Assets are stable references, not just files. A character asset records identity, wardrobe, view set, source provenance, generator and review notes. A scene asset records layout, lighting, time, weather, key props and allowed variations.

### 5. Generation layer

A generation adapter receives a normalized shot request and returns one or more artifacts. It must record the adapter name, tool version, workflow or prompt, seeds, model and LoRA references, input asset hashes, duration, resolution, output hash and execution time.

The adapter may be H3, another local model, an external service or a hand-made source. The project does not infer equivalence between adapters.

### 6. Editorial layer

The edit layer converts selected shot artifacts into an integer-frame timeline. It owns shot order, trims, replacement decisions, re-takes, subtitle cues and audio mapping. The audio master is the timing authority.

### 7. Composition layer

The composition layer adds presentation graphics, subtitles, title cards and final media treatment. HyperFrames is the implementation used in local productions, but the composition contract is independent of it.

### 8. Verification layer

Verification is split into:

- deterministic checks: media metadata, decode, duration, frame count, audio hash, subtitle timing and path references;
- visual review: composition, identity consistency, motion quality, continuity, legibility and creative fit.

A passing deterministic check cannot claim artistic quality.

## Revision rules

A local change should update only the affected layer and its dependent artifacts:

- translation or timing → subtitles and composition;
- title or credits → composition;
- one bad shot → that shot, edit selection and final render;
- wardrobe or identity → linked shots must be reviewed;
- audio replacement → analysis, plan, shots and edit timing require a new revision.

The project manifest should record the current revision and the parent revision when an artifact is replaced.

## Production recipes and local data

`init --recipe` snapshots a documented method plus visual-direction, caption-profile and review-plan templates into `projects/`. This scaffolds planning only; it is not a model runner. Production receipts and concrete assets remain local. Current implementation states are listed in [components](production/components.md).

A planning project can have unknown audio duration. Once its status leaves `planning`, a positive measured duration is required. Generic metadata validation is separate from generation coverage and delivery acceptance; the latter checks remain a documented procedure until the common runner is implemented.
