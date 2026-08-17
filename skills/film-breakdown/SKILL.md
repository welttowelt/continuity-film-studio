---
name: film-breakdown
description: Convert a treatment, script, ad concept, or scene into one-action 22-field shot cards and a separate edit-stage text task list. Use before reference gathering or prompt writing whenever an AI-film production needs scene IDs, asset tags, performance, camera, timing, and edit intent made explicit.
---

# Film Breakdown

Turn the idea into mechanically compilable shot cards.

## Procedure

1. Work scene by scene. Create a card with:

   ```bash
   continuity-film shot-template <project> --shot-id SC01-SH01
   ```

2. Fill every field. Keep `shot_id` stable and encode scene plus shot in it.
3. Give each card one visible action. Put a sequence of actions into separate cards.
4. Use registered asset tags for the location, characters, state variants, and props. If a state changes identity or
   wardrobe visibly, plan a separate asset tag.
5. Copy dialogue verbatim. Describe acting as visible behavior.
6. Use one lens per shot. Express blocking and location geometry in concrete positions or distances.
7. Put required signs, phone text, titles, captions, and UI copy in `text_tasks`; do not ask the video model to
   render them.
8. Run `continuity-film gate <project> --shot <card>`. Draft-asset errors are expected until the passport stages.

Route next to `$film-reference-board`.
