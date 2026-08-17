---
name: film-asset-passport
description: Create versioned, registry-backed passports for AI-film characters, locations, props, and visible state variants. Use when a production needs identity continuity, fixed descriptors, reference files, scene coverage, likeness authorization, or explicit draft-versus-locked asset state.
---

# Film Asset Passport

Create one stable identity record per asset and visible state.

## Procedure

1. Assign a stable tag such as `@cal`, `@cal_wet`, `@kitchen_night`, or `@red_phone`.
2. Put the exhaustive descriptor in a text file. Do not shorten it for later prompts.
3. Place immutable reference files inside the project. Never rename them after use.
4. Register the draft passport:

   ```bash
   continuity-film asset-add <project> \
     --tag @cal \
     --type character \
     --descriptor-file <descriptor.txt> \
     --reference <project-relative-reference>
   ```

5. Add `--variant-of @cal` for wet, bloody, damaged, aged, or wardrobe-change variants.
6. Add `--real-person --identity-authorized` only after confirming likeness permission. Use `--rights confirmed`
   for commercial assets with cleared source rights.
7. Keep the passport at `draft`. Only `$film-stress-test` may justify locking it.

Create neutral front, three-quarter, profile, back, and close views when the chosen image model supports reliable
reference sheets. Do not regenerate a locked seed reference to repair a motion prompt.
