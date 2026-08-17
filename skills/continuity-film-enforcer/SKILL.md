---
name: continuity-film-enforcer
description: Enforce auditable continuity, asset-lock, prompt, iteration, and acceptance gates around a project produced with Machina's seven film-studio skills. Use after or alongside setup, studio-init, film-breakdown, reference-board, asset-passport, stress-test, and shot-prompt when the user wants deterministic checks, JSON state, provider-safe submission, or a production audit.
---

# Continuity Film Enforcer

Use Machina's seven installed skills as the creative workflow and this repository's `continuity-film` CLI as the
deterministic enforcement layer. Do not replace or reinterpret the upstream skill instructions.

## Route the work

Invoke the relevant upstream skill first:

1. `setup`
2. `studio-init`
3. `film-breakdown`
4. `reference-board`
5. `asset-passport`
6. `stress-test`
7. `shot-prompt`

Then mirror each approved decision into the corresponding JSON state before opening the next gate. The mapping is:

- `docs/breakdown.md` and shot cards -> `prompts/shot-cards/*.json`
- reference boards and `docs/bible.md` -> `references/boards/*.json` and `docs/visual-bible.json`
- asset dossiers and `docs/registry.md` -> `assets/passports/*.json` and `docs/registry.json`
- stress-test decisions -> `assets/stress-tests/*.json`
- generated prompt and review history -> `prompts/compiled/*.json` and `docs/generation-log.jsonl`

Do not claim that Markdown-to-JSON import is automatic. Translate the approved state explicitly, preserve all
descriptors verbatim, and run the CLI gate afterward.

## Enforce each boundary

Run commands from the `continuity-film-studio` repository with `uv run continuity-film`:

```bash
uv run continuity-film audit PROJECT
uv run continuity-film gate PROJECT SHOT_CARD
uv run continuity-film compile PROJECT SHOT_CARD
```

Generation stays closed until the visual bible is approved and every referenced asset is locked. Character locks
require exactly 10 passing attempts. Location and prop matrices require all listed cases to pass plus an explicit
approved decision. Commercial assets require confirmed rights; a real-person identity requires explicit
authorization.

The compiled prompt must contain Machina's exact 15 blocks in order. Each action beat lasts 0.3 to 0.8 seconds,
the shot contains one visible action, and the total shot duration stays between 10 and 15 seconds. Keep required
in-frame text in the edit task list.

## Iterate without losing the audit trail

Log every attempt. After the first attempt, change at most one of the 15 prompt blocks. Do not overwrite a prior
generation, prompt, or accepted select. At rejected attempt 15, simplify or split the shot under a new shot ID.

Promote a result into `selects/` only after reference match, artifact, camera, performance, and neighboring-cut QA
all pass. Report gate failures exactly; never describe a draft, submission preview, or unaccepted take as complete.

## Keep providers at the edge

Treat model catalogs as live data. For Higgsfield, discover the current catalog and inspect the model schema before
mapping attachments. Preview the argument array first. Submit a billable render only when the user explicitly
authorizes generation.
