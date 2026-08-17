#!/usr/bin/env python3
"""Verify the pinned Machina submodule against the recorded manifest.

The upstream contract in docs/UPSTREAM.md requires deliberate updates: review the
changes, move the submodule pointer, compare all seven SKILL.md files, then record
the new state. This script makes that contract checkable. It fails when the
submodule commit or any upstream SKILL.md hash differs from docs/upstream-pin.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SUBMODULE = REPOSITORY / "upstream" / "machina-film-studio-skills"
DEFAULT_MANIFEST = REPOSITORY / "docs" / "upstream-pin.json"


def submodule_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(SUBMODULE), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def skill_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for skill_file in sorted(SUBMODULE.glob("skills/*/SKILL.md")):
        hashes[skill_file.parent.name] = hashlib.sha256(skill_file.read_bytes()).hexdigest()
    return hashes


def current_state() -> dict[str, object]:
    return {"submodule_commit": submodule_commit(), "skill_files": skill_hashes()}


def write_manifest(manifest_path: Path) -> int:
    manifest_path.write_text(json.dumps(current_state(), indent=2) + "\n")
    print(f"wrote {manifest_path}")
    return 0


def verify(manifest_path: Path) -> int:
    if not manifest_path.is_file():
        print(f"missing manifest: {manifest_path}", file=sys.stderr)
        print("run with --write after reviewing the upstream state", file=sys.stderr)
        return 1

    recorded = json.loads(manifest_path.read_text())
    actual = current_state()
    problems: list[str] = []

    if recorded.get("submodule_commit") != actual["submodule_commit"]:
        problems.append(
            "submodule commit moved: "
            f"recorded {recorded.get('submodule_commit')}, checked out {actual['submodule_commit']}"
        )

    recorded_files = recorded.get("skill_files", {})
    actual_files = actual["skill_files"]
    assert isinstance(actual_files, dict)
    for name in sorted(set(recorded_files) | set(actual_files)):
        if recorded_files.get(name) != actual_files.get(name):
            problems.append(f"SKILL.md drift in upstream skill: {name}")

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(
            "upstream moved without review: follow docs/UPSTREAM.md, compare all seven "
            "SKILL.md files, then rerun with --write to record the reviewed state",
            file=sys.stderr,
        )
        return 1

    print(f"upstream pin verified: {actual['submodule_commit']} with {len(actual_files)} skills")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or record the pinned upstream state")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--write", action="store_true", help="record the current reviewed state")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if args.write:
        return write_manifest(manifest_path)
    return verify(manifest_path)


if __name__ == "__main__":
    raise SystemExit(main())
