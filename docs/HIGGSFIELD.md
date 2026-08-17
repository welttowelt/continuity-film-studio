# Higgsfield adapter

Higgsfield is one generation provider. Production truth lives in the project registry and passports, which stay
portable if the video model changes.

## Related public projects

- Official CLI: <https://github.com/higgsfield-ai/cli>
- Official skills: <https://github.com/higgsfield-ai/skills>
- Machina film-studio skills: <https://github.com/machina-exm/film-studio-skills>
- npm package: <https://www.npmjs.com/package/@higgsfield/cli>

The seven pre-production skills come from Machina rather than Higgsfield's official skills repository. They are
provider-neutral: `setup` asks which image and video stack the user operates and does not recommend a model. This
repository pins Machina's upstream and adds deterministic continuity checks. It calls the official Higgsfield CLI
only when Higgsfield is the selected render provider.

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

The flags above are only examples. Use `higgsfield model get <model> --json` and never guess them. Preview the
exact argument array without spending credits:

```bash
continuity-film higgsfield-render \
  --prompt productions/demo/prompts/compiled/SC01-SH01-v001.json \
  --model MODEL_FROM_LIVE_CATALOG \
  --attachment-map attachment-map.json
```

The adapter refuses to submit a prompt with unmapped reference files. Add `--execute` only when a generation is
authorized. It invokes the official binary with an argument array rather than shell interpolation, so prompt text
is not executed by a shell.
