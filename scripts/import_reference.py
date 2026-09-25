#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "references" / "shunri.wav"
DOCKER_IMAGE = "irodori-openai-tts:local"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import MP4/MP3/WAV/etc. as the canonical Shunri reference voice."
    )
    parser.add_argument("source", type=Path, help="Source media file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def ffmpeg_command(input_path: str, output_path: str) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "48000",
        "-c:a",
        "pcm_s16le",
        output_path,
    ]


def convert_with_host_ffmpeg(source: Path, output: Path) -> None:
    subprocess.run(ffmpeg_command(str(source), str(output)), check=True)


def convert_with_docker(source: Path, output: Path) -> None:
    if shutil.which("docker") is None:
        raise SystemExit(
            "ffmpeg も docker も見つかりません。先に make setup を完了してください。"
        )

    inspect = subprocess.run(
        ["docker", "image", "inspect", DOCKER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if inspect.returncode != 0:
        raise SystemExit(
            f"Docker image {DOCKER_IMAGE} が見つかりません。先に make setup を実行してください。"
        )

    source_dir = source.parent.resolve()
    output_dir = output.parent.resolve()
    input_in_container = f"/input/{source.name}"
    output_in_container = f"/output/{output.name}"

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{source_dir}:/input:ro",
        "-v",
        f"{output_dir}:/output",
        DOCKER_IMAGE,
        *ffmpeg_command(input_in_container, output_in_container),
    ]
    subprocess.run(cmd, check=True)


def validate_wav(output: Path) -> tuple[float, int, int]:
    with wave.open(str(output), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
    duration = frames / sample_rate if sample_rate else 0.0
    return duration, channels, sample_rate


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()

    if not source.exists():
        raise SystemExit(f"入力ファイルが見つかりません: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg"):
        print("参照音声を変換します: host ffmpeg")
        convert_with_host_ffmpeg(source, output)
    else:
        print("参照音声を変換します: Docker ffmpeg")
        convert_with_docker(source, output)

    duration, channels, sample_rate = validate_wav(output)
    print()
    print("参照音声を登録しました。")
    print(f"- source: {source}")
    print(f"- output: {output}")
    print(f"- duration: {duration:.2f}s")
    print(f"- format: PCM WAV / {sample_rate} Hz / {channels}ch")

    if duration < 8:
        print("注意: かなり短い参照音声です。声の再現が弱い場合は20〜30秒程度を推奨します。")
    elif duration < 15:
        print("メモ: テストには使えます。声の再現をさらに安定させるなら20〜30秒程度が有利です。")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"参照音声の変換に失敗しました (exit={exc.returncode})", file=sys.stderr)
        raise
