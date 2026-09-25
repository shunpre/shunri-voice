#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "voices.json"
DEFAULT_UPSTREAM = ROOT / ".vendor" / "Irodori-TTS"
DEFAULT_SERVER = ROOT / ".vendor" / "Irodori-TTS-Server"
DEFAULT_OUTPUT = ROOT / "outputs"
API_URL = "http://127.0.0.1:8088/v1/audio/speech"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Shunri voice candidates with Irodori-TTS.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", help="Text to synthesize.")
    group.add_argument("--text-file", type=Path, help="UTF-8 text file to synthesize.")
    parser.add_argument("--preset", default="default", help="Preset name or all.")
    parser.add_argument("--reference", type=Path, help="Optional reference audio for fixed speaker identity.")
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM)
    parser.add_argument("--server-dir", type=Path, default=DEFAULT_SERVER)
    parser.add_argument("--model", help="Override Hugging Face checkpoint.")
    return parser.parse_args()


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def resolve_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        text = args.text.strip()
    else:
        text_file = args.text_file or (ROOT / "samples" / "reel_script.txt")
        if not text_file.exists():
            raise SystemExit(f"台本ファイルが見つかりません: {text_file}")
        text = text_file.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("台本が空です。")
    return text


def is_intel_mac() -> bool:
    return platform.system() == "Darwin" and platform.machine().lower() == "x86_64"


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        return "mps"
    return "cpu"


def prepare_reference_for_server(reference: Path | None, server_dir: Path) -> str:
    if reference is None:
        return "none"
    if not reference.exists():
        raise SystemExit(f"参照音声が見つかりません: {reference}")

    voices_dir = server_dir / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)
    target = voices_dir / "shunri.wav"
    shutil.copy2(reference, target)
    return "shunri"


def run_via_server(
    *,
    name: str,
    preset: dict,
    text: str,
    output_dir: Path,
    reference: Path | None,
    server_dir: Path,
) -> None:
    if not server_dir.exists():
        raise SystemExit("Intel Mac 用 Irodori-TTS-Server がありません。先に make setup を実行してください。")

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{name}.wav"
    caption = preset["caption"]
    voice = prepare_reference_for_server(reference, server_dir)

    payload = {
        "model": "irodori-tts",
        "input": text,
        "voice": voice,
        "response_format": "wav",
        "irodori": {
            "caption": caption,
            "seed": int(preset.get("seed", 1234)),
        },
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"\n=== {name} ===")
    print("runtime: Docker CPU API")
    print(f"output: {output}")
    print(f"caption: {caption}")

    try:
        with urllib.request.urlopen(request, timeout=7200) as response:
            output.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Irodori-TTS API がエラーを返しました: HTTP {exc.code}\n{detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            "Irodori-TTS API に接続できません。Docker Desktop が起動しているか確認し、"
            "make setup をもう一度実行してください。"
        ) from exc


def run_local(
    *,
    name: str,
    preset: dict,
    text: str,
    model: str,
    upstream: Path,
    output_dir: Path,
    reference: Path | None,
    device: str,
) -> None:
    infer = upstream / "infer.py"
    if not infer.exists():
        raise SystemExit("Irodori-TTS が見つかりません。先に make setup を実行してください。")

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{name}.wav"
    caption = preset["caption"]

    cmd = [
        "uv", "run", "--no-sync", "python", "infer.py",
        "--hf-checkpoint", model,
        "--text", text,
        "--caption", caption,
        "--seed", str(preset.get("seed", 1234)),
        "--model-device", device,
        "--codec-device", device,
        "--output-wav", str(output),
    ]

    if reference:
        if not reference.exists():
            raise SystemExit(f"参照音声が見つかりません: {reference}")
        cmd.extend(["--ref-wav", str(reference.resolve())])
    else:
        cmd.append("--no-ref")

    print(f"\n=== {name} ===")
    print(f"runtime: local {device}")
    print(f"output: {output}")
    print(f"caption: {caption}")
    subprocess.run(cmd, cwd=upstream, check=True)


def main() -> int:
    args = parse_args()
    config = load_config()
    presets = config["presets"]
    text = resolve_text(args)
    model = args.model or config["model"]
    device = resolve_device(args.device)

    if args.preset == "all":
        selected = [(name, preset) for name, preset in presets.items() if name.startswith("voice-")]
    else:
        if args.preset not in presets:
            raise SystemExit(f"不明なpreset: {args.preset}")
        selected = [(args.preset, presets[args.preset])]

    runtime = "docker-api" if is_intel_mac() else "local"
    reference_label = str(args.reference) if args.reference else "none (Voice Design)"

    display_model = "Aratako/Irodori-TTS-v4.1-Small-MF" if is_intel_mac() else model
    print("Shunri Voice Lab")
    print(f"model: {display_model}")
    print(f"runtime: {runtime}")
    print(f"reference: {reference_label}")

    for name, preset in selected:
        if is_intel_mac():
            run_via_server(
                name=name,
                preset=preset,
                text=text,
                output_dir=args.output_dir,
                reference=args.reference,
                server_dir=args.server_dir,
            )
        else:
            run_local(
                name=name,
                preset=preset,
                text=text,
                model=model,
                upstream=args.upstream,
                output_dir=args.output_dir,
                reference=args.reference,
                device=device,
            )

    print("\n完了しました。")
    for name, _ in selected:
        print(f"- {args.output_dir / (name + '.wav')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nIrodori-TTS の生成に失敗しました (exit={exc.returncode})", file=sys.stderr)
        print("MPSで失敗する場合は --device cpu を試してください。", file=sys.stderr)
        raise
