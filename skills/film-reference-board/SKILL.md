---
name: film-reference-board
description: Turn supplied visual, camera, color, texture, edit, and sound references into captioned specification boards with anti-references and a written approved, revise, or rejected decision. Use when defining a film's visual bible or when a production has attractive images but no explicit rule for what each image controls.
---

# Film Reference Board

Use references as specifications, not decoration.

## Procedure

1. Create one board at a time:

   ```bash
   continuity-film board-template <project> --name lighting --type lighting
   ```

2. Add each file to `references` with a caption that states exactly what it controls.
3. Add rejected examples to `anti_references` with the specific failure to avoid.
4. Do not hunt for an image that confirms an imagined description. Start from an actual supplied or
   rights-cleared reference, then describe the usable property.
5. Close the board with a written decision:

   ```bash
   continuity-film board-decide <board.json> --status approved --decision "<fixed rule>"
   ```

6. Link each approved board to its visual-bible decision:

   ```bash
   continuity-film bible-link <project> --key lighting --board <project>/references/boards/lighting.json
   ```

   Repeat for style, palette, lighting, optics, camera movement, texture, edit tempo, and sound.
7. Run `continuity-film bible-approve <project>`. It refuses missing boards, missing files, or decision drift.

Do not call a verbal agreement locked. Route next to `$film-asset-passport`.
