# Production workflow

This is the working procedure for an audio-driven project. Each stage should produce a reviewable artifact before the next stage expands the scope.

## 1. Register the audio

Create a dated project directory and register the audio master. Capture duration and media metadata, then compute a hash. If the audio is generated, also preserve the generation prompt, model, seed or service request.

## 2. Analyze the audio

Choose one or more analyzers:

- text-bearing audio: ASR, language detection, phrase segmentation and forced alignment;
- music with lyrics: transcript plus vocal or stem envelope review;
- instrumental audio: sections, tempo candidates, beats, onsets, RMS, spectral changes and silence;
- speech or voiceover: speaker turns, pauses, emphasis and pronunciation review.

Save raw observations and a human-reviewed interpretation. Do not turn an uncertain tempo estimate into a hard editorial cut without recording that decision.

## 3. Write the visual treatment

For each musical or textual section, state:

- what the listener hears;
- what the section means in the chosen interpretation;
- the visual subject and action;
- the desired shot duration and energy;
- the character, scene and prop assets needed;
- transitions into and out of the section.

Keep at least one alternative when the audio supports materially different visual readings.

## 4. Build only the needed assets

Create identity cards before generating many character shots. Add wardrobe, scene and prop variants when the shot plan requires them. Every generated reference receives a stable id and review status. Do not create a large asset library before a plan needs it.

## 5. Generate and review shots

A shot request includes the audio interval, frame prompt, action prompt, references, constraints and output spec. Generate a small set, inspect actual decoded frames, reject defects, and record why the selected take was chosen. Keep rejected outputs out of the delivery set while retaining their decision record when useful.

## 6. Assemble the edit

Convert selected clips to the target frame rate and resolution only once where possible. Keep an integer frame timeline. Preserve the original audio stream when the user expects the source recording unchanged. Add captions and opening information in a separate composition layer.

## 7. Review and revise

Run deterministic checks first. Then inspect opening, section transitions, all character appearances, every selected shot, subtitle intervals and the final fade. A revision should name the layer it changes and invalidate dependent checks.

## 8. Package the project

The Git repository contains contracts, manifests, scripts, prompts, workflows, lightweight previews and verification records. Large media, source recordings, model weights and machine caches remain local or use a separately configured artifact store. The project README must say exactly how to restore those inputs.
