# HeyGen adapter

HeyGen is the talking-shot provider. It renders a consistent presenter speaking the shot card's verbatim
dialogue. Higgsfield remains the lane for generated cinematography. Production truth stays in the project
files either way.

## What a HeyGen avatar is in this system

A HeyGen avatar is a character whose visual identity the platform already stabilizes across renders. The
continuity system still owns everything around it. The character keeps a passport, a registry row, and a lock
before any scene opens. Descriptors stay verbatim, prompts stay versioned, attempts stay logged.

The studio convention is one standard presenter per production, configured once per project. Ralph, a
platform-generated fictional persona, is the standard presenter in this studio's productions. Real-person
avatars remain subject to the identity gate: a passport with `real_person` set requires explicit identity
authorization before it can lock, and an avatar modeled on a colleague stays unusable until that person has
approved it.

## Configure

The API key lives only in the environment. Create one in the HeyGen app settings and export it as
`HEYGEN_API_KEY`. The key value never belongs in project files, and `heygen-configure` stores ids only.

```bash
export HEYGEN_API_KEY=...   # from app.heygen.com settings
uv run continuity-film heygen-doctor
uv run continuity-film heygen-avatars
uv run continuity-film heygen-voices
uv run continuity-film heygen-configure PROJECT --avatar-id LOOK_ID --voice-id VOICE_ID \
  --avatar-name Ralph --platform-persona
```

`heygen-avatars` lists look-level ids. A look id is what `POST /v3/videos` accepts as `avatar_id`, so pick the
look, then configure it. Treat the catalog as live data and rediscover ids instead of trusting old notes.

Configuration requires an identity declaration and refuses anything else. `--platform-persona` marks a
platform-generated fictional presenter. `--real-person` marks a presenter modeled on an actual person and
requires `--identity-authorized`, the same rule the asset registry applies to real-person passports. The
declaration is stored beside the ids and rechecked at render time, so an unauthorized real-person presenter
cannot reach a billable submission.

## Voice tuning

`heygen-configure` also accepts optional voice tuning, stored beside the presenter ids in
`config/project.json`:

```bash
uv run continuity-film heygen-configure PROJECT --avatar-id LOOK_ID --voice-id VOICE_ID \
  --avatar-name Ralph --platform-persona \
  --speed 1.1 --pitch -2 --expressiveness high \
  --engine-settings-json '{"model": "eleven_multilingual_v2", "stability": 0.35, "similarity_boost": 0.8}'
```

`--speed` (0.5 to 1.5) and `--pitch` (-50 to 50 semitones) become the payload's `voice_settings`.
`--engine-settings-json` is an ElevenLabs passthrough inside `voice_settings.engine_settings` and accepts
`model`, `stability`, `similarity_boost`, `style`, and `use_speaker_boost`; the numeric fields are
range-checked to 0..1 and `engine_type` is always `elevenlabs`. HeyGen accepts `stability` values of only 0,
0.5, or 1 with the `eleven_v3` model. `--expressiveness high|medium|low` becomes the payload's top-level
`expressiveness` field and applies to photo avatars.

Tuning lives in the project configuration, so it sits inside the hashed source state exactly like the
presenter ids: a compiled prompt renders with the tuning it was validated against, and retuning means
reconfiguring and recompiling. The stored values are also rechecked when the payload is built, so a
hand-edited configuration cannot push an out-of-range value into a billable submission.

## Render

```bash
uv run continuity-film heygen-render --prompt PROJECT/prompts/compiled/SC01-SH01-v001.json
```

The default is a preview: the exact JSON payload prints and nothing is submitted. The payload is built only
after `validate_render_prompt` passes, which reruns prompt integrity, the live shot gate, and the hashed
source state. A drifted card, a draft asset, or a tampered prompt refuses to render on either provider.

The presenter always comes from the project configuration, which sits inside the hashed source state. There
are no render-time avatar or voice overrides, so the face and voice that render are exactly the ones the
compiled prompt was validated against. Changing the presenter means reconfiguring and recompiling.

The lane also refuses silent shots. A card with an empty `dialogue` field belongs to the Higgsfield lane.

Submit only with explicit authorization, then poll and pull the result into the project:

```bash
uv run continuity-film heygen-render --prompt ... --execute
uv run continuity-film heygen-status --video-id VIDEO_ID
uv run continuity-film heygen-download PROJECT --video-id VIDEO_ID
```

Every executed submission is recorded in `docs/heygen-submissions.jsonl` with its video id, shot id, prompt
hash, and presenter ids. `heygen-download` refuses any video id without a submission record, downloads to a
temporary file, and moves it into `generations/heygen/` only when the transfer completes, never overwriting.
Account videos that never passed the gate cannot enter the pipeline through this tool.

## Assets and rights

Uploaded HeyGen assets, voices, and avatar looks are account resources, and ids are account-specific, so they
belong in each production's `config/project.json` (which stays out of version control under `productions/`)
rather than in this repository. Voice clones of a real person follow the same rule as real-person avatars:
explicit authorization from that person before commercial use, plus the platform's own consent flow.
