# 瞬理 Reel Engine Spec v1

## North Star

Final UX:

    @瞬理 このテーマでReelを作って

or, when the script is already fixed:

    @瞬理 この台本でReelを作って

The system should produce a finished 9:16 MP4 with the canonical Shunri voice, captions,
supporting visuals, BGM/SE, and deterministic brand-safe editing.

The target quality for v1 is the uploaded reference class:
- one primary presenter / avatar
- natural mouth / expression / pose variation
- large readable Japanese captions
- occasional screenshot / diagram / cutaway inserts
- clean studio background
- stable pacing
- one-pass automated assembly

This is intentionally NOT an open-ended video generator. It is a locked Shunri production system.

## What we borrow from OSS

### OpenReels — backbone ideas
Use as reference / donor for:
- DirectorScore-style scene plan
- provider abstraction
- TTS alignment fallback
- Whisper word timestamps
- image/video provider separation
- structured critic / QA stage

Do not let OpenReels rewrite approved Shunri scripts or replace the canonical voice.

### Revideo — preferred long-term renderer
Use as the preferred MIT-licensed deterministic composition/render layer for:
- 1080x1920 canvas
- captions
- overlays
- screenshots
- motion graphics
- transitions
- audio mixing

Prototype code may temporarily reuse compatible ideas from OpenReels, but the Shunri renderer
should remain replaceable and should not depend on a closed editor workflow.

### MoneyPrinterTurbo — utility patterns only
Borrow implementation ideas for:
- ffmpeg composition
- subtitle handling
- BGM ducking / audio mix
- media normalization

Do not adopt its generic topic-to-video creative decisions.

### OpenShorts — talking-head ideas only
Borrow implementation ideas for:
- presenter-first short-video pacing
- talking-head + B-roll alternation
- hook typography / preview concepts

Do not adopt its generic UGC identity or cloud-only assumptions.

### Explicitly not core
- story-flicks: too simple / stale for the target
- ClipForge: useful reference, but AGPL makes it a poor core dependency for future productization
- generic ShortGPT-style stock-video pipelines: too generic for the Shunri brand

## Canonical assets

Voice:
    ~/shunri-voice/references/shunri.wav

Voice rule:
- always preset = clone
- no fallback to voice-a ... voice-e
- never replace without explicit human approval

Character:
- the canonical Shunri character sheet / visual references from the scheduler repository
- same face identity across shots
- glasses and ShunLP brand rules remain governed by the Instagram canonical docs

## Production model

The engine is scene based.

Allowed scene types for v1:

1. talk
   - Shunri is the main presenter
   - captions are foreground priority
   - optional small overlay above / beside the presenter

2. talk_overlay
   - presenter remains visible
   - screenshot / diagram / UI card appears as a secondary visual

3. broll
   - full-frame or near-full-frame supporting visual
   - narration continues
   - Shunri may be absent

4. emphasis
   - one short phrase / keyword
   - stronger scale / motion
   - 0.6-2.0s
   - used sparingly

5. cta
   - final action
   - one CTA only

Do not invent additional scene types during normal generation.

## Scene plan contract

Every approved script is transformed into a deterministic scene JSON before rendering.

Example:

    {
      "version": 1,
      "format": "shunri-reel-v1",
      "title": "...",
      "scriptApproved": true,
      "voice": "shunri",
      "scenes": [
        {
          "id": "s01",
          "type": "talk",
          "narration": "...",
          "caption": "...",
          "visual": {
            "presenterPose": "open-hand",
            "overlay": null
          },
          "motion": "subtle-push-in"
        }
      ]
    }

The scene plan is an execution plan, not a second copywriting stage.
Approved narration must not be rewritten.

## Caption rules

All visible Japanese text must be rendered by the deterministic renderer, not baked into
AI-generated imagery whenever avoidable.

Why:
- avoids Japanese text corruption
- keeps typography consistent
- enables exact timing
- makes revision cheap

Default:
- max 2 lines
- phrase-based chunks, not full sentence dumps
- synchronized from word timestamps
- important phrase may scale / weight up
- no double subtitles
- no unrelated decorative copy

## Presenter rules

The reference video quality can be reached without generating a new cinematic clip for every line.

Preferred v1 strategy:
- create a reusable Shunri motion bank
- several neutral talking loops / pose variants
- mouth / face sync from narration when available
- cut between compatible variants based on scene plan
- overlay screenshots / diagrams above or beside presenter

This is more stable and cheaper than full generative video for every scene.

Suggested motion-bank minimum:
- neutral-talk
- open-hand
- point-up
- point-side
- think
- small-nod
- explain-both-hands
- CTA-forward

## Insert / B-roll rules

Supporting visual priority:
1. real ShunLP demo screenshot when the script discusses a feature
2. existing approved brand asset
3. generated diagram / concept visual
4. generated B-roll image / video

Do not use a random stock clip merely to avoid empty space.

## Audio

Narration is master.

BGM:
- must never mask speech
- duck automatically under narration
- no abrupt loop points
- mood chosen from the scene plan

SE:
- only for meaningful motion / emphasis
- no repetitive whoosh on every cut

## Editing rules

Target:
- 1080x1920
- 30fps default
- vertical safe zones
- hard cuts are the default
- punch-in / subtle push / short crossfade are allowed
- transitions are not decoration

Pacing:
- visible change roughly every 2-5s
- but do not force cuts against sentence rhythm
- inserts may be 1-3s
- emphasis shots may be shorter

## Quality gates

Automated QA must reject:
- missing narration
- canonical voice not used
- subtitle / narration mismatch
- overlapping duplicate subtitles
- text outside safe area
- silent / clipped audio
- broken media asset
- wrong aspect ratio
- visibly wrong Shunri identity
- unapproved script changes

Human Gate remains available before posting.

## Target architecture

    ChatGPT / @瞬理
         |
         v
    approved script
         |
         v
    Shunri scene planner
         |
         +--> Irodori canonical TTS
         |       |
         |       +--> Whisper alignment / word timestamps
         |
         +--> visual resolver
         |       +--> presenter motion bank
         |       +--> ShunLP screenshots
         |       +--> generated inserts
         |
         +--> BGM / SE resolver
         |
         v
    deterministic renderer
         |
         v
    MP4 + QA report
         |
         v
    scheduler Human Gate

## Implementation order

Phase 1 — reference-level talking Reel
- approved script
- Shunri TTS
- word timestamps
- presenter motion bank
- captions
- screenshot / diagram inserts
- BGM ducking
- MP4

Phase 2 — cinematic / editorial
- richer B-roll
- generated camera movement
- artist-photo visual DNA
- scene-level visual direction

Phase 3 — singing / MV
- music-first timing
- lyric timestamps
- performance shots
- cinematic continuity
- lip sync / singing animation
