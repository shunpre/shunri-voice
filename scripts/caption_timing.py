#!/usr/bin/env python3
from __future__ import annotations

import math
import re
import struct
import wave
from pathlib import Path


def _read_pcm16_mono(path: Path) -> tuple[list[int], int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if width != 2:
        raise ValueError(f"16-bit PCM WAV only: sample_width={width}")

    count = len(frames) // 2
    samples = list(struct.unpack("<" + "h" * count, frames))
    if channels > 1:
        mono: list[int] = []
        for i in range(0, len(samples), channels):
            chunk = samples[i : i + channels]
            mono.append(int(sum(chunk) / len(chunk)))
        samples = mono
    return samples, rate


def _frame_rms(samples: list[int], frame_size: int) -> list[float]:
    values: list[float] = []
    for start in range(0, len(samples), frame_size):
        frame = samples[start : start + frame_size]
        if not frame:
            continue
        power = sum(float(s) * float(s) for s in frame) / len(frame)
        values.append(math.sqrt(power))
    return values


def _pause_candidates(wav_path: Path, frame_ms: int = 20) -> list[float]:
    samples, rate = _read_pcm16_mono(wav_path)
    frame_size = max(1, int(rate * frame_ms / 1000))
    energies = _frame_rms(samples, frame_size)
    if not energies:
        return []

    ordered = sorted(energies)
    noise = ordered[max(0, int(len(ordered) * 0.20) - 1)]
    peak = ordered[-1]
    threshold = max(80.0, noise * 2.2, peak * 0.035)

    min_silence_frames = max(4, int(round(120 / frame_ms)))
    candidates: list[float] = []
    start: int | None = None

    for i, energy in enumerate(energies):
        silent = energy < threshold
        if silent and start is None:
            start = i
        elif not silent and start is not None:
            if i - start >= min_silence_frames:
                midpoint = (start + i) / 2 * frame_ms / 1000
                candidates.append(midpoint)
            start = None

    if start is not None and len(energies) - start >= min_silence_frames:
        midpoint = (start + len(energies)) / 2 * frame_ms / 1000
        candidates.append(midpoint)

    return candidates


def align_phrases(
    wav_path: Path,
    phrases: list[str],
    duration: float,
    *,
    min_scene_seconds: float = 0.28,
    snap_window_seconds: float = 1.10,
) -> list[tuple[float, float]]:
    if not phrases:
        return []

    weights = [max(4, len(re.sub(r"\s+", "", p))) for p in phrases]
    total_weight = sum(weights)

    ideal_boundaries = [0.0]
    cumulative = 0
    for weight in weights[:-1]:
        cumulative += weight
        ideal_boundaries.append(duration * cumulative / total_weight)
    ideal_boundaries.append(duration)

    try:
        pauses = _pause_candidates(wav_path)
    except Exception:
        pauses = []

    chosen = [0.0]
    used: set[int] = set()

    for ideal in ideal_boundaries[1:-1]:
        lower = chosen[-1] + min_scene_seconds
        upper = duration - min_scene_seconds

        best_index = -1
        best_distance = float("inf")
        for idx, pause in enumerate(pauses):
            if idx in used or pause < lower or pause > upper:
                continue
            distance = abs(pause - ideal)
            if distance <= snap_window_seconds and distance < best_distance:
                best_distance = distance
                best_index = idx

        boundary = pauses[best_index] if best_index >= 0 else ideal
        if best_index >= 0:
            used.add(best_index)

        boundary = max(lower, min(boundary, upper))
        chosen.append(boundary)

    chosen.append(duration)

    result: list[tuple[float, float]] = []
    for i in range(len(phrases)):
        start = round(chosen[i], 3)
        end = round(chosen[i + 1], 3)
        if end <= start:
            end = round(min(duration, start + min_scene_seconds), 3)
        result.append((start, end))
    return result
