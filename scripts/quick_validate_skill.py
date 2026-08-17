#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_frontmatter(source: str) -> dict[str, str] | None:
    text = source.lstrip("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fields: dict[str, str] = {}
    current: str | None = None
    for line in text[4:end].split("\n"):
        if not line.strip():
            continue
        if line.startswith((" ", "\t")):
            if current is None:
                return None
            fields[current] = f"{fields[current]} {line.strip()}"
            continue
        key, separator, value = line.partition(":")
        key = key.strip()
        if not separator or not key or any(character.isspace() for character in key):
            return None
        current = key
        fields[current] = value.strip()
    return fields


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
    fields = parse_frontmatter(source)
    if fields is None:
        print(f"invalid frontmatter: {skill}", file=sys.stderr)
        return 1
    for required in ("name", "description"):
        if not fields.get(required):
            print(f"frontmatter is missing a non-empty {required}: {skill}", file=sys.stderr)
            return 1
    if fields["name"] != skill.name:
        print(f"name mismatch: frontmatter says {fields['name']!r} in {skill}", file=sys.stderr)
        return 1
    if not args.source_only and not (skill / "agents/openai.yaml").is_file():
        print(f"missing agents/openai.yaml: {skill}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
