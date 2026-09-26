#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER_IMAGE = "shunri-reel-renderer:local"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate a rendered Shunri Reel.")
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--narration", required=True, type=Path)
    p.add_argument("--scene-plan", required=True, type=Path)
    p.add_argument("--captions", required=True, type=Path)
    p.add_argument("--script-file", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    return p.parse_args()


def wav_stats(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        count = wav.getnframes()
        raw = wav.readframes(count)

    duration = count / rate if rate else 0.0
    peak = 0
    rms = 0.0

    if width == 2 and raw:
        values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
        if channels > 1:
            mono = []
            for i in range(0, len(values), channels):
                chunk = values[i : i + channels]
                mono.append(sum(chunk) / len(chunk))
            values = tuple(mono)
        peak = max(abs(int(v)) for v in values) if values else 0
        rms = (sum(float(v) * float(v) for v in values) / max(1, len(values))) ** 0.5

    return {
        "duration": duration,
        "peak": peak,
        "rms": rms,
        "sampleRate": rate,
        "channels": channels,
    }


def ffprobe(path: Path) -> dict:
    parent = path.parent.resolve()
    proc = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{parent}:/work:ro",
            RENDER_IMAGE,
            "-hide_banner",
            "-loglevel", "error",
            "-show_streams",
            "-show_format",
            "-of", "json",
            f"/work/{path.name}",
        ],
        executable="docker",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffprobe failed")
    return json.loads(proc.stdout)


def parse_ass_time(value: str) -> float:
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def caption_windows(path: Path) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 3:
            continue
        result.append((parse_ass_time(parts[1]), parse_ass_time(parts[2])))
    return result


def fps_value(rate: str | None) -> float:
    if not rate or rate == "0/0":
        return 0.0
    if "/" in rate:
        a, b = rate.split("/", 1)
        return float(a) / float(b)
    return float(rate)


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    narration = args.narration.expanduser().resolve()
    plan_path = args.scene_plan.expanduser().resolve()
    captions = args.captions.expanduser().resolve()
    script_file = args.script_file.expanduser().resolve()
    report = args.report.expanduser().resolve()

    failures: list[str] = []
    warnings: list[str] = []
    checks: dict = {}

    for name, path in {
        "video": video,
        "narration": narration,
        "scenePlan": plan_path,
        "captions": captions,
        "script": script_file,
    }.items():
        checks[f"{name}Exists"] = path.exists()
        if not path.exists():
            failures.append(f"missing-{name}")

    if failures:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"passed": False, "failures": failures, "warnings": warnings, "checks": checks}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return 1

    probe = ffprobe(video)
    streams = probe.get("streams", [])
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
    astream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not vstream:
        failures.append("missing-video-stream")
    else:
        width = int(vstream.get("width") or 0)
        height = int(vstream.get("height") or 0)
        fps = fps_value(vstream.get("avg_frame_rate"))
        checks["width"] = width
        checks["height"] = height
        checks["fps"] = round(fps, 3)
        if (width, height) != (1080, 1920):
            failures.append("wrong-aspect-or-resolution")
        if not (29.0 <= fps <= 31.0):
            failures.append("wrong-fps")

    if not astream:
        failures.append("missing-audio-stream")

    narration_stats = wav_stats(narration)
    checks["narration"] = narration_stats
    if narration_stats["duration"] <= 0.1 or narration_stats["rms"] < 20:
        failures.append("silent-or-empty-narration")
    if narration_stats["peak"] >= 32767:
        warnings.append("narration-near-clipping")

    format_duration = float(probe.get("format", {}).get("duration") or 0)
    checks["videoDuration"] = round(format_duration, 3)
    duration_gap = abs(format_duration - narration_stats["duration"])
    checks["durationGap"] = round(duration_gap, 3)
    if duration_gap > 0.35:
        failures.append("audio-video-duration-mismatch")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    approved_script = script_file.read_text(encoding="utf-8").strip()
    checks["scriptPreserved"] = plan.get("script", "").strip() == approved_script
    if not checks["scriptPreserved"]:
        failures.append("approved-script-mutated")
    if plan.get("voice") != "shunri":
        failures.append("wrong-voice")

    windows = caption_windows(captions)
    checks["captionCount"] = len(windows)
    if not windows:
        failures.append("missing-captions")
    for i, (start, end) in enumerate(windows):
        if end <= start:
            failures.append(f"invalid-caption-window-{i+1}")
        if i and start < windows[i - 1][1] - 0.03:
            failures.append(f"overlapping-caption-{i+1}")
    if windows and abs(windows[-1][1] - narration_stats["duration"]) > 0.45:
        warnings.append("caption-end-not-close-to-audio-end")

    file_size = video.stat().st_size
    checks["videoBytes"] = file_size
    if file_size < 100_000:
        failures.append("video-file-too-small")

    payload = {
        "version": 1,
        "passed": len(failures) == 0,
        "failures": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
        "checks": checks,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    print(f"QA: {'PASS' if payload['passed'] else 'FAIL'}")
    print(f"- report: {report}")
    if payload["warnings"]:
        print("- warnings: " + ", ".join(payload["warnings"]))
    if payload["failures"]:
        print("- failures: " + ", ".join(payload["failures"]))

    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
