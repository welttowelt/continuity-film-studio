# Machina upstream contract

The creative workflow comes from [machina-exm/film-studio-skills](https://github.com/machina-exm/film-studio-skills).
This repository pins it as the `upstream/machina-film-studio-skills` Git submodule at commit
`314517381b1be72c1404c068a9e37a064ec4215c`.

The seven upstream skills stay unmodified:

```text
setup -> studio-init -> film-breakdown -> reference-board
      -> asset-passport -> stress-test -> shot-prompt
```

There was no root license file at the pinned revision. The submodule keeps provenance and avoids presenting an
edited copy as local work. Confirm upstream licensing before redistributing or vendoring its contents.

## Enforcement overlay

Machina's skills write Markdown production documents. The local `continuity-film-enforcer` skill and
`continuity-film` CLI add machine-checkable JSON without replacing those documents.

| Machina source | Enforced mirror |
|---|---|
| `docs/breakdown.md`, `prompts/scNN-shot-cards.md` | `prompts/shot-cards/*.json` |
| reference boards, `docs/bible.md` | `references/boards/*.json`, `docs/visual-bible.json` |
| asset dossiers, `docs/registry.md` | `assets/*/*/passport.json`, `docs/registry.json` |
| passport stress-test matrix | `assets/*/*/stress-test.json` |
| versioned shot prompt | `prompts/compiled/*.json` |
| `docs/generation-log.md` | `docs/generation-log.jsonl` |

The bridge is currently explicit rather than an automatic Markdown parser. Copy approved decisions into the JSON
templates, preserve canonical descriptors verbatim, and run the gate. Do not report the two representations as
synchronized until they have been checked.

## Install and verify

Claude Code sessions started inside this repository need no install: `.claude/skills/` symlinks all eight skills
project-scoped. For Codex:

```bash
npx skills add ./upstream/machina-film-studio-skills
uv run python scripts/install_skills.py
uv run python scripts/quick_validate_skill.py skills/continuity-film-enforcer
```

Select all seven upstream skills in the installer. The second command installs only the local enforcement overlay
as a symlink and refuses to replace an existing skill.

## Update upstream deliberately

Do not float to the latest upstream commit inside a production. Review changes first, update the submodule pointer,
compare all seven `SKILL.md` files, run the full test suite, and then record the new commit in this document.

The recorded pin lives in `docs/upstream-pin.json` (submodule commit plus a sha256 per upstream `SKILL.md`).
`scripts/check_upstream_pin.py` verifies the checkout against it, CI runs the check on every push, and
`--write` records the newly reviewed state after an intentional update.
