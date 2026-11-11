"""Reusable production recipe scaffolds; these do not generate or render media."""
from __future__ import annotations

import json
from pathlib import Path

from .io import write

RECIPE_DIR = Path(__file__).with_name("resources") / "recipes"
RECIPE_IDS = ("cinematic-scenes", "abstract-emotion", "continuous-scroll")


def load_recipe(name: str) -> dict:
    if name not in RECIPE_IDS:
        raise ValueError(f"unknown recipe: {name}")
    return json.loads((RECIPE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def scaffold(project: Path, recipe: dict) -> dict[str, str]:
    """Write a recipe into a newly created project, never into an existing work."""
    artifacts = {
        "production_recipe": "concept/recipe.json",
        "visual_direction": "concept/visual-direction.md",
        "caption_profile": "edit/caption-profile.json",
        "review_plan": "verification/review-plan.json",
    }
    for relative in artifacts.values():
        if (project / relative).exists():
            raise FileExistsError(f"refusing to overwrite recipe artifact: {relative}")
    caption = {
        "profile": recipe["caption_profile"],
        "status": "reference-settings-require-project-review",
        "text_baked_into_images": False,
        "source_timing_policy": "keep-confirmed-input; frame-quantization-only",
        "original_and_translation": "paired",
    }
    if recipe["caption_profile"] == "spatial-brackets":
        caption.update({
            "coordinate_space": "world",
            "stanza_preview": True,
            "active_indicator": "hand-drawn-short-brackets",
            "active_color_or_scale_change": False,
            "completed_pair_fade_seconds": 0.75,
            "indicator_transition_seconds": 1 / 6,
            "timing_note": "Reference durations; quantize to the selected project fps.",
        })
    else:
        caption.update({"coordinate_space": "screen", "placement": "bottom", "animated_emphasis": False})
    write(project / "concept/recipe.json", recipe)
    write(project / "edit/caption-profile.json", caption)
    write(project / "verification/review-plan.json", {
        "status": "pending",
        "pilot_focus": recipe["pilot_focus"],
        "coverage": {"planned": [], "selected": [], "missing": [], "rejected": []},
        "missing_asset_policy": "block-delivery; no-silent-still-or-loop-fallback",
        "technical_checks": ["decode-and-frame-count", "full-audio-and-sync", "caption-timing-and-layout", "source-hashes", "opening-and-ending"],
        "visual_checks": ["style-consistency", "identity-and-face-detail", "motion-and-contact", "scene-continuity", "lyric-legibility", "musical-fit"],
        "reviewed_ranges": [],
        "automatic_checks_imply_artistic_acceptance": False,
        "enforcement": "review-plan-only; generic-delivery-gate-not-implemented",
    })
    template = Path(__file__).with_name("resources") / "templates/production/visual-direction.md"
    (project / "concept/visual-direction.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return artifacts
