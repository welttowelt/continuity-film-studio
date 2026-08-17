#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    skill = Path(sys.argv[1])
    source = (skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", source, re.DOTALL)
    if not match:
        print(f"invalid frontmatter: {skill}", file=sys.stderr)
        return 1
    if match.group(1) != skill.name:
        print(f"name mismatch: {skill}", file=sys.stderr)
        return 1
    if not (skill / "agents/openai.yaml").is_file():
        print(f"missing agents/openai.yaml: {skill}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
