#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "references" / "shunri.wav"
GENERATOR = ROOT / "scripts" / "generate.py"
OUTPUTS = ROOT / "outputs"
SERVER_DIR = ROOT / ".vendor" / "Irodori-TTS-Server"
HEALTH_URL = "http://127.0.0.1:8088/health"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="shunri",
        description="Generate narration with Shunri's canonical reference voice.",
    )
    parser.add_argument("text", nargs="?", help="Text to speak.")
    parser.add_argument("-f", "--file", type=Path, help="UTF-8 text file to speak.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output WAV path. Default: ~/shunri-voice/outputs/shunri.wav",
    )
    parser.add_argument(
        "-p",
        "--play",
        action="store_true",
        help="Play the generated WAV after synthesis.",
    )
    return parser.parse_args()


def is_intel_mac() -> bool:
    return platform.system() == "Darwin" and platform.machine().lower() == "x86_64"


def server_is_healthy() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError):
        return False


def docker_daemon_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def ensure_docker_daemon(timeout_seconds: int = 120) -> None:
    if shutil.which("docker") is None:
        raise SystemExit(
            "Docker CLI が見つかりません。Docker Desktop のインストールを確認してください。"
        )

    if docker_daemon_ready():
        return

    if platform.system() == "Darwin":
        print("Docker Desktop が停止しています。自動起動します...")
        opened = subprocess.run(
            ["open", "-a", "Docker"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if opened.returncode != 0:
            raise SystemExit(
                "Docker Desktop を自動起動できませんでした。"
                " Applications から Docker を起動して再実行してください。"
            )

        waited = 0
        while waited < timeout_seconds:
            if docker_daemon_ready():
                print("Docker Desktop の起動を確認しました。")
                return
            time.sleep(2)
            waited += 2

        raise SystemExit(
            f"Docker Desktop が {timeout_seconds} 秒以内に起動しませんでした。"
            " Docker Desktop の画面を確認してから再実行してください。"
        )

    raise SystemExit(
        "Docker daemon が停止しています。Docker を起動してから再実行してください。"
    )


def ensure_server() -> None:
    if not is_intel_mac():
        return

    if server_is_healthy():
        return

    ensure_docker_daemon()

    if not SERVER_DIR.exists():
        raise SystemExit(
            "Irodori-TTS-Server がありません。~/shunri-voice で make setup を実行してください。"
        )

    print("Irodori-TTS API を起動します...")
    subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=SERVER_DIR,
        check=True,
    )

    for _ in range(60):
        if server_is_healthy():
            return
        time.sleep(1)

    raise SystemExit(
        "Irodori-TTS API が起動しませんでした。Docker Desktop と make setup の状態を確認してください。"
    )


def resolve_text(args: argparse.Namespace) -> tuple[str, Path | None]:
    if args.text and args.file:
        raise SystemExit("文章の直接指定と --file は同時に使えません。")

    if args.file:
        path = args.file.expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"台本ファイルが見つかりません: {path}")
        return path.read_text(encoding="utf-8").strip(), path

    if args.text:
        return args.text.strip(), None

    if not sys.stdin.isatty():
        return sys.stdin.read().strip(), None

    raise SystemExit(
        '使い方: shunri "読み上げたい文章"\n'
        'または: shunri --file script.txt'
    )


def main() -> int:
    args = parse_args()

    if not REFERENCE.exists():
        raise SystemExit(
            "瞬理の基準声が見つかりません: "
            f"{REFERENCE}\n"
            '先に make reference FILE="/path/to/sample.mp4" を実行してください。'
        )

    text, text_file = resolve_text(args)
    if not text:
        raise SystemExit("読み上げる文章が空です。")

    ensure_server()

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    generated = OUTPUTS / "clone.wav"

    cmd = [
        sys.executable,
        str(GENERATOR),
        "--preset",
        "clone",
        "--reference",
        str(REFERENCE),
    ]

    if text_file is not None:
        cmd.extend(["--text-file", str(text_file)])
    else:
        cmd.extend(["--text", text])

    subprocess.run(cmd, cwd=ROOT, check=True)

    destination = (
        args.output.expanduser().resolve()
        if args.output
        else OUTPUTS / "shunri.wav"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(generated, destination)

    print()
    print("瞬理の音声を生成しました。")
    print(destination)

    if args.play:
        if platform.system() == "Darwin" and shutil.which("afplay"):
            subprocess.run(["afplay", str(destination)], check=True)
        else:
            print("自動再生はmacOSの afplay が利用できる環境のみ対応しています。")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
