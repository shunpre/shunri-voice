#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "reel_profile.json"
CLI = ROOT / "scripts" / "shunri_cli.py"
RENDER_IMAGE = "shunri-reel-renderer:local"
RENDER_DOCKERFILE_DIR = ROOT / "docker" / "reel-renderer"
DEFAULT_PRESENTER = (
    Path.home()
    / "shun-x-scheduler"
    / "assets"
    / "instagram"
    / "character"
    / "reference"
    / "canonical_front.jpeg"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Phase-1 Shunri Reel proof-of-concept from an approved script."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", type=Path, help="Approved UTF-8 narration script.")
    group.add_argument("-t", "--text", help="Approved narration text.")
    parser.add_argument(
        "--presenter",
        type=Path,
        default=DEFAULT_PRESENTER,
        help="Presenter image. Defaults to the canonical Shunri front reference in shun-x-scheduler.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "outputs" / "reel-poc" / "shunri-reel-poc.mp4",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip Docker renderer build when the image already exists.",
    )
    return parser.parse_args()


def load_script(args: argparse.Namespace) -> str:
    if args.file:
        path = args.file.expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"台本ファイルが見つかりません: {path}")
        text = path.read_text(encoding="utf-8").strip()
    else:
        text = (args.text or "").strip()
    if not text:
        raise SystemExit("台本が空です。")
    return text


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        frames = audio.getnframes()
    return frames / rate if rate else 0.0


def split_long_phrase(text: str, max_chars: int = 24) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    pieces = [x.strip() for x in re.split(r"(?<=[、，,])", text) if x.strip()]
    if len(pieces) == 1:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > max_chars:
            chunks.append(current)
            current = piece
        else:
            current += piece
    if current:
        chunks.append(current)
    return chunks


def split_script(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text)
    rough = [
        p.strip()
        for p in re.split(r"(?<=[。！？!?])|\n+", normalized)
        if p.strip()
    ]
    phrases: list[str] = []
    for item in rough:
        phrases.extend(split_long_phrase(item))
    return phrases


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def wrap_caption(text: str, max_chars: int = 16) -> str:
    clean = text.replace("{", "（").replace("}", "）").strip()
    if len(clean) <= max_chars:
        return clean
    if len(clean) <= max_chars * 2:
        split = len(clean) // 2
        candidates = [
            i for i, ch in enumerate(clean)
            if ch in "、，,。！？!?" and 5 <= i <= len(clean) - 5
        ]
        if candidates:
            split = min(candidates, key=lambda i: abs(i - len(clean) / 2)) + 1
        return clean[:split] + r"\N" + clean[split:]
    return clean[:max_chars] + r"\N" + clean[max_chars : max_chars * 2]


def build_timeline(phrases: list[str], duration: float) -> list[dict]:
    if not phrases:
        return []
    weights = [max(4, len(re.sub(r"\s+", "", p))) for p in phrases]
    total = sum(weights)
    cursor = 0.0
    timeline: list[dict] = []
    for index, (phrase, weight) in enumerate(zip(phrases, weights), start=1):
        end = duration if index == len(phrases) else cursor + duration * (weight / total)
        timeline.append(
            {
                "id": f"s{index:02d}",
                "type": "cta" if index == len(phrases) else "talk",
                "narration": phrase,
                "caption": phrase,
                "start": round(cursor, 3),
                "end": round(end, 3),
                "motion": "subtle-push-in" if index % 3 == 0 else "none",
            }
        )
        cursor = end
    return timeline


