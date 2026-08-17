---
name: film-setup
description: Configure an AI-film production's providers, model-discovery policy, distribution mode, and rights boundary. Use when starting a new continuity-heavy video project, changing generation providers, checking Higgsfield readiness, or deciding which capabilities must be verified before production.
---

# Film Setup

Establish the production boundary before creating assets or prompts.

## Procedure

1. Record the project name, intended distribution (`internal` or `commercial`), target formats, and provider in
   `config/project.json`.
2. Record source-footage, music, voice, likeness, and distribution rights in `docs/rights.json`. Never store
   credentials in the project.
3. Treat model names and capabilities as live data. For Higgsfield, run:

   ```bash
   continuity-film higgsfield-doctor
   continuity-film higgsfield-models
   ```

4. Choose a representative shot and define acceptance criteria before spending credits. Test resolution,
   duration, lip sync, sound, reference count, identity repeatability, and neighboring-shot continuity.
5. Store the selected live model in `config/project.json` only after the test. Keep the production registry
   provider-neutral.

## Boundaries

- Do not repeat exclusivity, budget, or reliability claims from marketing copy as verified facts.
- Do not authenticate for the user. Ask them to run `higgsfield auth login` when the doctor reports no session.
- Do not submit a generation unless the user authorizes the billable render.
- Route next to `$film-studio-init` after configuration.
