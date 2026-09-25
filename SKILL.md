---
name: shunri-voice
description: Generate Japanese narration using Shunri's canonical Irodori-TTS reference voice.
---

# Shunri Voice Skill

## Purpose

Generate narration for the original AI PR character 瞬理 using the canonical local reference voice.

## Source of truth

- Canonical reference: `references/shunri.wav`
- Voice preset: `clone`
- Generator: `scripts/generate.py`
- User-facing command: `shunri`

Do not replace `references/shunri.wav` unless the user explicitly chooses a new canonical voice.

## Commands

Direct text:

    shunri "読み上げたい文章"

Generate and play:

    shunri --play "読み上げたい文章"

Text file:

    shunri --file /path/to/script.txt

Choose output path:

    shunri --output ~/Desktop/narration.wav "読み上げたい文章"

Pipe text:

    echo "読み上げたい文章" | shunri

## Runtime behavior

On Intel macOS, the command checks the local Irodori-TTS Docker API and starts the compose service automatically if necessary.

The latest result is also generated internally as `outputs/clone.wav`, and the user-facing result defaults to `outputs/shunri.wav`.

## Safety / voice provenance

Use the canonical reference only for the original fictional character 瞬理. Do not substitute or clone a real person's voice without explicit permission.
