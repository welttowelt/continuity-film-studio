from pathlib import Path

import pytest

from continuity_film_studio.io import read_json, write_json
from continuity_film_studio.models import StudioError
from continuity_film_studio.project import decide_reference_board, reference_board_template


def test_approved_reference_board_requires_captions(tmp_path: Path) -> None:
    path = tmp_path / "board.json"
    board = reference_board_template("lighting", "lighting")
    board["references"] = [{"file": "frame.ref", "caption": ""}]
    write_json(path, board)
    with pytest.raises(StudioError, match="caption"):
        decide_reference_board(path, "approved", "Side-lit practicals only.")


def test_approved_reference_board_requires_a_positive_reference(tmp_path: Path) -> None:
    path = tmp_path / "board.json"
    write_json(path, reference_board_template("lighting", "lighting"))
    with pytest.raises(StudioError, match="positive reference"):
        decide_reference_board(path, "approved", "Side-lit practicals only.")


def test_reference_board_records_written_decision(tmp_path: Path) -> None:
    path = tmp_path / "board.json"
    board = reference_board_template("lighting", "lighting")
    board["references"] = [{"file": "frame.ref", "caption": "Warm practical from frame left."}]
    write_json(path, board)
    decide_reference_board(path, "approved", "Warm practical from frame left; no flat frontal key.")
    updated = read_json(path)
    assert updated["status"] == "approved"
    assert updated["decision"].startswith("Warm practical")
