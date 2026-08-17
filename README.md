# Continuity Film Studio

A provider-aware enforcement layer for [Machina's seven film-studio
skills](https://github.com/machina-exm/film-studio-skills). The upstream skills run the creative workflow. This
repository records their approved decisions as enforceable project state: shot cards, visual locks, asset
passports, stress tests, generation gates, fixed prompt blocks, immutable attempt logs, and checklist-controlled
selects.

This repository is deliberately separate from `natural-faceswap-workflow`. Face swapping modifies existing
footage. This lane plans and generates original shots while keeping characters, locations, props, camera rules,
and state changes consistent across a production.

## Architecture

The video model remembers no prior actor, location, or prop, so the production files hold that continuity.
The named model and platform can change without changing the system.

The repository pins Machina's unmodified upstream skills as a Git submodule. It adds one local skill,
`continuity-film-enforcer`, plus a tested CLI. The overlay mirrors approved state into JSON, validates it, and
preserves an audit trail. It adds no eighth creative stage and never silently converts upstream Markdown.

The marketing claims are not treated as evidence. This project does **not** claim that a workflow has a $2M
budget, that a specific model is exclusive to one provider, or that a model can reliably one-shot a finished
30-second ad. Those are benchmarks to test on representative shots.

## What is implemented

- Machina's exact seven upstream skills, pinned rather than reconstructed
- One local enforcement skill that maps their outputs into deterministic gates
- A 22-field shot-card schema
- Written visual-bible approval
- Versioned character, location, prop, and state-variant passports
- Rights and real-person authorization gates
- Exactly 10/10 character stress tests
- Completed all-pass matrices and an explicit decision for location and prop locks
- A hard scene gate: no compiled generation prompt until every referenced asset is locked
- Machina's exact 15-block positive prompt order
- 10 to 15 second shots and 0.3 to 0.8 second action beats
- One-line-change enforcement between attempts, recomputed from the compiled prompt text
- Version allocation that never reuses or overwrites an existing compiled prompt
- Automatic “simplify the shot” flag on rejected attempt 15, with audit warnings from attempt 10
- Checklist-controlled promotion from `generations/` into per-scene `selects/` folders
- A read-only project audit that re-verifies visual references and locked-asset stress evidence
- A pinned-upstream drift guard, `scripts/check_upstream_pin.py`, enforced in CI
- A Higgsfield adapter that discovers the live catalog instead of hardcoding model names

Editing, cleanup, color, sound, and mastering remain human-approved stages.

## Quick start

Clone with the pinned upstream source:

```bash
git clone --recurse-submodules <repository-url>
cd continuity-film-studio
```

```bash
uv sync --extra dev
uv run continuity-film init productions/demo --name "Demo" --provider higgsfield
uv run continuity-film shot-template productions/demo --shot-id SC01-SH01
uv run continuity-film audit productions/demo
```

**Claude Code and Codex need no install step.** The repository ships `.claude/skills/` and `.agents/skills/`
with relative symlinks to all eight skills (Machina's seven plus the enforcer). Sessions started inside a
recursive clone discover them project-scoped, without changing either global skill library. Symlinks require a
POSIX checkout.

The first audit is expected to show draft state. Run the upstream workflow in this order:

```text
setup
  -> studio-init
  -> film-breakdown
  -> reference-board
  -> asset-passport
  -> stress-test
  -> shot-prompt
```

See [docs/UPSTREAM.md](docs/UPSTREAM.md) for provenance and the Markdown-to-JSON boundary,
[docs/WORKFLOW.md](docs/WORKFLOW.md) for the gates, and [docs/HIGGSFIELD.md](docs/HIGGSFIELD.md) for the provider
boundary.

## Higgsfield

Machina's skills are provider-neutral and explicitly ask which stack the project uses. Higgsfield is an optional
render adapter at the edge. The production files remain the source of continuity truth.

Install and authenticate the official CLI only when you are ready to generate:

```bash
npm install -g @higgsfield/cli
higgsfield auth login
uv run continuity-film higgsfield-doctor
uv run continuity-film higgsfield-models
```

`higgsfield-render` previews the exact argument array by default. It submits a billable job only with
`--execute`.

## Rights and private data

Do not commit production media, identity references, provider credentials, or tokens. Commercial projects
require confirmed rights on each asset. Real-person passports require explicit identity authorization. Source
footage, voices, music, and distribution permissions still require a human rights review before release.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/check_upstream_pin.py
```

The last command verifies that the checked-out submodule still matches the reviewed pin in
`docs/upstream-pin.json`. After a deliberate upstream review, rerun it with `--write` to record the new state.
