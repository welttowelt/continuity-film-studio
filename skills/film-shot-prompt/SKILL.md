---
name: film-shot-prompt
description: Gate a shot against the visual bible and locked asset registry, compile its fixed 15-block generation prompt, enforce one-block iterations, log attempts, and promote checklist-approved takes. Use when an AI-film shot is ready to generate, revise, compare, accept, or send to Higgsfield or another provider.
---

# Film Shot Prompt

Generate only from locked production state.

## Procedure

1. Run the gate:

   ```bash
   continuity-film gate <project> --shot <shot-card.json>
   ```

   Stop on any error. Do not bypass a draft asset or visual bible.

2. Compile the provider-neutral 15-block prompt:

   ```bash
   continuity-film compile <project> --shot <shot-card.json>
   ```

3. Inspect the live model schema and create an attachment map from every compiled reference path to that model's
   media flag. Preview provider arguments and omit `--execute` until a billable render is authorized:

   ```bash
   continuity-film higgsfield-render \
     --prompt <compiled.json> \
     --model <live-model> \
     --attachment-map <attachment-map.json>
   ```

4. Save raw output in `generations/` and log the attempt. On later attempts, change zero or one named prompt
   block; use the identical override only for a seed-only rerun.
5. At rejected attempt 15, simplify or split the shot. Do not keep polishing the same prompt.
6. Mark a take accepted only after reference, artifact, camera, performance, and neighboring-cut checks all pass.
7. Run `continuity-film accept` to copy that attempt into `selects/`. The editor sees `selects/`, never raw output.

Preserve original dialogue, passport descriptors, reference filenames, and prompt versions throughout.
