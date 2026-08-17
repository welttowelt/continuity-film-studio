---
name: film-studio-init
description: Create the versioned file tree and production laws for a continuity-first AI film project. Use when the user wants a new film, ad, trailer, scene, or episodic video workspace with separate assets, references, raw generations, accepted takes, edit, color, sound, and master stages.
---

# Film Studio Init

Create the project before writing prompts.

## Procedure

1. Pick a new, empty production directory.
2. Run:

   ```bash
   continuity-film init <project-directory> --name "<project name>" --provider higgsfield
   ```

   Add `--distribution commercial` only when that is the intended release mode.

3. Confirm the tree contains `assets`, `references`, `prompts`, `generations`, `selects`, `edit`, `cleanup`,
   `color`, `sound`, `master`, `docs`, and `config`.
4. Preserve the generated `AGENTS.md`. It contains the folder and gate laws inherited by future agents.
5. Run `continuity-film audit <project-directory>` and treat the initial draft warnings as the production queue.

## Folder laws

- Never rename a reference file; add a version.
- Keep raw generations out of `selects`.
- Keep production media, identity references, and credentials out of Git.
- Route next to `$film-breakdown`.
