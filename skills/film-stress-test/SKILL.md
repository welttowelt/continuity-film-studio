---
name: film-stress-test
description: Build and score static continuity tests for draft character, location, and prop passports before video generation. Use when an asset must survive production angles, shot sizes, scene lighting, co-stars, occlusion, hands, or interaction before its registry row can be locked.
---

# Film Stress Test

Test assets under the conditions that will break them in production.

## Procedure

1. Generate the required matrix:

   ```bash
   continuity-film stress-template <project> --tag @cal --output cal-stress.json
   ```

2. Replace placeholder conditions with the asset's actual angles, shot sizes, scene lighting, co-stars, props,
   occlusions, hands, and interactions from the breakdown.
3. Run cheap static-image tests before any video generation.
4. Inspect every case and record `passed: true` only when identity, geometry, costume/state, and interaction hold.
5. Record and lock:

   ```bash
   continuity-film stress-record <project> --tag @cal --results cal-stress.json
   continuity-film asset-lock <project> --tag @cal
   ```

Characters require at least 10/10, locations 8/8, and props 5/5. A partial pass stays draft. Do not average away a
failure that will appear in a real scene. Route to `$film-shot-prompt` only after every asset used by the shot is
locked.
