from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .io import read_json, write_json
from .models import StudioError
from .project import (
    accept_take,
    add_asset,
    approve_visual_bible,
    audit_project,
    compile_prompt,
    decide_reference_board,
    dump_report,
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
from .providers import execute_higgsfield, higgsfield_args, higgsfield_doctor, higgsfield_model_catalog


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="continuity-film", description="Continuity-first AI film tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create a production workspace")
    init.add_argument("project")
    init.add_argument("--name", required=True)
    init.add_argument("--provider", default="higgsfield")
    init.add_argument("--distribution", choices=("internal", "commercial"), default="internal")

    shot = subparsers.add_parser("shot-template", help="write a 22-field shot card")
    shot.add_argument("project")
    shot.add_argument("--shot-id", required=True)
    shot.add_argument("--output")

    board = subparsers.add_parser("board-template", help="write a reference-board template")
    board.add_argument("project")
    board.add_argument("--name", required=True)
    board.add_argument("--type", required=True)
    board.add_argument("--output")

    decide = subparsers.add_parser("board-decide", help="record a written board decision")
    decide.add_argument("board")
    decide.add_argument("--status", choices=("approved", "revise", "rejected"), required=True)
    decide.add_argument("--decision", required=True)

    bible = subparsers.add_parser("bible-approve", help="approve a complete visual bible")
    bible.add_argument("project")

    bible_link = subparsers.add_parser("bible-link", help="link an approved board into the visual bible")
    bible_link.add_argument("project")
    bible_link.add_argument("--key", required=True)
    bible_link.add_argument("--board", required=True)

    asset = subparsers.add_parser("asset-add", help="register a draft asset passport")
    asset.add_argument("project")
    asset.add_argument("--tag", required=True)
    asset.add_argument("--type", choices=("character", "location", "prop"), required=True)
    asset.add_argument("--descriptor-file", required=True)
    asset.add_argument("--reference", action="append", required=True)
    asset.add_argument("--scene", action="append", default=[])
    asset.add_argument("--variant-of")
    asset.add_argument("--rights", choices=("unknown", "confirmed", "denied"), default="unknown")
    asset.add_argument("--real-person", action="store_true")
    asset.add_argument("--identity-authorized", action="store_true")

    stress = subparsers.add_parser("stress-template", help="write an asset stress-test matrix")
    stress.add_argument("project")
    stress.add_argument("--tag", required=True)
    stress.add_argument("--output")

    stress_record = subparsers.add_parser("stress-record", help="record stress-test results")
    stress_record.add_argument("project")
    stress_record.add_argument("--tag", required=True)
    stress_record.add_argument("--results", required=True)

    asset_lock = subparsers.add_parser("asset-lock", help="lock a fully passing asset")
    asset_lock.add_argument("project")
    asset_lock.add_argument("--tag", required=True)

    gate = subparsers.add_parser("gate", help="check whether a shot may generate")
    gate.add_argument("project")
    gate.add_argument("--shot", required=True)

    compile_command = subparsers.add_parser("compile", help="compile the fixed 15-block prompt")
    compile_command.add_argument("project")
    compile_command.add_argument("--shot", required=True)

    attempt = subparsers.add_parser("attempt", help="append an immutable generation attempt")
    attempt.add_argument("project")
    attempt.add_argument("--shot-id", required=True)
    attempt.add_argument("--prompt", required=True)
    attempt.add_argument("--result", required=True)
    attempt.add_argument("--verdict", choices=("accepted", "rejected"), required=True)
    attempt.add_argument("--changed-block", default="initial")
    attempt.add_argument("--qa-file")
    attempt.add_argument("--allow-identical", action="store_true")

    accept = subparsers.add_parser("accept", help="copy a checklist-approved attempt into selects")
    accept.add_argument("project")
    accept.add_argument("--shot-id", required=True)
    accept.add_argument("--attempt", type=int, required=True)

    audit = subparsers.add_parser("audit", help="audit production structure and invariants")
    audit.add_argument("project")

    subparsers.add_parser("higgsfield-doctor", help="check official CLI installation and auth")
    subparsers.add_parser("higgsfield-models", help="print the live official model catalog")

    render = subparsers.add_parser("higgsfield-render", help="preview or execute a provider submission")
    render.add_argument("--prompt", required=True)
    render.add_argument("--model", required=True)
    render.add_argument("--attachment-map")
    render.add_argument("--execute", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
    command = args.command
    if command == "init":
        init_project(_path(args.project), args.name, args.provider, args.distribution)
        print(_path(args.project))
    elif command == "shot-template":
        project = _path(args.project)
        output = (
            _path(args.output) if args.output else project / "prompts/shot-cards" / f"{args.shot_id}.json"
        )
        write_json(output, shot_template(args.shot_id))
        print(output)
    elif command == "board-template":
        project = _path(args.project)
        output = _path(args.output) if args.output else project / "references/boards" / f"{args.name}.json"
        write_json(output, reference_board_template(args.name, args.type))
        print(output)
    elif command == "board-decide":
        decide_reference_board(_path(args.board), args.status, args.decision)
        print(_path(args.board))
    elif command == "bible-approve":
        approve_visual_bible(_path(args.project))
        print("visual bible approved")
    elif command == "bible-link":
        link_visual_bible_board(_path(args.project), args.key, _path(args.board))
        print(f"linked {args.key}")
    elif command == "asset-add":
        descriptor = _path(args.descriptor_file).read_text(encoding="utf-8")
        output = add_asset(
            _path(args.project),
            tag=args.tag,
            asset_type=args.type,
            descriptor=descriptor,
            references=[_path(value) for value in args.reference],
            scenes=args.scene,
            variant_of=args.variant_of,
            rights_state=args.rights,
            real_person=args.real_person,
            identity_authorized=args.identity_authorized,
        )
        print(output)
    elif command == "stress-template":
        project = _path(args.project)
        output = (
            _path(args.output)
            if args.output
            else project / "assets" / f"{args.tag.removeprefix('@')}-stress.json"
        )
        write_json(output, stress_template(project, args.tag))
        print(output)
    elif command == "stress-record":
        output = record_stress_test(_path(args.project), args.tag, read_json(_path(args.results)))
        print(output)
    elif command == "asset-lock":
        lock_asset(_path(args.project), args.tag)
        print(f"locked {args.tag}")
    elif command == "gate":
        report = gate_shot(_path(args.project), _path(args.shot))
        print(dump_report(report))
        return 0 if report.passed else 2
    elif command == "compile":
        print(compile_prompt(_path(args.project), _path(args.shot)))
    elif command == "attempt":
        qa = read_json(_path(args.qa_file)) if args.qa_file else None
        row = log_attempt(
            _path(args.project),
            shot_id=args.shot_id,
            prompt_path=_path(args.prompt),
            result_path=_path(args.result),
            verdict=args.verdict,
            changed_block=args.changed_block,
            qa=qa,
            allow_identical=args.allow_identical,
        )
        print(json.dumps(row, indent=2, sort_keys=True))
    elif command == "accept":
        print(accept_take(_path(args.project), args.shot_id, args.attempt))
    elif command == "audit":
        report = audit_project(_path(args.project))
        print(dump_report(report))
        return 0 if report.passed else 2
    elif command == "higgsfield-doctor":
        print(json.dumps(higgsfield_doctor(), indent=2, sort_keys=True))
    elif command == "higgsfield-models":
        print(json.dumps(higgsfield_model_catalog(), indent=2, sort_keys=True))
    elif command == "higgsfield-render":
        attachment_map = read_json(_path(args.attachment_map)) if args.attachment_map else None
        if args.execute:
            return execute_higgsfield(_path(args.prompt), args.model, attachment_map)
        print(json.dumps(higgsfield_args(_path(args.prompt), args.model, attachment_map), indent=2))
    return 0


def main() -> None:
    try:
        raise SystemExit(run(build_parser().parse_args()))
    except StudioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
