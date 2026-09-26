#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply optional Shunri lip-sync provider to one scene.")
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--audio", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--backend", choices=["auto","passthrough","external"], default="auto")
    return p.parse_args()


def passthrough(video: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video, output)


def external(video: Path, audio: Path, output: Path) -> None:
    template = os.environ.get("SHUNRI_LIPSYNC_COMMAND","").strip()
    if not template:
        raise SystemExit(
            "SHUNRI_LIPSYNC_COMMAND が未設定です。"
            " {video} {audio} {output} を含むコマンドテンプレートを設定してください。"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    command = template.format(
        video=shlex.quote(str(video.resolve())),
        audio=shlex.quote(str(audio.resolve())),
        output=shlex.quote(str(output.resolve())),
    )
    print("lip-sync backend: external")
    subprocess.run(command, shell=True, check=True)
    if not output.exists():
        raise SystemExit(f"lip-sync command がoutputを生成しませんでした: {output}")


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    audio = args.audio.expanduser().resolve()
    output = args.output.expanduser().resolve()

    if not video.exists():
        raise SystemExit(f"video がありません: {video}")
    if not audio.exists():
        raise SystemExit(f"audio がありません: {audio}")

    backend = args.backend
    if backend == "auto":
        backend = "external" if os.environ.get("SHUNRI_LIPSYNC_COMMAND","").strip() else "passthrough"

    if backend == "external":
        external(video, audio, output)
    else:
        print("lip-sync backend: passthrough")
        passthrough(video, output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
