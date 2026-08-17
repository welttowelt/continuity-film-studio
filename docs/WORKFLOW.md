# Workflow and gates

## Stage sequence

1. Configure providers, distribution mode, and rights boundary.
2. Initialize the studio tree.
3. Convert the treatment or script into one 22-field card per shot.
4. Caption references and anti-references; write a decision for each board.
5. Approve the visual bible in writing.
6. Create one passport per character, location, prop, and visible state variant.
7. Stress-test each passport in its real production conditions.
8. Lock only fully passing passports.
9. Compile a generation prompt only after the shot gate passes.
10. Generate, change zero or one prompt block, and log every attempt.
11. Promote only checklist-approved takes into `selects/`.
12. Finish picture, cleanup, color, sound, captions, and masters with human review.

## Gate A: visual lock

`bible-approve` requires approved source boards and written decisions for style, palette, lighting, optics,
camera movement, texture, edit tempo, and sound. Reference-board approval requires at least one positive
reference, a caption on every positive and negative reference, a written decision, and files that still exist
inside the production.

## Gate B: scene-open

`gate` and `compile` inspect the shot card and every asset tag it uses. The scene opens only when:

- all 22 required shot fields are present;
- the visual bible is approved;
- every character, location, and prop is registered and locked;
- every locked asset has a full stress-test pass;
- denied rights and unauthorized real-person identities are absent;
- commercial productions use only rights-confirmed assets.

## Prompt contract

The compiler emits these blocks in a fixed order:

1. shot contract
2. exact cast
3. character passports
4. location passport
5. prop passports
6. composition and blocking
7. timed action beats
8. acting and performance
9. dialogue and sound
10. camera and lens
11. lighting
12. physics and continuity
13. style and texture
14. 60:30:10 palette
15. reference roles and boundaries

Passports are copied verbatim. References say what they control and what they must not override. Required
on-screen text stays in `text_tasks` for the edit rather than inside the generation prompt.

## Iteration contract

The immutable JSONL log stores the prompt hash and all 15 block hashes. After the first attempt, an entry is
rejected if more than one block changed. An identical prompt needs an explicit seed-only override. A rejected
attempt 15 is marked `simplify_required` and attempt 16 is blocked; split the shot, remove an action, or change the
angle under a new shot ID.

## Acceptance contract

An accepted attempt requires explicit checks for reference match, artifacts, camera, performance, and the cut to
neighboring shots. Only then can `accept` copy the file from `generations/` into `selects/`. Existing selects are
never overwritten.
