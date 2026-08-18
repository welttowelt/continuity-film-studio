#!/usr/bin/env python3
"""TEMPLATE: vertical short-form master. Copy into productions/<name>/edit/ and fill SCENES.

Run with: uv run --with pillow python3 edit/build-tiktok.py  (from the production root's repo)
Pause law: intra-scene silences over CAP_TRIGGER compressed to CAP_KEEP, audio and video cut
together. Caption windows are remapped through the cut map so chips stay word-accurate.
Captions: Oswald 600 white on Ink chips, centered, TikTok-safe vertical band. End card:
get-off-market-mobile master on exact Pool blue per the brand manual.
"""

import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "edit/work"
CAP_TRIGGER = 0.30
CAP_KEEP = 0.16
HEAD_KEEP = 0.06
TAIL_KEEP = 0.18
W, H = 1080, 1920
CAPTION_Y = 1330
OSWALD = str(ROOT / "references/brand/fonts/Oswald.ttf")
INK = (3, 18, 31, 235)
POOL = (45, 161, 251, 255)
LEMON = (232, 247, 56, 255)
WHITE = (255, 255, 255, 255)

SCENES = [
    # ("scene-folder-name", "heygen-video-id", "the exact script line the take was rendered from"),
]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_duration(path: Path) -> float:
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    return float(out.stdout.strip())


def silences(path: Path, trigger: float) -> list[tuple[float, float]]:
    err = run(
        ["ffmpeg", "-i", str(path), "-af", f"silencedetect=noise=-40dB:d={trigger}", "-f", "null", "-"]
    ).stderr
    starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


def keep_windows(duration: float, gaps: list[tuple[float, float]]) -> list[tuple[float, float]]:
    windows, cursor = [], 0.0
    for start, end in gaps:
        if start <= 0.01:
            cursor = max(cursor, end - HEAD_KEEP)
            continue
        if end >= duration - 0.05:
            windows.append((cursor, start + TAIL_KEEP))
            cursor = duration
            break
        windows.append((cursor, start + CAP_KEEP / 2))
        cursor = end - CAP_KEEP / 2
    if cursor < duration:
        windows.append((cursor, duration))
    return [(a, b) for a, b in windows if b - a > 0.04]


def remap(t: float, windows: list[tuple[float, float]]) -> float:
    new = 0.0
    for a, b in windows:
        if t < a:
            return new
        if t <= b:
            return new + (t - a)
        new += b - a
    return new


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    def ts(value: str) -> float:
        h, m, rest = value.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    cues = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = [line for line in block.strip().split("\n") if line.strip()]
        if len(lines) >= 2 and "-->" in lines[1]:
            start, end = [ts(part.strip()) for part in lines[1].split("-->")]
            cues.append((start, end, " ".join(lines[2:]).strip()))
    return cues


def sentence_cues(
    text: str, duration: float, gaps: list[tuple[float, float]]
) -> list[tuple[float, float, str]]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?]) ", text) if s.strip()]
    boundaries = [0.0] + [(a + b) / 2 for a, b in gaps if 0.1 < a < duration - 0.1] + [duration]
    if len(boundaries) - 1 != len(sentences):
        total_words = sum(len(s.split()) for s in sentences)
        cues, cursor = [], 0.0
        for sentence in sentences:
            span = duration * len(sentence.split()) / total_words
            cues.append((cursor, cursor + span, sentence))
            cursor += span
        return cues
    return [(boundaries[i], boundaries[i + 1], s) for i, s in enumerate(sentences)]


def chunk_words(cue_text: str, limit: int = 4) -> list[str]:
    words = cue_text.split()
    return [" ".join(words[i : i + limit]) for i in range(0, len(words), limit)]


def caption_chip(text: str, out: Path) -> None:
    font = ImageFont.truetype(OSWALD, 72)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad = 26
    x = (W - tw) // 2
    draw.rectangle([x - pad, CAPTION_Y - pad, x + tw + pad, CAPTION_Y + th + pad], fill=INK)
    draw.text((x - box[0], CAPTION_Y - box[1]), text, font=font, fill=WHITE)
    layer.save(out)


