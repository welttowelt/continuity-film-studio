from continuity_film_studio.models import (
    PROMPT_BLOCK_NAMES,
    SHOT_FIELDS,
    VISUAL_BIBLE_DECISIONS,
    shot_asset_tags,
    validate_shot_card,
)
from continuity_film_studio.project import shot_template


def test_shot_schema_has_exactly_22_fields() -> None:
    assert len(SHOT_FIELDS) == 22
    card = shot_template("SC01-SH01")
    assert set(card) == {*SHOT_FIELDS, "prompt_prep"}
    assert set(card["prompt_prep"]) == {"text_tasks", "timed_beats", "known_risk"}
    assert validate_shot_card(card) == []


def test_shot_schema_rejects_unrecognized_fourth_lane_fields() -> None:
    card = shot_template("SC01-SH01")
    card["extra_direction_lane"] = {"mood": "ominous"}

    assert validate_shot_card(card) == ["unexpected shot field: extra_direction_lane"]


def test_shot_asset_tags_are_ordered_and_unique() -> None:
    card = shot_template("SC01-SH01")
    card["location"] = "@room"
    card["characters"] = [{"tag": "@cal", "state": "base"}, {"tag": "@cal", "state": "base"}]
    card["props"] = ["@cup"]
    assert shot_asset_tags(card) == ["@room", "@cal", "@cup"]


def test_prompt_schema_has_exactly_15_blocks() -> None:
    assert PROMPT_BLOCK_NAMES == (
        "scene_context",
        "active_references",
        "location_map",
        "first_frame_blocking",
        "format_mode",
        "optics",
        "camera_body",
        "action_timing",
        "physics",
        "lighting",
        "audio",
        "character_acting",
        "style_prefix",
        "quality_bar",
        "positive_constraints",
    )


def test_visual_bible_uses_machina_style_categories() -> None:
    assert VISUAL_BIBLE_DECISIONS == (
        "lighting",
        "palette",
        "optics",
        "camera_movement",
        "texture",
        "edit_tempo",
        "sound",
    )
