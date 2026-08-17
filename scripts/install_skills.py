#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install continuity film skills as local symlinks")
    parser.add_argument("--target", default="~/.codex/skills")
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    source_root = repository / "skills"
    target_root = Path(args.target).expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    for source in sorted(source_root.iterdir()):
        if not (source / "SKILL.md").is_file():
            continue
        target = target_root / source.name
        if target.is_symlink() and target.resolve() == source.resolve():
            print(f"already installed: {source.name}")
            continue
        if target.exists() or target.is_symlink():
            raise SystemExit(f"refusing to replace existing skill: {target}")
        target.symlink_to(source, target_is_directory=True)
        print(f"installed: {source.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
