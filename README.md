# Continuity Film Studio

A provider-aware production system for continuity-heavy AI video. It turns the useful part of the “$2M video
pipeline” article into enforceable project state: shot cards, written visual decisions, asset passports, stress
tests, generation gates, fixed prompt blocks, immutable attempt logs, and checklist-controlled selects.

This repository is deliberately separate from `natural-faceswap-workflow`. Face swapping modifies existing
footage. This lane plans and generates original shots while keeping characters, locations, props, camera rules,
and state changes consistent across a production.

## The useful idea

The article's strongest claim is architectural: a video model does not remember yesterday's actor, location, or
prop. The production files must hold that memory. The named model and platform can change without changing the
system.

The marketing claims are not treated as evidence. This project does **not** claim that a workflow has a $2M
budget, that a specific model is exclusive to one provider, or that a model can reliably one-shot a finished
30-second ad. Those are benchmarks to test on representative shots.

## What is implemented

- Seven agent skills covering setup through generation
- A 22-field shot-card schema
- Written visual-bible approval
- Versioned character, location, prop, and state-variant passports
- Rights and real-person authorization gates
- 10/10 character, 8/8 location, and 5/5 prop stress-test locks
- A hard scene gate: no compiled generation prompt until every referenced asset is locked
- A fixed 15-block positive prompt compiler
- One-block-change enforcement between attempts
- Automatic “simplify the shot” flag on rejected attempt 15
- Checklist-controlled promotion from `generations/` to `selects/`
- A read-only project audit
- A Higgsfield adapter that discovers the live catalog instead of hardcoding model names

Editing, cleanup, color, sound, and mastering remain human-approved stages.

## Quick start

```bash
uv sync --extra dev
uv run continuity-film init productions/demo --name "Demo" --provider higgsfield
uv run continuity-film shot-template productions/demo --shot-id SC01-SH01
uv run continuity-film audit productions/demo
```

The first audit is expected to show draft state. Complete the production in this order:

```text
film-setup
  -> film-studio-init
  -> film-breakdown
  -> film-reference-board
  -> film-asset-passport
  -> film-stress-test
  -> film-shot-prompt
```

Install the seven local skills into Codex without copying or forking them:

```bash
uv run python scripts/install_skills.py
```

The installer refuses to replace an existing skill with the same name.

See [docs/WORKFLOW.md](docs/WORKFLOW.md) for the gates and [docs/HIGGSFIELD.md](docs/HIGGSFIELD.md) for the
provider boundary.

## Higgsfield

The official CLI and public skill repository exist, but their current surface differs from the supplied article.
The official repository currently publishes generation, identity, product-photo, and marketplace-card skills;
the seven continuity skills in this repository are our own production layer.

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
```
