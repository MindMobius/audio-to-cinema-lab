# Adapter contract

An adapter is replaceable when it has a stable contract.

## Required request fields

- `project_id` and `revision`;
- `audio_interval` in seconds and integer frames;
- `intent` and `visual_constraints`;
- referenced asset ids and hashes;
- target resolution, frame rate and duration;
- optional provider-specific parameters.

## Required response fields

- adapter and tool version;
- execution status and elapsed seconds;
- input references and their hashes;
- workflow, prompt, seed and model or service identifiers;
- output path, media metadata and SHA-256;
- review status and rejection reason when not selected.

A recorded workflow from a previous machine is useful evidence, but it is not an executable local adapter until its inputs, models, nodes and runtime have been verified.

## Initial adapter groups

- `asr`: transcript and language;
- `alignment`: phrase or word timing;
- `audio-analysis`: sections, beats, onsets and energy;
- `asset-generation`: character, wardrobe, scene and prop references;
- `image-generation`: still keyframes;
- `video-generation`: motion clips;
- `editor`: frame timeline and media normalization;
- `composition`: subtitles, title card and final render;
- `verification`: deterministic and visual checks.