def build_endcard(out: Path) -> None:
    master = Image.open(ROOT / "references/brand/get-off-market-mobile.png").convert("RGBA")
    base_color = master.getpixel((10, 10))
    card = Image.new("RGBA", (W, H), base_color)
    scale = 880 / master.width
    resized = master.resize((880, round(master.height * scale)), Image.LANCZOS)
    card.alpha_composite(resized, ((W - 880) // 2, 240))
    draw = ImageDraw.Draw(card)
    draw.rectangle([W // 2 - 150, 1700, W // 2 + 150, 1708], fill=LEMON)
    font = ImageFont.truetype(OSWALD, 66)
    box = draw.textbbox((0, 0), "offmarket.cx", font=font)
    draw.text(((W - (box[2] - box[0])) // 2, 1740 - box[1]), "offmarket.cx", font=font, fill=WHITE)
    card.convert("RGB").save(out)


def build_scene(name: str, video_id: str, script_text: str) -> Path:
    source = ROOT / f"generations/heygen/{video_id}.mp4"
    duration = probe_duration(source)
    fine_gaps = silences(source, 0.05)
    windows = keep_windows(duration, silences(source, CAP_TRIGGER))
    kept = sum(b - a for a, b in windows)
    print(f"{name}: {duration:.2f}s -> {kept:.2f}s")

    srt = WORK / f"{video_id}.srt"
    cues = parse_srt(srt) if srt.is_file() else sentence_cues(script_text, duration, fine_gaps)
    chips = []
    for start, end, text in cues:
        parts = chunk_words(text)
        span = (end - start) / len(parts)
        for i, part in enumerate(parts):
            a = remap(start + i * span, windows)
            b = remap(start + (i + 1) * span, windows)
            if b - a > 0.12:
                chips.append((a, b, part))
    inputs = ["-i", str(source)]
    graph = ["[0:v]fps=30[v0];[0:a]anull[a]"]
    previous = "v0"
    for index, (a, b, text) in enumerate(chips):
        chip_path = WORK / f"chip-{name}-{index:02d}.png"
        caption_chip(text, chip_path)
        inputs += ["-loop", "1", "-t", f"{min(b + 0.2, kept):.2f}", "-i", str(chip_path)]
        graph.append(
            f"[{previous}][{index + 1}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{index + 1}]"
        )
        previous = f"v{index + 1}"
    graph_text = ";".join(graph)

    tight = WORK / f"tight-{name}-raw.mp4"
    parts = []
    for i, (a, b) in enumerate(windows):
        parts.append(
            f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[tv{i}];"
            f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[ta{i}];"
        )
    pairs = "".join(f"[tv{i}][ta{i}]" for i in range(len(windows)))
    (WORK / f"tight-{name}.filter").write_text(
        "".join(parts) + f"{pairs}concat=n={len(windows)}:v=1:a=1[v][a]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-filter_complex_script",
            str(WORK / f"tight-{name}.filter"),
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-r",
            "30",
            str(tight),
        ],
        check=True,
    )
    captioned = WORK / f"cap-{name}.mp4"
    (WORK / f"cap-{name}.filter").write_text(graph_text.replace("[0:v]", "[0:v]"))
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(tight)]
    cmd += inputs[2:]
    cmd += [
        "-filter_complex_script",
        str(WORK / f"cap-{name}.filter"),
        "-map",
        f"[{previous}]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(captioned),
    ]
    subprocess.run(cmd, check=True)
    return captioned


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    scenes = [build_scene(*scene) for scene in SCENES]
    endcard = WORK / "endcard-mobile.png"
    build_endcard(endcard)
    graph = (
        "[0:v]fps=30[va];[1:v]fps=30[vb];[2:v]fps=30[vc];"
        "[3:v]setsar=1,fps=30[vd];[4:a]atrim=duration=2.2[ad];"
        "[va][0:a][vb][1:a][vc][2:a][vd][ad]concat=n=4:v=1:a=1[v][a];"
        "[a]loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )
    (WORK / "tiktok-final.filter").write_text(graph)
    output = ROOT / "edit/OffMarket-tiktok-9x16-v1.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(scenes[0]),
            "-i",
            str(scenes[1]),
            "-i",
            str(scenes[2]),
            "-loop",
            "1",
            "-t",
            "2.2",
            "-framerate",
            "30",
            "-i",
            str(endcard),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex_script",
            str(WORK / "tiktok-final.filter"),
            "-map",
            "[v]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output),
        ],
        check=True,
    )
    print("tiktok master:", output)
    print(f"final duration: {probe_duration(output):.2f}s")


if __name__ == "__main__":
    main()
