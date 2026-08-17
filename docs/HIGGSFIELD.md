# Higgsfield adapter

Higgsfield is one generation provider, not the source of production truth. The project registry and passports
remain portable if the video model changes.

## Verified public surface

- Official CLI: <https://github.com/higgsfield-ai/cli>
- Official skills: <https://github.com/higgsfield-ai/skills>
- npm package: <https://www.npmjs.com/package/@higgsfield/cli>

The supplied article describes seven pre-production skills. The current official skills repository exposes a
different set aimed at generation, identity, product photography, and marketplace cards. This repository
therefore implements the continuity layer independently and calls the official CLI only at the render boundary.

## Setup

```bash
npm install -g @higgsfield/cli
higgsfield auth login
continuity-film higgsfield-doctor
```

Never store the resulting credentials in the production repo.

## Model selection

Treat model names and capabilities as live data:

```bash
continuity-film higgsfield-models
```

Select a model after inspecting the current catalog and running a representative shot test. Do not encode
“Seedance 2.5,” 1080p, 30 seconds, lip sync, or generated sound as a permanent pipeline assumption.

## Submission boundary

Inspect the chosen model schema and map every compiled reference to the corresponding live CLI media flag:

```json
{
  "references/characters/cal-front-v1.ref": "--image",
  "references/locations/kitchen-v1.ref": "--start-image"
}
```

The flags above are only examples. Use `higgsfield model get <model> --json`; do not guess them. Preview the exact
argument array without spending credits:

```bash
continuity-film higgsfield-render \
  --prompt productions/demo/prompts/compiled/SC01-SH01-v001.json \
  --model MODEL_FROM_LIVE_CATALOG \
  --attachment-map attachment-map.json
```

The adapter refuses to submit a prompt with unmapped reference files. Add `--execute` only when a generation is
authorized. It invokes the official binary with an argument array rather than shell interpolation, so prompt text
is not executed by a shell.
