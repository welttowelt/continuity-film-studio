from continuity_film_studio.models import PROMPT_BLOCK_NAMES, SHOT_FIELDS, shot_asset_tags, validate_shot_card
from continuity_film_studio.project import shot_template


def test_shot_schema_has_exactly_22_fields() -> None:
    assert len(SHOT_FIELDS) == 22
    card = shot_template("SC01-SH01")
    assert validate_shot_card(card) == []


def test_shot_asset_tags_are_ordered_and_unique() -> None:
    card = shot_template("SC01-SH01")
    card["location"] = "@room"
    card["characters"] = [{"tag": "@cal", "state": "base"}, {"tag": "@cal", "state": "base"}]
    card["props"] = ["@cup"]
    assert shot_asset_tags(card) == ["@room", "@cal", "@cup"]


def test_prompt_schema_has_exactly_15_blocks() -> None:
    assert len(PROMPT_BLOCK_NAMES) == 15
    assert PROMPT_BLOCK_NAMES[0] == "shot_contract"
    assert PROMPT_BLOCK_NAMES[-1] == "reference_roles_and_boundaries"
