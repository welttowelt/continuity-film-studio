from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .io import append_jsonl, read_json, read_jsonl, relative_to_project, sha256_text, utc_now, write_json
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
        "stress_requirements": {"character": 10, "location": 8, "prop": 5},
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
    (project / "docs/visual-bible.md").write_text(
        "# Visual bible\n\nRecord references, anti-references, and the final written decisions here.\n",
        encoding="utf-8",
    )
    (project / "README.md").write_text(
        f"# {name}\n\nThis production is controlled by the continuity gates in `AGENTS.md`.\n",
        encoding="utf-8",
    )
    (project / "AGENTS.md").write_text(
        "# Production laws\n\n"
        "- No generation before the bible and every referenced asset are locked.\n"
        "- Never rename a reference file; add a version.\n"
        "- Raw output stays in generations. Only accepted takes enter selects.\n"
        "- Change no more than one prompt block per attempt. Simplify at attempt 15.\n"
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
        "duration_seconds": 6,
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
        "text_tasks": [],
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
    return {
        "asset_tag": tag,
        "required_passes": required,
        "reviewer": "",
        "cases": [
            {
                "id": f"case-{index + 1:02d}",
                "condition": "Describe the production condition.",
                "passed": False,
            }
            for index in range(required)
        ],
        "notes": "",
    }


def record_stress_test(project: Path, tag: str, results: dict[str, Any]) -> Path:
    project = ensure_project(project)
    row = registry_row(project, tag)
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


def lock_asset(project: Path, tag: str) -> None:
    project = ensure_project(project)
    row = registry_row(project, tag)
    passport_path = project / row["passport_file"]
    passport = read_json(passport_path)
    if not row.get("stress_test_file"):
        raise StudioError(f"asset has no recorded stress test: {tag}")
    report = read_json(project / row["stress_test_file"])
    cases = report.get("cases", [])
    required = stress_requirement(row["type"])
    passed = sum(bool(case.get("passed")) for case in cases)
    if len(cases) < required or passed != len(cases):
        raise StudioError(f"asset requires a full pass of at least {required} cases: {passed}/{len(cases)}")
    if not str(report.get("reviewer", "")).strip():
        raise StudioError("stress test requires a named reviewer")
    identifiers = [str(case.get("id", "")).strip() for case in cases]
    conditions = [str(case.get("condition", "")).strip() for case in cases]
    if not all(identifiers) or len(set(identifiers)) != len(identifiers):
        raise StudioError("stress-test case ids must be non-empty and unique")
    if (
        not all(conditions)
        or len(set(conditions)) != len(conditions)
        or any(condition == "Describe the production condition." for condition in conditions)
    ):
        raise StudioError("stress-test conditions must be unique production conditions, not placeholders")

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


def gate_shot(project: Path, shot_path: Path) -> GateReport:
    project = ensure_project(project)
    card = read_json(shot_path)
    errors = validate_shot_card(card)
    warnings: list[str] = []
    bible = read_json(project / "docs/visual-bible.json")
    if bible.get("status") != "approved":
        errors.append("visual bible is not approved")

    checked_assets = shot_asset_tags(card)
    for tag in checked_assets:
        try:
            row = registry_row(project, tag)
        except StudioError as exc:
            errors.append(str(exc))
            continue
        if row.get("status") != "locked":
            errors.append(f"asset is not locked: {tag}")

    if not card.get("text_tasks"):
        warnings.append("no edit-stage text tasks recorded; confirm that no required text appears in-frame")
    if card.get("duration_seconds", 0) > 15 and card.get("complexity") == "high":
        warnings.append("long, high-complexity shot; consider splitting before attempt 15")
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


def compile_prompt(project: Path, shot_path: Path) -> Path:
    project = ensure_project(project)
    report = gate_shot(project, shot_path)
    if not report.passed:
        raise StudioError("shot gate failed: " + "; ".join(report.errors))
    card = read_json(shot_path)
    bible = read_json(project / "docs/visual-bible.json")
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
                f"{reference} controls {controls}; it must not override motion, dialogue, "
                "or unrelated assets."
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
    blocks = [
        {
            "name": "shot_contract",
            "text": (
                f"{card['duration_seconds']} seconds. One action only: "
                f"{card['task_verb']}. {card['description']}"
            ),
        },
        {"name": "exact_cast", "text": f"EXACT {cast_count} CHARACTERS. Each listed character appears once."},
        {"name": "character_passports", "text": _character_descriptors(project, card)},
        {
            "name": "location_passport",
            "text": f"{location_tag}: {location['descriptor']} Time: {card['time_of_day']}.",
        },
        {"name": "prop_passports", "text": _prop_descriptors(project, card)},
        {
            "name": "composition_and_blocking",
            "text": f"{card['shot_size']}; {card['angle']}. {card['blocking']}",
        },
        {"name": "timed_action_beats", "text": card.get("timed_beats", card["description"])},
        {"name": "acting_and_performance", "text": card["acting"]},
        {
            "name": "dialogue_and_sound",
            "text": (
                f"Dialogue verbatim: {card['dialogue']!r}. Sound direction: {bible['decisions']['sound']}"
            ),
        },
        {
            "name": "camera_and_lens",
            "text": (
                f"One {card['lens']} lens. {card['camera_movement']}. "
                f"{card['cut_type']}; {card['pace']}; {card['transition']}."
            ),
        },
        {"name": "lighting", "text": bible["decisions"]["lighting"]},
        {
            "name": "physics_and_continuity",
            "text": (
                "Preserve damage, debris, wardrobe state, prop position, and screen direction "
                "for the full shot."
            ),
        },
        {
            "name": "style_and_texture",
            "text": (
                f"{bible['decisions']['style']} {bible['decisions']['texture']} "
                f"Style device: {card['style_device']}."
            ),
        },
        {"name": "palette_60_30_10", "text": bible["decisions"]["palette"]},
        {"name": "reference_roles_and_boundaries", "text": "\n".join(reference_lines)},
    ]
    if tuple(block["name"] for block in blocks) != PROMPT_BLOCK_NAMES:
        raise StudioError("compiled prompt block order drifted from the schema")
    render_text = "\n\n".join(
        f"[{index + 1:02d} {block['name']}]\n{block['text']}" for index, block in enumerate(blocks)
    )
    output_dir = project / "prompts/compiled"
    existing = sorted(output_dir.glob(f"{card['shot_id']}-v*.json"))
    version = len(existing) + 1
    output = output_dir / f"{card['shot_id']}-v{version:03d}.json"
    write_json(
        output,
        {
            "shot_id": card["shot_id"],
            "version": version,
            "created_at": utc_now(),
            "source_shot_card": relative_to_project(project, shot_path),
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
    prompt = read_json(prompt_path)
    if prompt.get("shot_id") != shot_id:
        raise StudioError("prompt shot id does not match")
    if not result_path.is_file():
        raise StudioError(f"result file does not exist: {result_path}")
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
    if attempts:
        previous_hashes = attempts[-1]["block_hashes"]
        changed_names = [
            name for name, digest in prompt["block_hashes"].items() if previous_hashes.get(name) != digest
        ]
        if len(changed_names) > 1:
            raise StudioError(f"more than one prompt block changed: {', '.join(changed_names)}")
        if not changed_names and not allow_identical:
            raise StudioError("no prompt block changed; use --allow-identical for a seed-only rerun")
        if changed_names and changed_block != changed_names[0]:
            raise StudioError(f"declared changed block does not match content: {changed_names[0]}")

    attempt = len(attempts) + 1
    try:
        result_value = relative_to_project(project, result_path)
    except ValueError:
        result_value = str(result_path.resolve())
    row = {
        "shot_id": shot_id,
        "attempt": attempt,
        "created_at": utc_now(),
        "prompt_file": relative_to_project(project, prompt_path),
        "prompt_sha256": prompt["render_text_sha256"],
        "block_hashes": prompt["block_hashes"],
        "changed_block": changed_block,
        "detected_changed_blocks": changed_names,
        "result_file": result_value,
        "verdict": verdict,
        "qa": qa or {},
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
    if not source.is_absolute():
        source = project / source
    if not source.is_file():
        raise StudioError(f"accepted result file is missing: {source}")
    output = project / "selects" / f"{shot_id}-A{attempt_number:02d}{source.suffix.lower()}"
    if output.exists():
        raise StudioError(f"select already exists and will not be overwritten: {output}")
    shutil.copy2(source, output)
    return output


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
    for row in registry.get("assets", []):
        passport_path = project / row["passport_file"]
        if not passport_path.is_file():
            errors.append(f"missing passport: {row['tag']}")
            continue
        passport = read_json(passport_path)
        for reference in passport.get("reference_files", []):
            if not (project / reference).is_file():
                errors.append(f"missing reference for {row['tag']}: {reference}")
        if row.get("status") == "locked" and passport.get("status") != "locked":
            errors.append(f"registry/passport status mismatch: {row['tag']}")

    for shot_path in sorted((project / "prompts/shot-cards").glob("*.json")):
        errors.extend(f"{shot_path.name}: {error}" for error in validate_shot_card(read_json(shot_path)))
        readiness = gate_shot(project, shot_path)
        warnings.extend(f"{shot_path.name} is not generation-ready: {error}" for error in readiness.errors)
    attempts = read_jsonl(project / "docs/generation-log.jsonl")
    for row in attempts:
        if row.get("simplify_required"):
            warnings.append(f"{row['shot_id']} reached attempt {row['attempt']} and must be simplified")
    return GateReport(not errors, errors, warnings, [row["tag"] for row in registry.get("assets", [])])


def dump_report(report: GateReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)
