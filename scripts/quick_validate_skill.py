#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill")
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="validate portable SKILL.md frontmatter without requiring Codex UI metadata",
    )
    args = parser.parse_args()
    skill = Path(args.skill)
    source = (skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", source, re.DOTALL)
    if not match:
        print(f"invalid frontmatter: {skill}", file=sys.stderr)
        return 1
    if match.group(1) != skill.name:
        print(f"name mismatch: {skill}", file=sys.stderr)
        return 1
    if not args.source_only and not (skill / "agents/openai.yaml").is_file():
        print(f"missing agents/openai.yaml: {skill}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
