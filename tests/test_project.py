from __future__ import annotations

from pathlib import Path

import pytest

from continuity_film_studio.io import read_json, write_json
from continuity_film_studio.models import (
    PROMPT_BLOCK_NAMES,
    QA_FIELDS,
    VISUAL_BIBLE_DECISIONS,
    StudioError,
)
from continuity_film_studio.project import (
    accept_take,
    add_asset,
    approve_visual_bible,
    audit_project,
    compile_prompt,
    decide_reference_board,
    gate_shot,
    init_project,
    link_visual_bible_board,
    lock_asset,
    log_attempt,
    record_stress_test,
    reference_board_template,
    shot_template,
    stress_template,
)


def approve_bible(project: Path) -> None:
    for key in VISUAL_BIBLE_DECISIONS:
        board_path = project / "references/boards" / f"{key}.json"
        (project / "references" / f"{key}.ref").write_text("reference", encoding="utf-8")
        board = reference_board_template(key, key)
        board["references"] = [
            {"file": f"references/{key}.ref", "caption": f"Controls the locked {key} decision."}
        ]
        write_json(board_path, board)
        decide_reference_board(board_path, "approved", f"locked {key} decision")
        link_visual_bible_board(project, key, board_path)
    approve_visual_bible(project)


def add_locked_asset(project: Path, tag: str, asset_type: str, *, rights: str = "confirmed") -> None:
    asset_name = tag.removeprefix("@").replace("/", "-")
    reference = project / "references" / f"{asset_name}.ref"
    reference.write_text("test-only reference marker", encoding="utf-8")
    add_asset(
        project,
        tag=tag,
        asset_type=asset_type,
        descriptor=f"Stable descriptor for {tag}.",
        references=[reference],
        scenes=["SC01"],
        variant_of=None,
        rights_state=rights,
        real_person=False,
        identity_authorized=False,
    )
    report = stress_template(project, tag)
    report["reviewer"] = "Test Reviewer"
    for index, case in enumerate(report["cases"]):
        case["condition"] = f"Production condition {index + 1} for {tag}."
        case["passed"] = True
    record_stress_test(project, tag, report)
    lock_asset(project, tag)


def ready_project(tmp_path: Path, distribution: str = "internal") -> tuple[Path, Path]:
    project = tmp_path / "production"
    init_project(project, "Test Film", "higgsfield", distribution)
    approve_bible(project)
    add_locked_asset(project, "@room", "location")
    add_locked_asset(project, "@cal", "character")
    add_locked_asset(project, "@cup", "prop")
    card = shot_template("SC01-SH01")
    card["location"] = "@room"
    card["characters"] = [{"tag": "@cal", "state": "base"}]
    card["props"] = ["@cup"]
    shot_path = project / "prompts/shot-cards/SC01-SH01.json"
    write_json(shot_path, card)
    return project, shot_path


def test_gate_blocks_draft_production(tmp_path: Path) -> None:
    project = tmp_path / "draft"
    init_project(project, "Draft", "higgsfield", "internal")
    shot_path = project / "prompts/shot-cards/SC01-SH01.json"
    write_json(shot_path, shot_template("SC01-SH01"))
    report = gate_shot(project, shot_path)
    assert not report.passed
    assert "visual bible is not approved" in report.errors
    audit = audit_project(project)
    assert audit.passed
    assert "visual bible is still draft" in audit.warnings
    assert any("not generation-ready" in warning for warning in audit.warnings)


def test_incomplete_stress_test_cannot_lock(tmp_path: Path) -> None:
    project = tmp_path / "production"
    init_project(project, "Test", "higgsfield", "internal")
    reference = project / "references/cal.ref"
    reference.write_text("reference", encoding="utf-8")
    add_asset(
        project,
        tag="@cal",
        asset_type="character",
        descriptor="Stable Cal descriptor.",
        references=[reference],
        scenes=["SC01"],
        variant_of=None,
        rights_state="confirmed",
        real_person=False,
        identity_authorized=False,
    )
    report = stress_template(project, "@cal")
    report["reviewer"] = "Test Reviewer"
    for index, case in enumerate(report["cases"]):
        case["condition"] = f"Distinct production condition {index + 1}."
    for case in report["cases"][:-1]:
        case["passed"] = True
    record_stress_test(project, "@cal", report)
    with pytest.raises(StudioError, match="full pass"):
        lock_asset(project, "@cal")


