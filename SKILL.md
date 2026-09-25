---
name: shunri
description: Orchestrate Shunri Reel production. Use the canonical Shunri voice, preserve approved scripts, create narration jobs, and progress toward finished vertical video.
---

# 瞬理 Skill

## North star

The intended user experience is:

    @瞬理 この台本で動画を作って

and the system should progress through:

    script
    → Shunri narration
    → storyboard / visuals
    → captions
    → BGM / SE
    → 9:16 Reel render
    → QA

The implementation is incremental. Never pretend an unimplemented stage is complete.

## Canonical voice

The canonical reference voice is local only:

    references/shunri.wav

Rules:

- always use preset `clone`
- never fall back to Voice Design candidates A-E
- never replace the canonical reference unless the user explicitly selects a new voice
- the reference audio itself must not be committed to GitHub

## When a script is already approved

Do not rewrite it.

Create a narration job using the private production bridge:

    shunpre/shun-x-scheduler
    runtime/shunri-reel-jobs.json

Required job fields:

- action: narrate
- status: queued
- scriptApproved: true
- voice: shunri
- script: exact approved narration text

The user's Mac worker will generate:
- local WAV master
- private-repo MP3 proxy
- result entry in runtime/shunri-reel-results.json

## When only a topic / brief exists

Draft:
1. Reel hook
2. narration script
3. scene-by-scene storyboard
4. on-screen captions
5. visual asset requirements
6. BGM / SE direction

Ask for script approval before enqueueing narration unless the user explicitly says no approval is necessary.

## Current local commands

Direct narration:

    shunri "読み上げたい文章"

Generate and play:

    shunri --play "読み上げたい文章"

Process private GitHub narration queue once:

    make worker-once

Install automatic queue processing:

    make install-reel-worker

## Private bridge

The private scheduler repository is the transport layer for ChatGPT ↔ local Mac.

Canonical contract:

    shun-x-scheduler/docs/instagram/CHATGPT_SHUNRI_REEL_SKILL.md

## Video stages

These are the intended stages:

1. script
2. narration
3. storyboard
4. visual generation
5. scene timing
6. caption generation
7. BGM / SE
8. 9:16 render
9. QA

Narration automation is implemented first. Visual generation and final render should be connected to the same job/result contract rather than creating a separate ad-hoc workflow.

## Safety / provenance

The canonical voice is for the original fictional AI PR character 瞬理. Do not substitute or clone a real person's voice without explicit permission.
