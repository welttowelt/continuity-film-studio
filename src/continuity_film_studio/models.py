from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SHOT_FIELDS = (
    "shot_id",
    "location",
    "time_of_day",
    "characters",
    "props",
    "description",
    "dialogue",
    "duration_seconds",
    "complexity",
    "goal",
    "task_verb",
    "dramaturgy",
    "blocking",
    "acting",
    "style_device",
    "shot_size",
    "camera_movement",
    "lens",
    "angle",
    "cut_type",
    "pace",
    "transition",
)

PROMPT_BLOCK_NAMES = (
    "shot_contract",
    "exact_cast",
    "character_passports",
    "location_passport",
    "prop_passports",
    "composition_and_blocking",
    "timed_action_beats",
    "acting_and_performance",
    "dialogue_and_sound",
    "camera_and_lens",
    "lighting",
    "physics_and_continuity",
    "style_and_texture",
    "palette_60_30_10",
    "reference_roles_and_boundaries",
)

VISUAL_BIBLE_DECISIONS = (
    "style",
    "palette",
    "lighting",
    "optics",
    "camera_movement",
    "texture",
    "edit_tempo",
    "sound",
)

ASSET_TYPES = ("character", "location", "prop")
RIGHTS_STATES = ("unknown", "confirmed", "denied")
QA_FIELDS = (
    "reference_match",
    "no_artifacts",
    "camera_match",
    "performance_match",
    "neighbor_cut_match",
)


class StudioError(RuntimeError):
    """Raised when a production gate fails."""


@dataclass
class GateReport:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_assets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "checked_assets": self.checked_assets,
        }


def validate_shot_card(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in SHOT_FIELDS:
        if field_name not in card:
            errors.append(f"missing shot field: {field_name}")
            continue
        value = card[field_name]
        if value is None or (value == "" and field_name != "dialogue"):
            errors.append(f"empty shot field: {field_name}")

    if errors:
        return errors

    if not isinstance(card["characters"], list):
        errors.append("characters must be a list")
    else:
        for character in card["characters"]:
            if not isinstance(character, dict) or not character.get("tag"):
                errors.append("each character must contain a tag")

    if not isinstance(card["props"], list):
        errors.append("props must be a list")

    duration = card["duration_seconds"]
    if not isinstance(duration, (int, float)) or not 0 < duration <= 30:
        errors.append("duration_seconds must be greater than 0 and no more than 30")

    text_tasks = card.get("text_tasks", [])
    if not isinstance(text_tasks, list):
        errors.append("text_tasks must be a list when present")

    return errors


def shot_asset_tags(card: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    location = card.get("location")
    if isinstance(location, str) and location:
        tags.append(location)
    elif isinstance(location, dict) and location.get("tag"):
        tags.append(location["tag"])

    for character in card.get("characters", []):
        if isinstance(character, dict) and character.get("tag"):
            tags.append(character["tag"])

    for prop in card.get("props", []):
        if isinstance(prop, str):
            tags.append(prop)
        elif isinstance(prop, dict) and prop.get("tag"):
            tags.append(prop["tag"])

    return list(dict.fromkeys(tags))


def stress_requirement(asset_type: str) -> int:
    return {"character": 10, "location": 8, "prop": 5}[asset_type]
