---
name: compose-gb-studio-vn-bgm
description: Compose, generate, integrate, and validate original looping four-channel ProTracker MOD background music for GB Studio visual novels using the hUGE driver. Use when a GB Studio VN needs scene cue planning, chiptune track specifications, deterministic MOD output, B00 looping, .gbsres registration, official ROM/Web build verification, or runtime music-transition QA. Do not use for MIDI, UGE authoring, streaming audio, or non-GB Studio music production.
---

# Compose GB Studio VN BGM

## Goal

Turn a stable VN scene cue plan into original looping four-channel MOD tracks whose files, GB Studio resources, scene events, official builds, and runtime behavior agree.

## Load the relevant guidance

- Read `references/cue-design.md` before choosing track count, mood, tempo, reuse, or silence.
- Read `references/mod-and-gb-studio.md` before generating MOD data, registering resources, exporting, or testing.
- Also use `build-gb-studio-game` and `build-gb-studio-visual-novel` for project ownership, official exports, and emulator QA.

## Workflow

### 1. Scaffold and lock cues

Run:

```powershell
python scripts/scaffold_vn_bgm.py --out <project>\source\vn-bgm
```

Complete `music-cues.json` before composing. Give every cue a narrative function, scenes, mood, BPM range, energy, entry/exit behavior, loop requirement, and silence policy. Prefer a small reusable score over one track per scene.

### 2. Author a deterministic track spec

Create one `track-spec.json` per track. Use up to 16 steps per 64-row pattern with four fixed roles:

1. melody;
2. harmony/pulse counterline;
3. wave-style bass;
4. noise drums.

Use only original note sequences. Do not imitate a named copyrighted song or artist.

### 3. Generate and validate MOD

```powershell
python scripts/compose_mod.py --spec <track-spec.json> --out <track.mod> --report <compose-report.json>
python scripts/validate_mod.py --mod <track.mod> --spec <track-spec.json> --report <validation-report.json>
```

The generator must emit a four-channel `M.K.` MOD, set BPM with `Fxx`, and end the final pattern with `B00` when looping is required. Repeated generation from the same spec must be byte-identical.

Use `--gbsres-out` only when the spec contains the project generator's real stable resource ID, symbol, and project-relative filename. Never invent or replace project-specific IDs inside the skill.

### 4. Integrate through the project authority

Determine which generator owns music `.gbsres` files and scene events. Register the MOD there, preserve stable IDs, and map cue entry/exit behavior explicitly. A copied MOD that is not triggered is not integrated.

Do not silently replace unsupported music with another format. Initial scope is hUGE-compatible ProTracker MOD only.

### 5. Build and test

Use the exact target GB Studio version to export official ROM and Web builds. Record warnings, ROM hash, Web ROM hash, and source/report hashes.

Drive the built-in emulator with real input. Verify track start, stop, loop, scene carryover, transitions, ending cues, and intentional silence. Listen for stuck notes, drum overload, tempo changes, and audible loop gaps. State physical-device audio as an external gate unless tested.

## Delivery contract

Report cue map, track specs, MOD/resource paths, BPM, patterns, instruments, loop effect, hashes, registered scene IDs, official build evidence, runtime transitions, and external audio gates.
