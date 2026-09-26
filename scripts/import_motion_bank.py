#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "motion_bank.json"
RENDER_IMAGE = "shunri-reel-renderer:local"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import real Shunri motion clips into the production Motion Bank.")
    p.add_argument("source_dir", type=Path)
    p.add_argument("--force", action="store_true")
    return p.parse_args()


def docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    r = subprocess.run(["docker","info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return r.returncode == 0


def ensure_docker() -> None:
    if docker_ready():
        return
    if platform.system() == "Darwin" and shutil.which("docker"):
        subprocess.run(["open","-a","Docker"], check=False)
        for _ in range(60):
            if docker_ready():
                return
            time.sleep(2)
    raise SystemExit("Docker Desktop を起動できませんでした。")


def normalize(source: Path, destination: Path) -> None:
    work = destination.parent / ".import-work"
    work.mkdir(parents=True, exist_ok=True)
    temp_in = work / ("input" + source.suffix.lower())
    temp_out = work / destination.name
    shutil.copy2(source, temp_in)

    subprocess.run([
        "docker","run","--rm",
        "-v",f"{work.resolve()}:/work",
        RENDER_IMAGE,
        "-y",
        "-i",f"/work/{temp_in.name}",
        "-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
        "-an",
        "-c:v","libx264",
        "-preset","veryfast",
        "-crf","18",
        "-pix_fmt","yuv420p",
        "-movflags","+faststart",
        f"/work/{temp_out.name}",
    ], check=True)
    shutil.move(str(temp_out), str(destination))


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir.expanduser().resolve()
    if not source_dir.exists():
        raise SystemExit(f"入力フォルダがありません: {source_dir}")

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    variants = [str(v["id"]) for v in data["variants"]]
    dest_dir = Path(data["productionDir"]).expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)

    candidates: dict[str, Path] = {}
    for variant in variants:
        found = None
        for ext in (".mp4",".mov",".m4v",".webm"):
            p = source_dir / f"{variant}{ext}"
            if p.exists():
                found = p
                break
        if found is None:
            raise SystemExit(
                f"必須clipがありません: {variant}.mp4/mov/m4v/webm\n"
                f"必要variant: {', '.join(variants)}"
            )
        candidates[variant] = found

    ensure_docker()

    for variant in variants:
        dest = dest_dir / f"{variant}.mp4"
        if dest.exists() and not args.force:
            print(f"skip: {variant}")
            continue
        print(f"import: {variant} <- {candidates[variant].name}")
        normalize(candidates[variant], dest)

    print()
    print("Production Motion Bank を登録しました。")
    print(f"- dir: {dest_dir}")
    print("- 1080x1920 / 30fps / H.264 / muted に正規化済み")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