def write_plan(path: Path, script: str, duration: float, timeline: list[dict]) -> None:
    data = {
        "version": 1,
        "format": "shunri-reel-v1",
        "scriptApproved": True,
        "voice": "shunri",
        "durationSeconds": round(duration, 3),
        "script": script,
        "scenes": timeline,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_ass(path: Path, timeline: list[dict], width: int, height: int) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Noto Sans CJK JP,66,&H00FFFFFF,&H000000FF,&H00111111,&H7A000000,-1,0,0,0,100,100,0,0,1,5,1,2,80,80,250,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [header]
    for scene in timeline:
        start = ass_time(float(scene["start"]))
        end = ass_time(float(scene["end"]))
        caption = wrap_caption(str(scene["caption"]))
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{caption}\n")
    path.write_text("".join(lines), encoding="utf-8")


def ensure_renderer_image(skip_build: bool) -> None:
    if shutil.which("docker") is None:
        raise SystemExit("Docker が見つかりません。Docker Desktop を起動してください。")
    if skip_build:
        return
    inspect = subprocess.run(
        ["docker", "image", "inspect", RENDER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if inspect.returncode == 0:
        return
    print("Reel renderer Docker image を初回構築します...")
    subprocess.run(
        ["docker", "build", "-t", RENDER_IMAGE, str(RENDER_DOCKERFILE_DIR)],
        check=True,
    )


def render(job_dir: Path, duration: float, output_name: str) -> None:
    filter_graph = (
        "[0:v]split=2[bg0][fg0];"
        "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=30:10[bg];"
        "[fg0]scale=900:1450:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2-80,"
        "subtitles=/work/captions.ass:fontsdir=/usr/share/fonts/opentype/noto[outv]"
    )

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{job_dir.resolve()}:/work",
        RENDER_IMAGE,
        "-y",
        "-loop",
        "1",
        "-framerate",
        "30",
        "-i",
        "/work/presenter.jpg",
        "-i",
        "/work/narration.wav",
        "-filter_complex",
        filter_graph,
        "-map",
        "[outv]",
        "-map",
        "1:a:0",
        "-t",
        f"{duration:.3f}",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        f"/work/{output_name}",
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    args = parse_args()
    script = load_script(args)

    presenter = args.presenter.expanduser().resolve()
    if not presenter.exists():
        raise SystemExit(
            "瞬理の正準人物画像が見つかりません。\n"
            f"期待パス: {presenter}\n"
            "先に ~/shun-x-scheduler を git pull するか、--presenter で画像を指定してください。"
        )

    profile = json.loads(CONFIG.read_text(encoding="utf-8"))
    width = int(profile["output"]["width"])
    height = int(profile["output"]["height"])

    output = args.output.expanduser().resolve()
    job_dir = output.parent / ".poc-work"
    job_dir.mkdir(parents=True, exist_ok=True)

    script_path = job_dir / "script.txt"
    narration_path = job_dir / "narration.wav"
    plan_path = job_dir / "scene-plan.json"
    ass_path = job_dir / "captions.ass"
    presenter_copy = job_dir / "presenter.jpg"

    script_path.write_text(script + "\n", encoding="utf-8")
    shutil.copy2(presenter, presenter_copy)

    print("[1/4] 瞬理の正式声でナレーション生成")
    subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--file",
            str(script_path),
            "--output",
            str(narration_path),
        ],
        cwd=ROOT,
        check=True,
    )

    duration = wav_duration(narration_path)
    if duration <= 0:
        raise SystemExit("ナレーション音声の長さを取得できませんでした。")

    print("[2/4] 台本をシーン / 字幕へ分割")
    phrases = split_script(script)
    timeline = build_timeline(phrases, duration)
    write_plan(plan_path, script, duration, timeline)
    write_ass(ass_path, timeline, width, height)

    print("[3/4] Reel renderer 準備")
    ensure_renderer_image(args.skip_build)

    print("[4/4] 1080x1920 MP4 をレンダリング")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = job_dir / output.name
    render(job_dir, duration, output.name)
    shutil.copy2(temp_output, output)

    print()
    print("Phase-1 Reel PoC を生成しました。")
    print(f"- video: {output}")
    print(f"- narration: {narration_path}")
    print(f"- scene plan: {plan_path}")
    print(f"- captions: {ass_path}")
    print()
    print("注: このPoCはまだ静止画Presenterです。次工程で瞬理Motion Bankを接続します。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