def test_gate_and_compile_locked_production(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    report = gate_shot(project, shot_path)
    assert report.passed
    prompt_path = compile_prompt(project, shot_path)
    prompt = read_json(prompt_path)
    assert [block["name"] for block in prompt["blocks"]] == list(PROMPT_BLOCK_NAMES)
    assert "Stable descriptor for @cal" in prompt["render_text"]
    assert audit_project(project).passed


def test_commercial_asset_requires_confirmed_rights(tmp_path: Path) -> None:
    project = tmp_path / "commercial"
    init_project(project, "Commercial", "higgsfield", "commercial")
    reference = project / "references/asset.ref"
    reference.write_text("reference", encoding="utf-8")
    add_asset(
        project,
        tag="@asset",
        asset_type="prop",
        descriptor="Stable asset.",
        references=[reference],
        scenes=[],
        variant_of=None,
        rights_state="unknown",
        real_person=False,
        identity_authorized=False,
    )
    report = stress_template(project, "@asset")
    report["reviewer"] = "Test Reviewer"
    for index, case in enumerate(report["cases"]):
        case["condition"] = f"Distinct commercial condition {index + 1}."
        case["passed"] = True
    record_stress_test(project, "@asset", report)
    with pytest.raises(StudioError, match="confirmed asset rights"):
        lock_asset(project, "@asset")


def test_attempt_log_enforces_one_changed_block(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_1 = compile_prompt(project, shot_path)
    result_1 = project / "generations/attempt-1.bin"
    result_1.write_bytes(b"one")
    first = log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt_1,
        result_path=result_1,
        verdict="rejected",
        changed_block="initial",
        qa=None,
        allow_identical=False,
    )
    assert first["attempt"] == 1

    card = read_json(shot_path)
    card["acting"] = "Cal blinks once and tightens his jaw."
    write_json(shot_path, card)
    prompt_2 = compile_prompt(project, shot_path)
    result_2 = project / "generations/attempt-2.bin"
    result_2.write_bytes(b"two")
    second = log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt_2,
        result_path=result_2,
        verdict="rejected",
        changed_block="acting_and_performance",
        qa=None,
        allow_identical=False,
    )
    assert second["detected_changed_blocks"] == ["acting_and_performance"]

    card["acting"] = "Cal looks down."
    card["lens"] = "35mm"
    write_json(shot_path, card)
    prompt_3 = compile_prompt(project, shot_path)
    with pytest.raises(StudioError, match="more than one prompt block changed"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt_3,
            result_path=result_2,
            verdict="rejected",
            changed_block="acting_and_performance",
            qa=None,
            allow_identical=False,
        )


def test_accept_take_requires_complete_qa(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt = compile_prompt(project, shot_path)
    result = project / "generations/final.mp4"
    result.write_bytes(b"test media marker")
    qa = {field: True for field in QA_FIELDS}
    log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt,
        result_path=result,
        verdict="accepted",
        changed_block="initial",
        qa=qa,
        allow_identical=False,
    )
    selected = accept_take(project, "SC01-SH01", 1)
    assert selected.read_bytes() == result.read_bytes()
    with pytest.raises(StudioError, match="will not be overwritten"):
        accept_take(project, "SC01-SH01", 1)


def test_rejected_attempt_15_stops_further_iteration(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt = compile_prompt(project, shot_path)
    result = project / "generations/rejected.bin"
    result.write_bytes(b"rejected")
    row = None
    for attempt in range(1, 16):
        row = log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt,
            result_path=result,
            verdict="rejected",
            changed_block="initial" if attempt == 1 else "seed_only",
            qa=None,
            allow_identical=attempt > 1,
        )
    assert row is not None and row["simplify_required"]
    with pytest.raises(StudioError, match="simplify or split"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt,
            result_path=result,
            verdict="rejected",
            changed_block="seed_only",
            qa=None,
            allow_identical=True,
        )
