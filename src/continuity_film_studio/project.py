from __future__ import annotations

import difflib
import json
import shutil
from pathlib import Path
from typing import Any

from .io import (
    append_jsonl,
    read_json,
    read_jsonl,
    relative_to_project,
    sha256_file,
    sha256_text,
    utc_now,
    write_json,
)
from .models import (
    ASSET_TYPES,
    PROMPT_BLOCK_NAMES,
    QA_FIELDS,
    RIGHTS_STATES,
    VISUAL_BIBLE_DECISIONS,
    GateReport,
    StudioError,
    shot_asset_tags,
    stress_requirement,
    validate_shot_card,
)

PROJECT_DIRS = (
    "assets/characters",
    "assets/locations",
    "assets/props",
    "references/boards",
    "references/anti-references",
    "prompts/shot-cards",
    "prompts/compiled",
    "generations",
    "selects",
    "edit",
    "cleanup",
    "color",
    "sound",
    "master",
    "docs/breakdown",
    "config",
)


def ensure_project(project: Path) -> Path:
    project = project.resolve()
    if not (project / "config/project.json").is_file():
        raise StudioError(f"not a continuity film project: {project}")
    return project


def init_project(project: Path, name: str, provider: str, distribution: str) -> None:
    project = project.resolve()
    if project.exists() and any(project.iterdir()):
        raise StudioError(f"project directory is not empty: {project}")
    project.mkdir(parents=True, exist_ok=True)
    for directory in PROJECT_DIRS:
        (project / directory).mkdir(parents=True, exist_ok=True)

    config = {
        "schema_version": 1,
        "project_name": name,
        "created_at": utc_now(),
        "distribution": distribution,
        "providers": {
            provider: {
                "enabled": True,
                "video_model": None,
                "discover_live_catalog": True,
            }
        },
        "working_defaults": {
            "clip_seconds": 12,
            "frame_format": "16:9",
            "generation_mode": "text-to-video",
        },
        "stress_requirements": {
            "character": 10,
            "location": "explicit-pass",
            "prop": "explicit-pass",
        },
    }
    write_json(project / "config/project.json", config)
    write_json(project / "docs/registry.json", {"assets": []})
    write_json(
        project / "docs/visual-bible.json",
        {
            "status": "draft",
            "decision": None,
            "updated_at": utc_now(),
            "decisions": {key: "" for key in VISUAL_BIBLE_DECISIONS},
            "source_boards": {key: None for key in VISUAL_BIBLE_DECISIONS},
        },
    )
    write_json(
        project / "docs/rights.json",
        {
            "distribution": distribution,
            "source_footage": "unknown",
            "music": "unknown",
            "voices": "unknown",
            "notes": "Confirm every right before public or commercial distribution.",
        },
    )
    (project / "docs/generation-log.jsonl").touch()
    (project / "docs/breakdown.md").write_text(
        "# Breakdown\n\n"
        "## Scenes\n\n"
        "| Scene ID | Summary | Location | Time of day | Characters | Props | Shot-card file | Status |\n"
        "|---|---|---|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    (project / "docs/bible.md").write_text(
        "# Visual Bible\n\n## Asset boards\n\n## Style boards\n\n## Ban list\n",
        encoding="utf-8",
    )
    (project / "docs/registry.md").write_text(
        "# Asset Registry\n\n| Tag | Type | Version | Seed file | Scenes | Status |\n"
        "|---|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    (project / "docs/generation-log.md").write_text(
        "# Generation Log\n\n| Shot ID | Prompt version | What changed | Result | Verdict |\n"
        "|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    (project / "docs/README").write_text(
        f"# {name} studio\n\n"
        "## Folder map\n\n"
        "- `assets/` stores character, location, and prop passports and references.\n"
        "- `prompts/` stores shot cards and versioned generation prompts.\n"
        "- `generations/` stores raw attempts.\n"
        "- `selects/` stores approved takes for the edit.\n"
        "- `edit/`, `color/`, `sound/`, and `master/` form the finishing chain.\n"
        "- `docs/` stores the breakdown, visual bible, registry, and generation log.\n\n"
        "## Studio laws\n\n"
        "1. Only `/selects/` is visible to the edit.\n"
        "2. Nobody but the prompt engineer enters `/generations/`.\n"
        "3. Reference files are never renamed; a new version is a new file.\n",
        encoding="utf-8",
    )
    (project / "README.md").write_text(
        f"# {name}\n\nThis production is controlled by the continuity gates in `AGENTS.md`.\n",
        encoding="utf-8",
    )
    (project / "AGENTS.md").write_text(
        "# Production laws\n\n"
        "- No generation before the bible and every referenced asset are locked.\n"
        "- Never rename a reference file. A new version is a new file.\n"
        "- Raw output stays in generations/ and only the prompt engineer works there.\n"
        "- The edit stage reads only selects/. Only checklist-accepted takes enter it.\n"
        "- Change exactly one prompt line per attempt and keep every other line verbatim.\n"
        "- Rejected attempts 10 to 15 call for a simpler shot. Attempt 15 is the hard stop.\n"
        "- Keep required on-screen text for the edit.\n"
        "- Confirm identity and media rights before distribution.\n",
        encoding="utf-8",
    )


