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
    validate_render_prompt,
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


def add_locked_asset(
    project: Path,
    tag: str,
    asset_type: str,
    *,
    rights: str = "confirmed",
    variant_of: str | None = None,
) -> None:
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
        variant_of=variant_of,
        rights_state=rights,
        real_person=False,
        identity_authorized=False,
    )
    report = stress_template(project, tag)
    report["reviewer"] = "Test Reviewer"
    if asset_type != "character":
        report["lock_decision"] = "approved"
        report["lock_decision_by"] = "Test Producer"
    passport_folder = project / "assets" / f"{asset_type}s" / asset_name
    for index, case in enumerate(report["cases"]):
        case["condition"] = f"Production condition {index + 1} for {tag}."
        case["angle"] = f"Angle {index + 1}"
        case["shot_size"] = f"Shot size {index + 1}"
        case["scene_lighting"] = f"Scene lighting {index + 1}"
        case["prompt"] = f"Complete test prompt {index + 1} for {tag}."
        result = passport_folder / f"{asset_name}-test-{index + 1}.png"
        result.write_bytes(f"test result {index + 1}".encode())
        case["result"] = str(result.relative_to(project))
        case["verdict"] = "pass"
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
    card["prompt_prep"]["timed_beats"] = [
        {"start_seconds": 2.0, "end_seconds": 2.6, "action": "Cal turns his eyes toward the cup."},
        {"start_seconds": 7.0, "end_seconds": 7.6, "action": "Cal returns his gaze to camera."},
    ]
    card["prompt_prep"]["known_risk"] = "Cal's eyes or hand identity drifts during the glance"
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


def test_init_seeds_machina_markdown_contract(tmp_path: Path) -> None:
    project = tmp_path / "studio"
    init_project(project, "Studio", "higgsfield", "internal")
    assert (project / "docs/breakdown.md").read_text(encoding="utf-8") == (
        "# Breakdown\n\n"
        "## Scenes\n\n"
        "| Scene ID | Summary | Location | Time of day | Characters | Props | Shot-card file | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    assert (project / "docs/bible.md").read_text(encoding="utf-8") == (
        "# Visual Bible\n\n## Asset boards\n\n## Style boards\n\n## Ban list\n"
    )
    assert (project / "docs/registry.md").read_text(encoding="utf-8") == (
        "# Asset Registry\n\n"
        "| Tag | Type | Version | Seed file | Scenes | Status |\n"
        "|---|---|---|---|---|---|\n"
    )
    assert (project / "docs/generation-log.md").read_text(encoding="utf-8") == (
        "# Generation Log\n\n"
        "| Shot ID | Prompt version | What changed | Result | Verdict |\n"
        "|---|---|---|---|---|\n"
    )
    studio_readme = (project / "docs/README").read_text(encoding="utf-8")
    assert "Studio" in studio_readme
    assert "Only `/selects/` is visible to the edit." in studio_readme
    assert "Nobody but the prompt engineer enters `/generations/`." in studio_readme
    assert "Reference files are never renamed; a new version is a new file." in studio_readme


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
        case["angle"] = f"Angle {index + 1}"
        case["shot_size"] = f"Shot size {index + 1}"
        case["scene_lighting"] = f"Scene lighting {index + 1}"
        case["prompt"] = f"Complete static test prompt {index + 1}."
        case["result"] = f"assets/tests/cal-test-{index + 1}.png"
    for case in report["cases"][:-1]:
        case["verdict"] = "pass"
    record_stress_test(project, "@cal", report)
    with pytest.raises(StudioError, match="exactly 10/10"):
        lock_asset(project, "@cal")


def test_stress_result_paths_must_exist_beside_the_passport(tmp_path: Path) -> None:
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
        case["angle"] = f"Angle {index + 1}"
        case["shot_size"] = f"Shot size {index + 1}"
        case["scene_lighting"] = f"Scene lighting {index + 1}"
        case["prompt"] = f"Complete static test prompt {index + 1}."
        case["result"] = f"assets/characters/cal/cal-test-{index + 1}.png"
        case["verdict"] = "pass"
    record_stress_test(project, "@cal", report)

    with pytest.raises(StudioError, match="stress-test result file is missing"):
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


