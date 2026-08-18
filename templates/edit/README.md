# Edit-stage templates

Copy a template into your production's `edit/` folder, fill the `SCENES` list with your takes,
and run it with `uv run --with pillow python3 edit/<script>.py` from the repository root.

The pattern implemented here, distilled from real productions:

- Pause law: intra-scene silences over `CAP_TRIGGER` seconds are compressed to `CAP_KEEP`,
  cutting audio and video together so lip sync holds. Jump cuts are the format's grammar.
- Caption chips: word-timed from the render's SRT sidecar (request `caption {file_format: srt}`
  at render time), remapped through the cut map so timings stay accurate after tightening.
- Text renders as PNG overlays via Pillow, since slim ffmpeg builds lack drawtext. Keep every
  overlay input's `-t` below its scene's duration or the overlay freezes the scene tail.
- End cards use artwork masters only, with the canvas color sampled from the master itself,
  since a hardcoded hex can seam against a baked background.
- Scene sound: search the licensed audio catalog, mix beds at low volume with fades, and cut
  or duck them at story beats. Never source commercial tracks locally.

Production-specific values (video ids, scripts, brand assets, voices) belong in the production,
never in this repository.