def shot_template(shot_id: str) -> dict[str, Any]:
    return {
        "shot_id": shot_id,
        "location": "@location",
        "time_of_day": "day",
        "characters": [{"tag": "@character", "state": "base"}],
        "props": [],
        "description": "One visible action.",
        "dialogue": "",
        "duration_seconds": 12,
        "complexity": "medium",
        "goal": "What changes for the viewer in this shot.",
        "task_verb": "reveals",
        "dramaturgy": "setup",
        "blocking": "Describe positions and movement in metres.",
        "acting": "Describe observable performance, not an emotion label alone.",
        "style_device": "none",
        "shot_size": "medium",
        "camera_movement": "static",
        "lens": "50mm",
        "angle": "eye level",
        "cut_type": "hard cut",
        "pace": "restrained",
        "transition": "cut",
        "prompt_prep": {
            "text_tasks": [],
            "timed_beats": [
                {
                    "start_seconds": 2.0,
                    "end_seconds": 2.6,
                    "action": "Replace with the first visible action beat.",
                },
                {
                    "start_seconds": 7.0,
                    "end_seconds": 7.6,
                    "action": "Replace with the resolving action beat.",
                },
            ],
            "known_risk": "Replace with the shot's concrete failure risk.",
        },
    }


def reference_board_template(name: str, board_type: str) -> dict[str, Any]:
    return {
        "name": name,
        "type": board_type,
        "status": "draft",
        "decision": None,
        "references": [],
        "anti_references": [],
        "updated_at": utc_now(),
    }


def decide_reference_board(path: Path, status: str, decision: str) -> None:
    if status not in {"approved", "revise", "rejected"}:
        raise StudioError(f"unsupported board status: {status}")
    board = read_json(path)
    if status == "approved":
        references = board.get("references", [])
        if not references:
            raise StudioError("an approved board requires at least one positive reference")
        uncaptioned = [row for row in references if not row.get("caption")]
        if uncaptioned:
            raise StudioError("every approved reference requires a caption")
        uncaptioned_anti = [row for row in board.get("anti_references", []) if not row.get("caption")]
        if uncaptioned_anti:
            raise StudioError("every anti-reference requires a caption")
        if not decision.strip():
            raise StudioError("an approved board requires a written decision")
    board["status"] = status
    board["decision"] = decision
    board["updated_at"] = utc_now()
    write_json(path, board)


def link_visual_bible_board(project: Path, key: str, board_path: Path) -> None:
    project = ensure_project(project)
    if key not in VISUAL_BIBLE_DECISIONS:
        raise StudioError(f"unsupported visual-bible decision: {key}")
    if not board_path.is_file():
        raise StudioError(f"reference board does not exist: {board_path}")
    try:
        relative_board = relative_to_project(project, board_path)
    except ValueError as exc:
        raise StudioError("reference board must live inside the project") from exc
    board = read_json(board_path)
    if board.get("status") != "approved" or not str(board.get("decision", "")).strip():
        raise StudioError("reference board must be approved with a written decision")
    for row in [*board.get("references", []), *board.get("anti_references", [])]:
        reference_value = row.get("file")
        if not reference_value:
            raise StudioError("every board entry requires a file")
        reference_path = (project / reference_value).resolve()
        try:
            reference_path.relative_to(project.resolve())
        except ValueError as exc:
            raise StudioError(f"board reference escapes the project: {reference_value}") from exc
        if not reference_path.is_file():
            raise StudioError(f"board reference is missing: {reference_value}")
    path = project / "docs/visual-bible.json"
    bible = read_json(path)
    bible["source_boards"][key] = relative_board
    bible["decisions"][key] = board["decision"]
    bible["updated_at"] = utc_now()
    write_json(path, bible)


def approve_visual_bible(project: Path) -> None:
    project = ensure_project(project)
    path = project / "docs/visual-bible.json"
    bible = read_json(path)
    missing = [
        key for key in VISUAL_BIBLE_DECISIONS if not str(bible.get("decisions", {}).get(key, "")).strip()
    ]
    if missing:
        raise StudioError(f"visual bible decisions are incomplete: {', '.join(missing)}")
    missing_boards = [key for key in VISUAL_BIBLE_DECISIONS if not bible.get("source_boards", {}).get(key)]
    if missing_boards:
        raise StudioError(f"visual bible source boards are incomplete: {', '.join(missing_boards)}")
    for key, board_value in bible["source_boards"].items():
        board_path = project / board_value
        if not board_path.is_file():
            raise StudioError(f"visual bible source board is missing for {key}: {board_value}")
        board = read_json(board_path)
        if board.get("status") != "approved" or board.get("decision") != bible["decisions"][key]:
            raise StudioError(f"visual bible decision drifted from source board: {key}")
    bible["status"] = "approved"
    bible["decision"] = "approved"
    bible["updated_at"] = utc_now()
    write_json(path, bible)


def _asset_dir(project: Path, asset_type: str, tag: str) -> Path:
    clean_tag = tag.removeprefix("@").replace("/", "-")
    plural = {"character": "characters", "location": "locations", "prop": "props"}[asset_type]
    return project / "assets" / plural / clean_tag


def add_asset(
    project: Path,
    *,
    tag: str,
    asset_type: str,
    descriptor: str,
    references: list[Path],
    scenes: list[str],
    variant_of: str | None,
    rights_state: str,
    real_person: bool,
    identity_authorized: bool,
) -> Path:
    project = ensure_project(project)
    if asset_type not in ASSET_TYPES:
        raise StudioError(f"unsupported asset type: {asset_type}")
    if rights_state not in RIGHTS_STATES:
        raise StudioError(f"unsupported rights state: {rights_state}")
    if not tag.startswith("@"):
        raise StudioError("asset tags must start with @")
    if not descriptor.strip():
        raise StudioError("asset descriptor cannot be empty")
    if not references:
        raise StudioError("at least one reference file is required")

    reference_paths: list[str] = []
    for reference in references:
        if not reference.is_file():
            raise StudioError(f"reference file does not exist: {reference}")
        try:
            reference_paths.append(relative_to_project(project, reference))
        except ValueError as exc:
            raise StudioError(f"reference must live inside the project: {reference}") from exc

    registry_path = project / "docs/registry.json"
    registry = read_json(registry_path)
    if any(row["tag"] == tag for row in registry["assets"]):
        raise StudioError(f"asset already exists: {tag}")
    if variant_of is not None and not any(row["tag"] == variant_of for row in registry["assets"]):
        raise StudioError(f"variant_of references an unregistered asset: {variant_of}")

    directory = _asset_dir(project, asset_type, tag)
    directory.mkdir(parents=True, exist_ok=True)
    passport_path = directory / "passport.json"
    passport = {
        "tag": tag,
        "type": asset_type,
        "version": 1,
        "status": "draft",
        "descriptor": descriptor,
        "reference_files": reference_paths,
        "variant_of": variant_of,
        "scenes": scenes,
        "rights": {
            "state": rights_state,
            "real_person": real_person,
            "identity_authorized": identity_authorized,
        },
        "created_at": utc_now(),
    }
    write_json(passport_path, passport)
    registry["assets"].append(
        {
            "tag": tag,
            "type": asset_type,
            "version": 1,
            "status": "draft",
            "passport_file": relative_to_project(project, passport_path),
            "stress_test_file": None,
            "scenes": scenes,
        }
    )
    registry["assets"].sort(key=lambda row: row["tag"])
    write_json(registry_path, registry)
    return passport_path


