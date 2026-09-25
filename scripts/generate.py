#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "voices.json"
DEFAULT_UPSTREAM = ROOT / ".vendor" / "Irodori-TTS"
DEFAULT_OUTPUT = ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Shunri voice candidates with Irodori-TTS.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", help="Text to synthesize.")
    group.add_argument("--text-file", type=Path, help="UTF-8 text file to synthesize.")
    parser.add_argument("--preset", default="default", help='Preset name or "all".')
    parser.add_argument("--reference", type=Path, help="Optional reference audio for fixed speaker identity.")
    parser.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM)
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


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        return "mps"
    return "cpu"


def run_one(name: str, preset: dict, text: str, model: str, upstream: Path, output_dir: Path, reference: Path | None, device: str) -> None:
    infer = upstream / "infer.py"
    if not infer.exists():
        raise SystemExit("Irodori-TTS が見つかりません。先に make setup を実行してください。")

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{name}.wav"

    cmd = [
        "uv", "run", "--no-sync", "python", "infer.py",
        "--hf-checkpoint", model,
        "--text", text,
        "--caption", preset["caption"],
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
    print(f"device: {device}")
    print(f"output: {output}")
    print(f"caption: {preset[\"caption\"]}")
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

    print("Shunri Voice Lab")
    print(f"model: {model}")
    print(f"device: {device}")
    print(f"reference: {args.reference or \"none (Voice Design)\"}")

    for name, preset in selected:
        run_one(name, preset, text, model, args.upstream, args.output_dir, args.reference, device)

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
