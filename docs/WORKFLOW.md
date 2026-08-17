# Workflow and gates

## Stage sequence

1. Run Machina's `setup` and configure the stack without storing secrets.
2. Run `studio-init` and initialize the studio tree.
3. Run `film-breakdown` and convert the treatment or script into one 22-field card per shot.
4. Run `reference-board`; caption references and anti-references and write a decision for each board.
5. Approve the visual bible in writing.
6. Run `asset-passport` for each character, location, prop, and visible state variant.
7. Run `stress-test` under the asset's real production conditions.
8. Lock only fully passing passports.
9. Run `shot-prompt`, mirror the approved shot state into JSON, and open the CLI gate.
10. Compile a generation prompt only after the shot gate passes.
11. Generate, change zero or one prompt block, and log every attempt.
12. Promote only checklist-approved takes into `selects/`.
13. Finish picture, cleanup, color, sound, captions, and masters with human review.

## Gate A: visual lock

`bible-approve` requires approved source boards and written decisions for style, palette, lighting, optics,
camera movement, texture, edit tempo, and sound. Reference-board approval requires at least one positive
reference, a caption on every positive and negative reference, a written decision, and files that still exist
inside the production.

## Gate B: scene-open

`gate` and `compile` inspect the shot card and every asset tag it uses. The scene opens only when:

- all 22 required shot fields are present;
- the shot runs for 10–15 seconds and contains one action;
- the visual bible is approved;
- every character, location, and prop is registered and locked;
- characters have exactly 10/10 passing stress-test attempts;
- every location and prop matrix row passes and the lock decision is explicitly approved;
- denied rights and unauthorized real-person identities are absent;
- commercial productions use only rights-confirmed assets.

## Prompt contract

The compiler emits these blocks in a fixed order:

1. scene context
2. active references
3. location map
4. first-frame blocking
5. format mode
6. optics
7. camera body
8. action timing
9. physics
10. lighting
11. audio
12. character acting
13. style prefix
14. quality bar
15. positive constraints

Passports are copied verbatim. The first block opens with `EXACT N CHARACTERS — NO DUPLICATES`. Action timing
uses 0.3–0.8 second beats. Prohibitions become positive visible constraints; there is no separate negative-prompt
section. Required on-screen text stays in `prompt_prep.text_tasks` for the edit rather than inside the generation
prompt. `prompt_prep` is enforcement metadata outside the three 22-field shot-card lanes.

## Iteration contract

The immutable JSONL log stores the prompt hash and all 15 block hashes. After the first attempt, an entry is
rejected if more than one block changed. An identical prompt needs an explicit seed-only override. A rejected
attempt 15 is marked `simplify_required` and attempt 16 is blocked; split the shot, remove an action, or change the
angle under a new shot ID.

## Acceptance contract

An accepted attempt requires explicit checks for reference match, artifacts, camera, performance, and the cut to
neighboring shots. Only then can `accept` copy the file from `generations/` into `selects/`. Existing selects are
never overwritten.