def stress_template(project: Path, tag: str) -> dict[str, Any]:
    project = ensure_project(project)
    row = registry_row(project, tag)
    required = stress_requirement(row["type"])
    case_count = required or 1
    return {
        "asset_tag": tag,
        "required_passes": required,
        "reviewer": "",
        "lock_decision": "pending",
        "lock_decision_by": "",
        "cases": [
            {
                "id": f"case-{index + 1:02d}",
                "condition": "Describe the production condition.",
                "angle": "Describe the test angle.",
                "shot_size": "Describe the test shot size.",
                "scene_lighting": "Describe the actual scene lighting.",
                "paired_asset": "",
                "prompt": "Paste the complete static-image test prompt.",
                "result": "Record the versioned result path.",
                "verdict": "pending",
            }
            for index in range(case_count)
        ],
        "notes": "",
    }


def record_stress_test(project: Path, tag: str, results: dict[str, Any]) -> Path:
    project = ensure_project(project)
    row = registry_row(project, tag)
    if row.get("status") == "locked":
        raise StudioError(
            f"asset is locked and its stress evidence is frozen: {tag}. "
            "Deliberately set the registry row and passport back to draft before re-recording."
        )
    if results.get("asset_tag") != tag:
        raise StudioError("stress-test asset tag does not match")
    if not isinstance(results.get("cases"), list):
        raise StudioError("stress-test cases must be a list")
    path = Path(project / row["passport_file"]).parent / "stress-test.json"
    results["recorded_at"] = utc_now()
    write_json(path, results)
    registry = read_json(project / "docs/registry.json")
    for candidate in registry["assets"]:
        if candidate["tag"] == tag:
            candidate["stress_test_file"] = relative_to_project(project, path)
    write_json(project / "docs/registry.json", registry)
    return path


def registry_row(project: Path, tag: str) -> dict[str, Any]:
    registry = read_json(project / "docs/registry.json")
    for row in registry["assets"]:
        if row["tag"] == tag:
            return row
    raise StudioError(f"asset is not registered: {tag}")


