#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE = Path.home() / "shun-x-scheduler"
JOBS_REL = Path("runtime/shunri-reel-jobs.json")
RESULTS_REL = Path("runtime/shunri-reel-results.json")
ASSETS_REL = Path("runtime/shunri-reel-assets")
LOCAL_JOB_OUTPUTS = ROOT / "outputs" / "jobs"
CLI = ROOT / "scripts" / "shunri_cli.py"
DOCKER_IMAGE = "irodori-openai-tts:local"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process queued Shunri narration jobs from the private scheduler bridge."
    )
    parser.add_argument(
        "--bridge-repo",
        type=Path,
        default=Path(os.environ.get("SHUNRI_BRIDGE_REPO", DEFAULT_BRIDGE)),
    )
    parser.add_argument(
        "--no-git-sync",
        action="store_true",
        help="Process local queue files without git pull/commit/push.",
    )
    return parser.parse_args()


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True)


def tracked_repo_dirty(repo: Path) -> bool:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return bool(proc.stdout.strip())


def git_sync_before(repo: Path) -> None:
    if tracked_repo_dirty(repo):
        raise SystemExit(
            f"{repo} に未コミットの追跡ファイル変更があります。安全のため瞬理workerを停止しました。"
        )
    run(["git", "pull", "--ff-only", "origin", "main"], cwd=repo)


def git_publish(repo: Path) -> None:
    paths = [str(JOBS_REL), str(RESULTS_REL), str(ASSETS_REL)]
    run(["git", "add", "--", *paths], cwd=repo)

    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo,
        check=False,
    )
    if diff.returncode == 0:
        return

    run(["git", "commit", "-m", "chore: process Shunri Reel narration jobs"], cwd=repo)

    # Rebase once in case ChatGPT appended another job during synthesis.
    pull = subprocess.run(
        ["git", "pull", "--rebase", "origin", "main"],
        cwd=repo,
        check=False,
        text=True,
    )
    if pull.returncode != 0:
        raise SystemExit(
            "GitHub側と同時更新が衝突しました。自動pushを止めました。"
            " ~/shun-x-scheduler で git status を確認してください。"
        )

    run(["git", "push", "origin", "main"], cwd=repo)


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        frames = audio.getnframes()
    return frames / rate if rate else 0.0


def convert_mp3(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg"):
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-codec:a", "libmp3lame",
            "-q:a", "2",
            str(destination),
        ])
        return

    if not shutil.which("docker"):
        raise RuntimeError("MP3変換用の ffmpeg / docker が見つかりません。")

    inspect = subprocess.run(
        ["docker", "image", "inspect", DOCKER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if inspect.returncode != 0:
        raise RuntimeError(
            f"Docker image {DOCKER_IMAGE} がありません。~/shunri-voice で make setup を実行してください。"
        )

    run([
        "docker", "run", "--rm",
        "-v", f"{source.parent.resolve()}:/input:ro",
        "-v", f"{destination.parent.resolve()}:/output",
        DOCKER_IMAGE,
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", f"/input/{source.name}",
        "-codec:a", "libmp3lame",
        "-q:a", "2",
        f"/output/{destination.name}",
    ])


def upsert_result(results: list[dict], value: dict) -> None:
    for index, existing in enumerate(results):
        if existing.get("jobId") == value.get("jobId"):
            results[index] = value
            return
    results.append(value)


def process_job(job: dict, bridge: Path) -> dict:
    job_id = str(job.get("id", "")).strip()
    if not job_id:
        raise ValueError("job.id がありません。")
    if job.get("action") != "narrate":
        raise ValueError("現在のローカルworkerは action=narrate のみ対応しています。")
    if job.get("scriptApproved") is not True:
        raise ValueError("scriptApproved=true の確定台本だけをナレーション化できます。")
    if job.get("voice") not in (None, "shunri"):
        raise ValueError("voice は shunri 固定です。")

    script = str(job.get("script", "")).strip()
    if not script:
        raise ValueError("script が空です。")

    local_dir = LOCAL_JOB_OUTPUTS / job_id
    local_dir.mkdir(parents=True, exist_ok=True)
    wav_path = local_dir / "narration.wav"

    run([
        sys.executable,
        str(CLI),
        "--output",
        str(wav_path),
        script,
    ], cwd=ROOT)

    asset_rel = ASSETS_REL / job_id / "narration.mp3"
    mp3_path = bridge / asset_rel
    convert_mp3(wav_path, mp3_path)

    return {
        "jobId": job_id,
        "action": "narrate",
        "status": "completed",
        "voice": "shunri",
        "asset": asset_rel.as_posix(),
        "durationSeconds": round(wav_duration(wav_path), 3),
        "localMaster": f"~/shunri-voice/outputs/jobs/{job_id}/narration.wav",
        "completedAt": now_iso(),
    }


def main() -> int:
    args = parse_args()
    bridge = args.bridge_repo.expanduser().resolve()

    if not bridge.exists():
        raise SystemExit(f"bridge repo が見つかりません: {bridge}")
    if not (bridge / ".git").exists():
        raise SystemExit(f"Gitリポジトリではありません: {bridge}")

    if not args.no_git_sync:
        git_sync_before(bridge)

    jobs_path = bridge / JOBS_REL
    results_path = bridge / RESULTS_REL

    jobs_doc = read_json(jobs_path, {"version": 1, "jobs": []})
    results_doc = read_json(results_path, {"version": 1, "results": []})

    jobs = jobs_doc.setdefault("jobs", [])
    results = results_doc.setdefault("results", [])
    queued = [job for job in jobs if job.get("status") == "queued" and job.get("action") == "narrate"]

    if not queued:
        print("queued の瞬理ナレーションjobはありません。")
        return 0

    changed = False
    for job in queued:
        job_id = job.get("id", "(no id)")
        print(f"\n=== Shunri Reel job: {job_id} ===")
        job["status"] = "processing"
        job["startedAt"] = now_iso()
        try:
            result = process_job(job, bridge)
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            job["completedAt"] = now_iso()
            upsert_result(results, {
                "jobId": job.get("id"),
                "action": job.get("action"),
                "status": "failed",
                "error": str(exc),
                "completedAt": now_iso(),
            })
            print(f"失敗: {exc}", file=sys.stderr)
        else:
            job["status"] = "completed"
            job["completedAt"] = result["completedAt"]
            job.pop("error", None)
            upsert_result(results, result)
            print(f"完了: {result['asset']}")
        changed = True

    if changed:
        write_json(jobs_path, jobs_doc)
        write_json(results_path, results_doc)
        if not args.no_git_sync:
            git_publish(bridge)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