def test_gate_rechecks_approved_visual_bible_references(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    (project / "references/lighting.ref").unlink()

    report = gate_shot(project, shot_path)

    assert not report.passed
    assert any("visual-bible reference is missing" in error for error in report.errors)


def test_compile_uses_next_highest_version_without_overwriting(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    first = compile_prompt(project, shot_path)
    assert first.name.endswith("v001.json")
    reserved = project / "prompts/compiled/SC01-SH01-v003.json"
    reserved.write_text('{"reserved": true}\n', encoding="utf-8")

    compiled = compile_prompt(project, shot_path)

    assert compiled.name.endswith("v004.json")
    assert reserved.read_text(encoding="utf-8") == '{"reserved": true}\n'


def test_render_validation_rejects_source_drift_after_compile(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_path = compile_prompt(project, shot_path)
    validated_project, prompt = validate_render_prompt(prompt_path)
    assert validated_project == project.resolve()
    assert prompt["shot_id"] == "SC01-SH01"

    card = read_json(shot_path)
    card["acting"] = "Cal gives the camera a restrained look."
    write_json(shot_path, card)

    with pytest.raises(StudioError, match="source state changed"):
        validate_render_prompt(prompt_path)


def test_render_validation_hashes_visual_bible_reference_content(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_path = compile_prompt(project, shot_path)
    (project / "references/lighting.ref").write_text("changed reference", encoding="utf-8")

    with pytest.raises(StudioError, match="source state changed"):
        validate_render_prompt(prompt_path)


def test_attempt_log_rejects_source_drift_after_compile(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_path = compile_prompt(project, shot_path)
    card = read_json(shot_path)
    card["acting"] = "Cal gives the camera a restrained look."
    write_json(shot_path, card)
    result = project / "generations/stale-prompt.bin"
    result.write_bytes(b"stale")

    with pytest.raises(StudioError, match="source state changed"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt_path,
            result_path=result,
            verdict="rejected",
            changed_block="initial",
            qa=None,
            allow_identical=False,
        )


def test_gate_rejects_state_variant_that_reuses_base_passport(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    card = read_json(shot_path)
    card["characters"] = [{"tag": "@cal", "state": "wet"}]
    write_json(shot_path, card)

    report = gate_shot(project, shot_path)

    assert not report.passed
    assert "state wet requires its own registered variant tag" in report.errors


def test_gate_accepts_locked_state_variant_with_its_own_tag(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    add_locked_asset(project, "@cal_wet", "character", variant_of="@cal")
    card = read_json(shot_path)
    card["characters"] = [{"tag": "@cal_wet", "state": "wet"}]
    write_json(shot_path, card)

    report = gate_shot(project, shot_path)

    assert report.passed


def test_gate_rejects_prop_state_that_reuses_base_passport(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    card = read_json(shot_path)
    card["props"] = [{"tag": "@cup", "state": "broken"}]
    write_json(shot_path, card)

    report = gate_shot(project, shot_path)

    assert not report.passed
    assert "state broken requires its own registered variant tag" in report.errors


def test_compile_rejects_overlapping_action_beats(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    card = read_json(shot_path)
    card["prompt_prep"]["timed_beats"] = [
        {"start_seconds": 2.0, "end_seconds": 2.6, "action": "Cal turns toward the cup."},
        {"start_seconds": 2.4, "end_seconds": 3.0, "action": "Cal looks back to camera."},
    ]
    write_json(shot_path, card)
    with pytest.raises(StudioError, match="must not overlap"):
        compile_prompt(project, shot_path)


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
    report["lock_decision"] = "approved"
    report["lock_decision_by"] = "Test Producer"
    for index, case in enumerate(report["cases"]):
        case["condition"] = f"Distinct commercial condition {index + 1}."
        case["angle"] = f"Angle {index + 1}"
        case["shot_size"] = f"Shot size {index + 1}"
        case["scene_lighting"] = f"Scene lighting {index + 1}"
        case["prompt"] = f"Complete static commercial test prompt {index + 1}."
        result = project / "assets/props/asset" / f"asset-test-{index + 1}.png"
        result.write_bytes(f"commercial result {index + 1}".encode())
        case["result"] = str(result.relative_to(project))
        case["verdict"] = "pass"
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
        changed_block="character_acting",
        qa=None,
        allow_identical=False,
    )
    assert second["detected_changed_blocks"] == ["character_acting"]

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
            changed_block="character_acting",
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
    assert selected.parent.name == "sc01"
    assert selected.read_bytes() == result.read_bytes()
    with pytest.raises(StudioError, match="will not be overwritten"):
        accept_take(project, "SC01-SH01", 1)


def test_attempt_log_enforces_one_changed_line(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_1 = compile_prompt(project, shot_path)
    result = project / "generations/attempt.bin"
    result.write_bytes(b"attempt")
    log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt_1,
        result_path=result,
        verdict="rejected",
        changed_block="initial",
        qa=None,
        allow_identical=False,
    )
    card = read_json(shot_path)
    card["acting"] = "Cal blinks once.\nCal tightens his jaw.\nCal exhales."
    write_json(shot_path, card)
    prompt_2 = compile_prompt(project, shot_path)
    with pytest.raises(StudioError, match="exactly one prompt line"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt_2,
            result_path=result,
            verdict="rejected",
            changed_block="character_acting",
            qa=None,
            allow_identical=False,
        )


def test_attempt_log_rejects_identical_seed_only_retry(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt = compile_prompt(project, shot_path)
    result_1 = project / "generations/attempt-1.bin"
    result_1.write_bytes(b"attempt one")
    log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt,
        result_path=result_1,
        verdict="rejected",
        changed_block="initial",
        qa=None,
        allow_identical=False,
    )
    result_2 = project / "generations/attempt-2.bin"
    result_2.write_bytes(b"attempt two")

    with pytest.raises(StudioError, match="exactly one prompt line"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt,
            result_path=result_2,
            verdict="rejected",
            changed_block="character_acting",
            qa=None,
            allow_identical=True,
        )


def test_attempt_log_rejects_delete_plus_insert_at_different_lines(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    card = read_json(shot_path)
    card["acting"] = "Cal breathes.\nCal looks at the cup."
    write_json(shot_path, card)
    prompt_1 = compile_prompt(project, shot_path)
    result_1 = project / "generations/attempt-1.bin"
    result_1.write_bytes(b"attempt one")
    log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt_1,
        result_path=result_1,
        verdict="rejected",
        changed_block="initial",
        qa=None,
        allow_identical=False,
    )

    card["acting"] = "Cal looks at the cup.\nCal steadies his gaze."
    write_json(shot_path, card)
    prompt_2 = compile_prompt(project, shot_path)
    result_2 = project / "generations/attempt-2.bin"
    result_2.write_bytes(b"attempt two")
    with pytest.raises(StudioError, match="exactly one prompt line"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt_2,
            result_path=result_2,
            verdict="rejected",
            changed_block="character_acting",
            qa=None,
            allow_identical=False,
        )


def test_attempt_log_detects_tampered_prompt_hashes(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_path = compile_prompt(project, shot_path)
    result = project / "generations/attempt.bin"
    result.write_bytes(b"attempt")
    prompt = read_json(prompt_path)
    prompt["blocks"][10]["text"] = "Silently rewritten audio block."
    write_json(prompt_path, prompt)
    with pytest.raises(StudioError, match="do not match the block text"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt_path,
            result_path=result,
            verdict="rejected",
            changed_block="initial",
            qa=None,
            allow_identical=False,
        )


def test_attempt_log_rejects_tampered_previous_prompt(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_1 = compile_prompt(project, shot_path)
    result_1 = project / "generations/attempt-1.bin"
    result_1.write_bytes(b"attempt one")
    log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt_1,
        result_path=result_1,
        verdict="rejected",
        changed_block="initial",
        qa=None,
        allow_identical=False,
    )

    card = read_json(shot_path)
    card["acting"] = "Cal blinks once and steadies his gaze."
    write_json(shot_path, card)
    prompt_2 = compile_prompt(project, shot_path)
    prompt_1_value = read_json(prompt_1)
    prompt_1_value["render_text"] = read_json(prompt_2)["render_text"]
    write_json(prompt_1, prompt_1_value)
    result_2 = project / "generations/attempt-2.bin"
    result_2.write_bytes(b"attempt two")

    with pytest.raises(StudioError, match="previous attempt prompt"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt_2,
            result_path=result_2,
            verdict="rejected",
            changed_block="character_acting",
            qa=None,
            allow_identical=False,
        )


def test_audit_rejects_tampered_logged_prompt(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_path = compile_prompt(project, shot_path)
    result = project / "generations/attempt.bin"
    result.write_bytes(b"attempt")
    log_attempt(
        project,
        shot_id="SC01-SH01",
        prompt_path=prompt_path,
        result_path=result,
        verdict="rejected",
        changed_block="initial",
        qa=None,
        allow_identical=False,
    )
    prompt = read_json(prompt_path)
    prompt["blocks"][0]["text"] = "Tampered scene context."
    write_json(prompt_path, prompt)

    report = audit_project(project)

    assert not report.passed
    assert any("logged prompt integrity failed" in error for error in report.errors)


def test_attempt_result_must_live_in_generations(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    prompt_path = compile_prompt(project, shot_path)
    stray = tmp_path / "stray.bin"
    stray.write_bytes(b"stray")
    with pytest.raises(StudioError, match="inside generations/"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt_path,
            result_path=stray,
            verdict="rejected",
            changed_block="initial",
            qa=None,
            allow_identical=False,
        )


def test_locked_asset_refuses_stress_rerecord(tmp_path: Path) -> None:
    project, _ = ready_project(tmp_path)
    report = read_json(
        project / "assets/characters/cal/stress-test.json",
    )
    with pytest.raises(StudioError, match="stress evidence is frozen"):
        record_stress_test(project, "@cal", report)


def test_audit_flags_locked_asset_with_degraded_evidence(tmp_path: Path) -> None:
    project, _ = ready_project(tmp_path)
    stress_path = project / "assets/characters/cal/stress-test.json"
    evidence = read_json(stress_path)
    evidence["cases"][0]["verdict"] = "miss"
    write_json(stress_path, evidence)
    report = audit_project(project)
    assert not report.passed
    assert any("exactly 10/10" in error for error in report.errors)


def test_gate_rechecks_locked_stress_result_files(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    evidence = read_json(project / "assets/characters/cal/stress-test.json")
    missing_result = project / evidence["cases"][0]["result"]
    missing_result.unlink()

    report = gate_shot(project, shot_path)

    assert not report.passed
    assert any("stress-test result file is missing" in error for error in report.errors)


def test_variant_of_requires_registered_base(tmp_path: Path) -> None:
    project = tmp_path / "production"
    init_project(project, "Test", "higgsfield", "internal")
    reference = project / "references/cal.ref"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text("reference", encoding="utf-8")
    with pytest.raises(StudioError, match="unregistered asset"):
        add_asset(
            project,
            tag="@cal_wet",
            asset_type="character",
            descriptor="Wet variant of Cal.",
            references=[reference],
            scenes=["SC01"],
            variant_of="@cal",
            rights_state="confirmed",
            real_person=False,
            identity_authorized=False,
        )


def test_board_decision_rejects_unknown_status(tmp_path: Path) -> None:
    board_path = tmp_path / "board.json"
    write_json(board_path, reference_board_template("style", "style"))
    with pytest.raises(StudioError, match="unsupported board status"):
        decide_reference_board(board_path, "maybe", "undecided")


def test_rejected_attempt_15_stops_further_iteration(tmp_path: Path) -> None:
    project, shot_path = ready_project(tmp_path)
    result = project / "generations/rejected.bin"
    result.write_bytes(b"rejected")
    row = None
    for attempt in range(1, 16):
        card = read_json(shot_path)
        card["acting"] = f"Cal holds his gaze for attempt {attempt}."
        write_json(shot_path, card)
        prompt = compile_prompt(project, shot_path)
        row = log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt,
            result_path=result,
            verdict="rejected",
            changed_block="initial" if attempt == 1 else "character_acting",
            qa=None,
            allow_identical=False,
        )
    assert row is not None and row["simplify_required"]
    card = read_json(shot_path)
    card["acting"] = "Cal holds his gaze for attempt 16."
    write_json(shot_path, card)
    prompt = compile_prompt(project, shot_path)
    with pytest.raises(StudioError, match="simplify or split"):
        log_attempt(
            project,
            shot_id="SC01-SH01",
            prompt_path=prompt,
            result_path=result,
            verdict="rejected",
            changed_block="character_acting",
            qa=None,
            allow_identical=False,
        )