def _stress_evidence_errors(project: Path, row: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = report.get("cases", [])
    if not isinstance(cases, list):
        return ["stress-test cases must be a list"]

    required = stress_requirement(row["type"])
    passed = sum(isinstance(case, dict) and case.get("verdict") == "pass" for case in cases)
    if row["type"] == "character" and (len(cases) != required or passed != required):
        errors.append(f"character requires exactly 10/10 passing attempts: {passed}/{len(cases)}")
    if row["type"] != "character" and (not cases or passed != len(cases)):
        errors.append(f"asset test matrix must contain only passing cases: {passed}/{len(cases)}")
    if row["type"] != "character" and report.get("lock_decision") != "approved":
        errors.append("location and prop locks require an explicit approved decision")
    if row["type"] != "character" and not str(report.get("lock_decision_by", "")).strip():
        errors.append("location and prop locks require the decision-maker's name")
    if not str(report.get("reviewer", "")).strip():
        errors.append("stress test requires a named reviewer")

    identifiers = [str(case.get("id", "")).strip() for case in cases if isinstance(case, dict)]
    conditions = [str(case.get("condition", "")).strip() for case in cases if isinstance(case, dict)]
    if len(identifiers) != len(cases) or not all(identifiers) or len(set(identifiers)) != len(identifiers):
        errors.append("stress-test case ids must be non-empty and unique")
    if (
        len(conditions) != len(cases)
        or not all(conditions)
        or len(set(conditions)) != len(conditions)
        or any(condition == "Describe the production condition." for condition in conditions)
    ):
        errors.append("stress-test conditions must be unique production conditions, not placeholders")

    required_case_fields = ("angle", "shot_size", "scene_lighting", "prompt", "result")
    placeholders = {
        "Describe the test angle.",
        "Describe the test shot size.",
        "Describe the actual scene lighting.",
        "Paste the complete static-image test prompt.",
        "Record the versioned result path.",
    }
    passport_dir = (project / row["passport_file"]).parent.resolve()
    for case in cases:
        if not isinstance(case, dict):
            errors.append("every stress-test row must be an object")
            continue
        values = {field: str(case.get(field, "")).strip() for field in required_case_fields}
        if any(not values[field] for field in required_case_fields):
            errors.append("every stress-test row requires angle, shot size, lighting, prompt, and result")
            continue
        if any(values[field] in placeholders for field in required_case_fields):
            errors.append("stress-test rows must replace every matrix placeholder")
            continue
        result_value = Path(values["result"])
        if result_value.is_absolute():
            errors.append(f"stress-test result must be project-relative: {result_value}")
            continue
        result_path = (project / result_value).resolve()
        try:
            result_path.relative_to(passport_dir)
        except ValueError:
            errors.append(f"stress-test result must live beside the passport: {result_value}")
            continue
        if not result_path.is_file():
            errors.append(f"stress-test result file is missing: {result_value}")
    return list(dict.fromkeys(errors))


def _locked_asset_errors(project: Path, row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    passport_path = project / row["passport_file"]
    if not passport_path.is_file():
        return [f"missing passport: {row['tag']}"]
    passport = read_json(passport_path)
    if passport.get("status") != "locked":
        errors.append(f"registry/passport status mismatch: {row['tag']}")

    stress_value = row.get("stress_test_file")
    stress_path = project / stress_value if isinstance(stress_value, str) and stress_value else None
    if stress_path is None or not stress_path.is_file():
        errors.append(f"locked asset has no stress-test evidence: {row['tag']}")
    else:
        evidence = read_json(stress_path)
        errors.extend(
            f"locked asset evidence is invalid for {row['tag']}: {evidence_error}"
            for evidence_error in _stress_evidence_errors(project, row, evidence)
        )

    rights = passport.get("rights", {})
    if rights.get("state") == "denied":
        errors.append(f"asset rights are denied: {row['tag']}")
    if rights.get("real_person") and not rights.get("identity_authorized"):
        errors.append(f"real-person identity authorization is missing: {row['tag']}")
    distribution = read_json(project / "config/project.json").get("distribution")
    if distribution == "commercial" and rights.get("state") != "confirmed":
        errors.append(f"commercial projects require confirmed asset rights: {row['tag']}")
    return errors


def lock_asset(project: Path, tag: str) -> None:
    project = ensure_project(project)
    row = registry_row(project, tag)
    passport_path = project / row["passport_file"]
    passport = read_json(passport_path)
    if not row.get("stress_test_file"):
        raise StudioError(f"asset has no recorded stress test: {tag}")
    report = read_json(project / row["stress_test_file"])
    evidence_errors = _stress_evidence_errors(project, row, report)
    if evidence_errors:
        raise StudioError("; ".join(evidence_errors))

    rights = passport.get("rights", {})
    if rights.get("state") == "denied":
        raise StudioError(f"asset rights are denied: {tag}")
    if rights.get("real_person") and not rights.get("identity_authorized"):
        raise StudioError(f"real-person identity authorization is missing: {tag}")
    distribution = read_json(project / "config/project.json")["distribution"]
    if distribution == "commercial" and rights.get("state") != "confirmed":
        raise StudioError(f"commercial projects require confirmed asset rights: {tag}")

    passport["status"] = "locked"
    passport["locked_at"] = utc_now()
    write_json(passport_path, passport)
    registry = read_json(project / "docs/registry.json")
    for candidate in registry["assets"]:
        if candidate["tag"] == tag:
            candidate["status"] = "locked"
    write_json(project / "docs/registry.json", registry)


def _visual_bible_source_paths(project: Path, bible: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for board_value in bible.get("source_boards", {}).values():
        if not isinstance(board_value, str) or not board_value or Path(board_value).is_absolute():
            continue
        board_path = (project / board_value).resolve()
        try:
            board_path.relative_to(project)
        except ValueError:
            continue
        if not board_path.is_file():
            continue
        paths.append(board_path)
        board = read_json(board_path)
        for entry in [*board.get("references", []), *board.get("anti_references", [])]:
            if not isinstance(entry, dict):
                continue
            reference_value = entry.get("file")
            if (
                not isinstance(reference_value, str)
                or not reference_value
                or Path(reference_value).is_absolute()
            ):
                continue
            paths.append((project / reference_value).resolve())
    return paths


def _visual_bible_errors(project: Path, bible: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    decisions = bible.get("decisions", {})
    source_boards = bible.get("source_boards", {})
    if not isinstance(decisions, dict) or set(decisions) != set(VISUAL_BIBLE_DECISIONS):
        errors.append("visual bible must contain exactly the seven upstream decision categories")
        return errors
    if not isinstance(source_boards, dict) or set(source_boards) != set(VISUAL_BIBLE_DECISIONS):
        errors.append("visual bible must link exactly one source board for each decision category")
        return errors

    for key in VISUAL_BIBLE_DECISIONS:
        if not str(decisions.get(key, "")).strip():
            errors.append(f"visual-bible decision is empty: {key}")
        board_value = source_boards.get(key)
        if not isinstance(board_value, str) or not board_value or Path(board_value).is_absolute():
            errors.append(f"visual-bible source board path is invalid: {key}")
            continue
        board_path = (project / board_value).resolve()
        try:
            board_path.relative_to(project)
        except ValueError:
            errors.append(f"visual-bible source board escapes the project: {board_value}")
            continue
        if not board_path.is_file():
            errors.append(f"visual-bible source board is missing: {board_value}")
            continue
        board = read_json(board_path)
        if board.get("status") != "approved" or board.get("decision") != decisions.get(key):
            errors.append(f"visual-bible decision drifted from source board: {key}")
        references = board.get("references", [])
        anti_references = board.get("anti_references", [])
        if not isinstance(references, list) or not references:
            errors.append(f"visual-bible source board has no positive reference: {key}")
            continue
        if not isinstance(anti_references, list):
            errors.append(f"visual-bible anti-references must be a list: {key}")
            continue
        for entry in [*references, *anti_references]:
            if not isinstance(entry, dict) or not str(entry.get("caption", "")).strip():
                errors.append(f"visual-bible reference is missing its caption: {key}")
                continue
            reference_value = entry.get("file")
            if (
                not isinstance(reference_value, str)
                or not reference_value
                or Path(reference_value).is_absolute()
            ):
                errors.append(f"visual-bible reference path is invalid: {key}")
                continue
            reference_path = (project / reference_value).resolve()
            try:
                reference_path.relative_to(project)
            except ValueError:
                errors.append(f"visual-bible reference escapes the project: {reference_value}")
                continue
            if not reference_path.is_file():
                errors.append(f"visual-bible reference is missing: {reference_value}")
    return list(dict.fromkeys(errors))


def gate_shot(project: Path, shot_path: Path) -> GateReport:
    project = ensure_project(project)
    card = read_json(shot_path)
    errors = validate_shot_card(card)
    warnings: list[str] = []
    bible = read_json(project / "docs/visual-bible.json")
    if bible.get("status") != "approved":
        errors.append("visual bible is not approved")
    else:
        errors.extend(_visual_bible_errors(project, bible))

    checked_assets = shot_asset_tags(card)
    for tag in checked_assets:
        try:
            row = registry_row(project, tag)
        except StudioError as exc:
            errors.append(str(exc))
            continue
        if row.get("status") != "locked":
            errors.append(f"asset is not locked: {tag}")
        else:
            errors.extend(_locked_asset_errors(project, row))

    stateful_assets: list[dict[str, Any]] = []
    if isinstance(card.get("location"), dict):
        stateful_assets.append(card["location"])
    stateful_assets.extend(
        asset for asset in [*card.get("characters", []), *card.get("props", [])] if isinstance(asset, dict)
    )
    for asset in stateful_assets:
        if not asset.get("tag"):
            continue
        state = str(asset.get("state", "base")).strip() or "base"
        if state == "base":
            continue
        try:
            passport = _passport(project, asset["tag"])
        except StudioError:
            continue
        if not passport.get("variant_of"):
            errors.append(f"state {state} requires its own registered variant tag")

    if not card.get("prompt_prep", {}).get("text_tasks"):
        warnings.append("no edit-stage text tasks recorded; confirm that no required text appears in-frame")
    if card.get("complexity") == "high":
        warnings.append("high-complexity shot; confirm it still contains one action before generation")
    return GateReport(not errors, errors, warnings, checked_assets)


def _passport(project: Path, tag: str) -> dict[str, Any]:
    row = registry_row(project, tag)
    return read_json(project / row["passport_file"])


def _character_descriptors(project: Path, card: dict[str, Any]) -> str:
    lines = []
    for character in card["characters"]:
        passport = _passport(project, character["tag"])
        state = character.get("state", "base")
        lines.append(f"{character['tag']} [{state}]: {passport['descriptor']}")
    return "\n".join(lines)


def _prop_descriptors(project: Path, card: dict[str, Any]) -> str:
    if not card["props"]:
        return "No key prop passport is active in this shot."
    lines = []
    for prop in card["props"]:
        tag = prop if isinstance(prop, str) else prop["tag"]
        lines.append(f"{tag}: {_passport(project, tag)['descriptor']}")
    return "\n".join(lines)


def _render_text(blocks: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[{index + 1:02d} {block['name']}]\n{block['text']}" for index, block in enumerate(blocks)
    )


def _verify_prompt_integrity(prompt: dict[str, Any], prompt_path: Path) -> None:
    blocks = prompt.get("blocks", [])
    if (
        not isinstance(blocks, list)
        or tuple(block.get("name") for block in blocks if isinstance(block, dict)) != PROMPT_BLOCK_NAMES
    ):
        raise StudioError(f"compiled prompt integrity failed: invalid 15-block order in {prompt_path}")
    if any(not isinstance(block.get("text"), str) for block in blocks):
        raise StudioError(f"compiled prompt integrity failed: block text is invalid in {prompt_path}")
    computed_hashes = {block["name"]: sha256_text(block["text"]) for block in blocks}
    if computed_hashes != prompt.get("block_hashes"):
        raise StudioError(f"prompt block hashes do not match the block text, recompile: {prompt_path}")
    render_text = prompt.get("render_text", "")
    if render_text != _render_text(blocks) or sha256_text(render_text) != prompt.get("render_text_sha256"):
        raise StudioError(f"prompt render text does not match its blocks, recompile: {prompt_path}")


def _source_state_hashes(project: Path, shot_path: Path, card: dict[str, Any]) -> dict[str, str]:
    bible = read_json(project / "docs/visual-bible.json")
    source_paths = [
        project / "config/project.json",
        project / "docs/visual-bible.json",
        shot_path,
        *_visual_bible_source_paths(project, bible),
    ]
    for tag in shot_asset_tags(card):
        row = registry_row(project, tag)
        passport_path = project / row["passport_file"]
        source_paths.append(passport_path)
        passport = read_json(passport_path)
        source_paths.extend(project / reference for reference in passport.get("reference_files", []))
        if row.get("stress_test_file"):
            stress_path = project / row["stress_test_file"]
            source_paths.append(stress_path)
            stress = read_json(stress_path)
            source_paths.extend(
                project / case["result"]
                for case in stress.get("cases", [])
                if isinstance(case, dict) and isinstance(case.get("result"), str)
            )

    hashes: dict[str, str] = {}
    for source_path in source_paths:
        try:
            relative = relative_to_project(project, source_path)
        except ValueError as exc:
            raise StudioError(f"compiled prompt source escapes the project: {source_path}") from exc
        if not source_path.is_file():
            raise StudioError(f"compiled prompt source is missing: {relative}")
        hashes[relative] = sha256_file(source_path)
    return dict(sorted(hashes.items()))


def validate_render_prompt(prompt_path: Path) -> tuple[Path, dict[str, Any]]:
    prompt_path = prompt_path.resolve()
    project = ensure_project(prompt_path.parents[2])
    try:
        prompt_path.relative_to((project / "prompts/compiled").resolve())
    except ValueError as exc:
        raise StudioError("compiled prompt must live inside prompts/compiled/") from exc

    prompt = read_json(prompt_path)
    _verify_prompt_integrity(prompt, prompt_path)
    source_value = prompt.get("source_shot_card")
    if not isinstance(source_value, str) or not source_value:
        raise StudioError("compiled prompt integrity failed: source shot card is missing")
    source_shot = (project / source_value).resolve()
    try:
        source_shot.relative_to(project)
    except ValueError as exc:
        raise StudioError("compiled prompt source shot card escapes the project") from exc
    if not source_shot.is_file():
        raise StudioError(f"compiled prompt source shot card is missing: {source_shot}")
    gate = gate_shot(project, source_shot)
    if not gate.passed:
        raise StudioError("compiled prompt shot gate failed: " + "; ".join(gate.errors))
    card = read_json(source_shot)
    if prompt.get("shot_id") != card.get("shot_id"):
        raise StudioError("compiled prompt shot id no longer matches its source card")
    if prompt.get("source_hashes") != _source_state_hashes(project, source_shot, card):
        raise StudioError("compiled prompt source state changed; recompile before rendering")
    return project, prompt


def _single_changed_line(previous_text: str, current_text: str) -> str | None:
    previous_lines = previous_text.splitlines()
    current_lines = current_text.splitlines()
    matcher = difflib.SequenceMatcher(None, previous_lines, current_lines, autojunk=False)
    changes = [opcode for opcode in matcher.get_opcodes() if opcode[0] != "equal"]
    if len(changes) != 1:
        return None
    operation, old_start, old_end, new_start, new_end = changes[0]
    if operation != "replace" or old_end - old_start != 1 or new_end - new_start != 1:
        return None
    return current_lines[new_start]


def compile_prompt(project: Path, shot_path: Path) -> Path:
    project = ensure_project(project)
    report = gate_shot(project, shot_path)
    if not report.passed:
        raise StudioError("shot gate failed: " + "; ".join(report.errors))
    card = read_json(shot_path)
    bible = read_json(project / "docs/visual-bible.json")
    config = read_json(project / "config/project.json")
    location_tag = card["location"] if isinstance(card["location"], str) else card["location"]["tag"]
    location = _passport(project, location_tag)
    reference_lines = []
    attachments = []
    for tag in report.checked_assets:
        passport = _passport(project, tag)
        controls = {
            "character": "identity and wardrobe",
            "location": "geometry and atmosphere",
            "prop": "prop identity",
        }[passport["type"]]
        for reference in passport["reference_files"]:
            reference_lines.append(
                f"{reference} fixes {controls}. Motion, dialogue, and every other asset follow their own "
                "locked shot instructions."
            )
            attachments.append(
                {
                    "path": reference,
                    "asset_tag": tag,
                    "controls": controls,
                    "must_not_control": ["motion", "dialogue", "unrelated_assets"],
                }
            )

    cast_count = len(card["characters"])
    character_descriptors = _character_descriptors(project, card)
    prop_descriptors = _prop_descriptors(project, card)
    reference_summary = "\n".join(reference_lines)
    active_references = (
        f"Characters:\n{character_descriptors}\n\n"
        f"Location:\n{location_tag}: {location['descriptor']}\n\n"
        f"Props:\n{prop_descriptors}\n\n"
        f"Reference files:\n{reference_summary}"
    )
    prompt_prep = card.get("prompt_prep", {})
    timed_beats = prompt_prep.get("timed_beats", [])
    if not timed_beats:
        raise StudioError("shot requires timed_beats before prompt compilation")
    beat_lines: list[str] = []
    previous_end = 0.0
    for beat in timed_beats:
        start = beat.get("start_seconds")
        end = beat.get("end_seconds")
        action = str(beat.get("action", "")).strip()
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not action:
            raise StudioError("each timed beat requires numeric start/end seconds and an action")
        if start < 0 or end > card["duration_seconds"]:
            raise StudioError("each timed beat must stay inside the shot duration")
        if start < previous_end:
            raise StudioError("timed beats must be ordered and must not overlap")
        if not 0.3 <= end - start <= 0.8:
            raise StudioError("each action beat must last 0.3 to 0.8 seconds")
        if action.startswith("Replace with"):
            raise StudioError("replace every placeholder timed beat before prompt compilation")
        beat_lines.append(f"{start:.1f}-{end:.1f}s: {action}")
        previous_end = end
    known_risk = str(prompt_prep.get("known_risk", "")).strip()
    if not known_risk or known_risk.startswith("Replace with"):
        raise StudioError("shot requires a concrete known_risk before prompt compilation")
    defaults = config.get("working_defaults", {})
    dialogue_quoted = json.dumps(card["dialogue"], ensure_ascii=False)
    blocks = [
        {
            "name": "scene_context",
            "text": (
                f"EXACT {cast_count} CHARACTERS — NO DUPLICATES. Shot {card['shot_id']}. "
                f"Goal: {card['goal']}. One action: {card['task_verb']} — {card['description']}"
            ),
        },
        {"name": "active_references", "text": active_references},
        {
            "name": "location_map",
            "text": (
                f"{card['blocking']} State all positions and distances in metres. "
                "The camera stays on the established side of the action axis for the full shot."
            ),
        },
        {
            "name": "first_frame_blocking",
            "text": (
                f"First frame: {card['blocking']} Every character and prop begins already in place; "
                "the camera begins at its specified starting point."
            ),
        },
        {
            "name": "format_mode",
            "text": (
                f"Frame format: {defaults.get('frame_format', 'unspecified')}. "
                f"Generation mode: {defaults.get('generation_mode', 'unspecified')}. "
                f"Duration: {card['duration_seconds']} seconds."
            ),
        },
        {
            "name": "optics",
            "text": (
                f"Use one {card['lens']} lens for the full shot. "
                "Field of view remains constant within the shot; "
                f"the next change occurs only on the specified {card['cut_type']}."
            ),
        },
        {
            "name": "camera_body",
            "text": (
                f"Camera height and angle: {card['angle']}. Framing: {card['shot_size']}. "
                f"Support, movement, path, and stopping point: {card['camera_movement']}. "
                f"Pace: {card['pace']}; transition: {card['transition']}."
            ),
        },
        {"name": "action_timing", "text": "\n".join(beat_lines)},
        {
            "name": "physics",
            "text": (
                "Physical consequences persist. Damage remains visible; "
                "debris and props stay where they land."
            ),
        },
        {
            "name": "lighting",
            "text": (
                f"{location['descriptor']} Locked light direction: {bible['decisions']['lighting']} "
                f"Locked palette: {bible['decisions']['palette']}"
            ),
        },
        {
            "name": "audio",
            "text": (
                f"Ambience and in-frame sound: {bible['decisions']['sound']} "
                f"Dialogue verbatim: {dialogue_quoted}."
            ),
        },
        {"name": "character_acting", "text": card["acting"]},
        {
            "name": "style_prefix",
            "text": (
                f"Texture: {bible['decisions']['texture']}. Lighting: {bible['decisions']['lighting']}. "
                f"Optics: {bible['decisions']['optics']}. Style device: {card['style_device']}. "
                f"60:30:10 palette: {bible['decisions']['palette']}"
            ),
        },
        {
            "name": "quality_bar",
            "text": (
                "Exact reference match, coherent anatomy, stable materials, natural motion, "
                "persistent continuity, "
                "accurate lip-sync where dialogue is present, and artifact-free surfaces and objects."
            ),
        },
        {
            "name": "positive_constraints",
            "text": (
                "Every listed character appears once with stable identity, living eyes, "
                "natural hands and teeth, legible material detail, and continuous motion. "
                "The take fails review if this known risk appears: "
                f"{known_risk}."
            ),
        },
    ]
    if tuple(block["name"] for block in blocks) != PROMPT_BLOCK_NAMES:
        raise StudioError("compiled prompt block order drifted from the schema")
    render_text = _render_text(blocks)
    output_dir = project / "prompts/compiled"
    versions: list[int] = []
    prefix = f"{card['shot_id']}-v"
    for candidate in output_dir.glob(f"{prefix}*.json"):
        suffix = candidate.stem.removeprefix(prefix)
        if suffix.isdigit():
            versions.append(int(suffix))
    version = max(versions, default=0) + 1
    output = output_dir / f"{card['shot_id']}-v{version:03d}.json"
    if output.exists():
        raise StudioError(f"refusing to overwrite compiled prompt: {output}")
    write_json(
        output,
        {
            "shot_id": card["shot_id"],
            "version": version,
            "created_at": utc_now(),
            "source_shot_card": relative_to_project(project, shot_path),
            "source_hashes": _source_state_hashes(project, shot_path, card),
            "blocks": blocks,
            "block_hashes": {block["name"]: sha256_text(block["text"]) for block in blocks},
            "attachments": attachments,
            "render_text": render_text,
            "render_text_sha256": sha256_text(render_text),
        },
    )
    return output


def log_attempt(
    project: Path,
    *,
    shot_id: str,
    prompt_path: Path,
    result_path: Path,
    verdict: str,
    changed_block: str,
    qa: dict[str, bool] | None,
    allow_identical: bool,
) -> dict[str, Any]:
    project = ensure_project(project)
    if allow_identical:
        raise StudioError(
            "exactly one prompt line must be replaced; identical seed-only retries are disabled"
        )
    prompt_project, prompt = validate_render_prompt(prompt_path)
    if prompt_project != project:
        raise StudioError("compiled prompt belongs to a different continuity film project")
    if prompt.get("shot_id") != shot_id:
        raise StudioError("prompt shot id does not match")
    if not result_path.is_file():
        raise StudioError(f"result file does not exist: {result_path}")
    try:
        result_path.resolve().relative_to((project / "generations").resolve())
    except ValueError as exc:
        raise StudioError(f"result file must live inside generations/: {result_path}") from exc
    if verdict not in {"accepted", "rejected"}:
        raise StudioError("verdict must be accepted or rejected")
    if verdict == "accepted":
        if qa is None or any(qa.get(field) is not True for field in QA_FIELDS):
            raise StudioError("accepted attempts require every QA check to be true")

    log_path = project / "docs/generation-log.jsonl"
    attempts = [row for row in read_jsonl(log_path) if row.get("shot_id") == shot_id]
    if attempts and attempts[-1].get("simplify_required"):
        raise StudioError("attempt 15 was rejected; simplify or split the shot under a new shot id")
    changed_names: list[str] = []
    changed_line: str | None = None
    if attempts:
        previous_hashes = attempts[-1]["block_hashes"]
        changed_names = [
            name for name, digest in prompt["block_hashes"].items() if previous_hashes.get(name) != digest
        ]
        if len(changed_names) > 1:
            raise StudioError(f"more than one prompt block changed: {', '.join(changed_names)}")
        previous_prompt_path = project / attempts[-1]["prompt_file"]
        if not previous_prompt_path.is_file():
            raise StudioError(f"previous attempt prompt file is missing: {previous_prompt_path}")
        previous_prompt = read_json(previous_prompt_path)
        try:
            _verify_prompt_integrity(previous_prompt, previous_prompt_path)
        except StudioError as exc:
            raise StudioError(f"previous attempt prompt integrity failed: {exc}") from exc
        if previous_prompt.get("render_text_sha256") != attempts[-1].get(
            "prompt_sha256"
        ) or previous_prompt.get("block_hashes") != attempts[-1].get("block_hashes"):
            raise StudioError("previous attempt prompt no longer matches the immutable generation log")
        changed_line = _single_changed_line(previous_prompt.get("render_text", ""), prompt["render_text"])
        if changed_line is None:
            raise StudioError(
                "exactly one prompt line must be replaced per attempt, with every other line kept verbatim"
            )
        if changed_names and changed_block != changed_names[0]:
            raise StudioError(f"declared changed block does not match content: {changed_names[0]}")

    attempt = len(attempts) + 1
    row = {
        "shot_id": shot_id,
        "attempt": attempt,
        "created_at": utc_now(),
        "prompt_file": relative_to_project(project, prompt_path),
        "prompt_sha256": prompt["render_text_sha256"],
        "block_hashes": prompt["block_hashes"],
        "changed_block": changed_block,
        "detected_changed_blocks": changed_names,
        "changed_line": changed_line,
        "result_file": relative_to_project(project, result_path),
        "verdict": verdict,
        "qa": qa or {},
        "simplify_recommended": verdict == "rejected" and attempt >= 10,
        "simplify_required": verdict == "rejected" and attempt >= 15,
    }
    append_jsonl(log_path, row)
    return row


def accept_take(project: Path, shot_id: str, attempt_number: int) -> Path:
    project = ensure_project(project)
    rows = [
        row
        for row in read_jsonl(project / "docs/generation-log.jsonl")
        if row.get("shot_id") == shot_id and row.get("attempt") == attempt_number
    ]
    if not rows:
        raise StudioError("attempt not found")
    row = rows[-1]
    if row["verdict"] != "accepted" or any(row.get("qa", {}).get(field) is not True for field in QA_FIELDS):
        raise StudioError("take is not checklist-approved")
    source = Path(row["result_file"])
    if source.is_absolute():
        raise StudioError(f"attempt result lives outside the project and cannot be promoted: {source}")
    source = (project / source).resolve()
    try:
        source.relative_to((project / "generations").resolve())
    except ValueError as exc:
        raise StudioError(f"accepted result must live inside generations/: {source}") from exc
    if not source.is_file():
        raise StudioError(f"accepted result file is missing: {source}")
    scene = shot_id.split("-")[0].lower()
    output_dir = project / "selects" / scene
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{shot_id}-A{attempt_number:02d}{source.suffix.lower()}"
    if output.exists():
        raise StudioError(f"select already exists and will not be overwritten: {output}")
    shutil.copy2(source, output)
    return output


def _attempt_integrity_errors(project: Path, row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    prompt_value = row.get("prompt_file")
    if not isinstance(prompt_value, str) or not prompt_value or Path(prompt_value).is_absolute():
        return ["generation log has an invalid prompt path"]
    prompt_path = (project / prompt_value).resolve()
    try:
        prompt_path.relative_to((project / "prompts/compiled").resolve())
    except ValueError:
        return [f"logged prompt escapes prompts/compiled/: {prompt_value}"]
    if not prompt_path.is_file():
        return [f"logged prompt is missing: {prompt_value}"]
    prompt = read_json(prompt_path)
    try:
        _verify_prompt_integrity(prompt, prompt_path)
    except StudioError as exc:
        errors.append(f"logged prompt integrity failed: {exc}")
    if prompt.get("render_text_sha256") != row.get("prompt_sha256") or prompt.get("block_hashes") != row.get(
        "block_hashes"
    ):
        errors.append(f"logged prompt no longer matches the attempt record: {prompt_value}")

    result_value = row.get("result_file")
    if not isinstance(result_value, str) or not result_value or Path(result_value).is_absolute():
        errors.append("generation log has an invalid result path")
        return errors
    result_path = (project / result_value).resolve()
    try:
        result_path.relative_to((project / "generations").resolve())
    except ValueError:
        errors.append(f"logged result escapes generations/: {result_value}")
    else:
        if not result_path.is_file():
            errors.append(f"logged result is missing: {result_value}")
    return errors


def audit_project(project: Path) -> GateReport:
    project = ensure_project(project)
    errors: list[str] = []
    warnings: list[str] = []
    for directory in PROJECT_DIRS:
        if not (project / directory).is_dir():
            errors.append(f"missing project directory: {directory}")
    registry = read_json(project / "docs/registry.json")
    bible = read_json(project / "docs/visual-bible.json")
    if bible.get("status") != "approved":
        warnings.append("visual bible is still draft")
    else:
        errors.extend(_visual_bible_errors(project, bible))
    for row in registry.get("assets", []):
        passport_path = project / row["passport_file"]
        if not passport_path.is_file():
            errors.append(f"missing passport: {row['tag']}")
            continue
        passport = read_json(passport_path)
        for reference in passport.get("reference_files", []):
            if not (project / reference).is_file():
                errors.append(f"missing reference for {row['tag']}: {reference}")
        if row.get("status") == "locked":
            errors.extend(_locked_asset_errors(project, row))

    for shot_path in sorted((project / "prompts/shot-cards").glob("*.json")):
        errors.extend(f"{shot_path.name}: {error}" for error in validate_shot_card(read_json(shot_path)))
        readiness = gate_shot(project, shot_path)
        warnings.extend(f"{shot_path.name} is not generation-ready: {error}" for error in readiness.errors)
    attempts = read_jsonl(project / "docs/generation-log.jsonl")
    latest_by_shot: dict[str, dict[str, Any]] = {}
    for row in attempts:
        errors.extend(_attempt_integrity_errors(project, row))
        latest_by_shot[str(row.get("shot_id", ""))] = row
        if row.get("simplify_required"):
            warnings.append(f"{row['shot_id']} reached attempt {row['attempt']} and must be simplified")
    for shot, last in latest_by_shot.items():
        if last.get("verdict") == "rejected" and 10 <= int(last.get("attempt", 0)) < 15:
            warnings.append(
                f"{shot} is in the 10 to 15 stop-polishing window at attempt {last['attempt']}: "
                "prefer a simpler shot over more wording changes"
            )
    return GateReport(not errors, errors, warnings, [row["tag"] for row in registry.get("assets", [])])


def dump_report(report: GateReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)
