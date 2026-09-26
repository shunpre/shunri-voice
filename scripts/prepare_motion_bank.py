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
RENDER_DOCKERFILE_DIR = ROOT / "docker" / "reel-renderer"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare deterministic Shunri motion-bank clips.")
    parser.add_argument("--force", action="store_true", help="Rebuild all bank clips.")
    return parser.parse_args()


def docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    p = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return p.returncode == 0


def ensure_docker(timeout_seconds: int = 120) -> None:
    if shutil.which("docker") is None:
        raise SystemExit("Docker CLI が見つかりません。")
    if docker_ready():
        return
    if platform.system() == "Darwin":
        print("Docker Desktop が停止しています。自動起動します...")
        subprocess.run(["open", "-a", "Docker"], check=False)
        for _ in range(timeout_seconds // 2):
            if docker_ready():
                return
            time.sleep(2)
    raise SystemExit("Docker daemon を起動できませんでした。")


def ensure_renderer() -> None:
    ensure_docker()
    inspect = subprocess.run(
        ["docker", "image", "inspect", RENDER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if inspect.returncode == 0:
        return
    subprocess.run(
        ["docker", "build", "-t", RENDER_IMAGE, str(RENDER_DOCKERFILE_DIR)],
        check=True,
    )


def motion_filter(kind: str, fps: int, duration: float) -> str:
    frames = max(1, int(round(fps * duration)))
    if kind == "push-in-strong":
        zoom = "min(zoom+0.0014,1.14)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif kind == "slow-push":
        zoom = "min(zoom+0.00045,1.06)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif kind == "pan-left":
        zoom = "1.07"
        x = "(iw-iw/zoom)*(1-on/%d)" % max(1, frames - 1)
        y = "ih/2-(ih/zoom/2)"
    elif kind == "pan-right":
        zoom = "1.07"
        x = "(iw-iw/zoom)*(on/%d)" % max(1, frames - 1)
        y = "ih/2-(ih/zoom/2)"
    elif kind == "micro-drift":
        zoom = "1.035"
        x = "iw/2-(iw/zoom/2)+6*sin(on/25)"
        y = "ih/2-(ih/zoom/2)+4*cos(on/30)"
    else:
        zoom = "min(zoom+0.0007,1.08)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"

    return (
        "scale=1200:2134:force_original_aspect_ratio=increase,"
        "crop=1200:2134,"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:"
        f"s=1080x1920:fps={fps},"
        "format=yuv420p"
    )


def build_clip(source: Path, output: Path, motion: str, fps: int, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output.parent / ".bank-work"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_source = temp_dir / ("source" + source.suffix.lower())
    shutil.copy2(source, temp_source)

    vf = motion_filter(motion, fps, duration)
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{temp_dir.resolve()}:/work",
        RENDER_IMAGE,
        "-y",
        "-loop", "1",
        "-framerate", str(fps),
        "-i", f"/work/{temp_source.name}",
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-r", str(fps),
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        f"/work/{output.name}",
    ]
    subprocess.run(cmd, check=True)
    built = temp_dir / output.name
    shutil.move(str(built), str(output))


def main() -> int:
    args = parse_args()
    ensure_renderer()

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scheduler_root = Path(data["schedulerRoot"]).expanduser()
    output_dir = Path(data["outputDir"]).expanduser()
    duration = float(data.get("clipDurationSeconds", 6))
    fps = int(data.get("fps", 30))
    output_dir.mkdir(parents=True, exist_ok=True)

    built = 0
    skipped = 0

    for variant in data["variants"]:
        variant_id = variant["id"]
        source = scheduler_root / variant["source"]
        output = output_dir / f"{variant_id}.mp4"

        if not source.exists():
            raise SystemExit(f"Motion Bank source が見つかりません: {source}")

        if output.exists() and not args.force:
            print(f"skip: {variant_id}")
            skipped += 1
            continue

        print(f"build: {variant_id} <- {source.name}")
        build_clip(source, output, variant.get("motion", "push-in"), fps, duration)
        built += 1

    print()
    print("瞬理 Motion Bank 準備完了")
    print(f"- built: {built}")
    print(f"- skipped: {skipped}")
    print(f"- dir: {output_dir}")
    print()
    print("注: v1 は静止画由来のモーションです。ここに後で実写的なAI motion/lip-sync clipを同名で差し替えられます。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
