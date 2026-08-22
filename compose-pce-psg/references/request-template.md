# Composition request

Normalize the brief into these decisions before writing a score. Use defaults when a missing value does not materially change the requested music.

## Musical decisions

- Purpose: looping BGM/song or one-shot SFX/jingle.
- Asset ID: 1-48 ASCII letters, numbers, `_`, or `-`.
- Scene function: what the music should help the player feel or understand, and what it must not mask.
- Emotion and energy/tension curve by section.
- Style profile:
  - `tonal`: functional stability, departure, tension, and return are relevant.
  - `modal`: modal center, characteristic scale degrees, pedal tones, and color matter more than V-I syntax.
  - `ambient`: space, slow change, timbre, and controlled repetition take priority.
  - `action`: pulse, ostinato, syncopation, density, and sectional energy take priority.
  - `sfx-jingle`: a short, legible gesture; one-shot by default.
- Form, bar count, motif identity, variation plan, harmony or pitch-center plan, part roles, ranges, and timbres.
- Loop return: smooth or intentionally discontinuous.

## Defaults

| Decision | Default |
| --- | --- |
| Type | `psg-song` |
| Loop | Complete-asset loop for songs; disabled for SFX |
| Profile | Infer from scene function; use `tonal` only when functional harmony is actually intended |
| BPM | 120 |
| Meter/grid | 4/4, four 16th-note steps per quarter note |
| Form | 16 bars with at least two meaningfully contrasted sections |
| Hardware target | `generic`; integration validates CD-ROM2 and HuCARD separately |
| Master volume | 100 |
| Speed metadata | 6 |
| Tone wave | 45 unless another timbre is intentional |
| Audition | `pending` until listening really occurs |

## Brief normalization record

Before authoring, state a compact working plan containing:

- purpose, emotions, profile, BPM, meter, bars, and loop intent;
- section functions and energy/tension trajectory;
- harmonic or modal plan;
- one or more motifs and explicit variation operations;
- melody, secondary voice, harmony/pad/arpeggio, bass, and percussion roles actually needed;
- fixed channel and register allocation;
- density, rests, and dialogue-masking constraints;
- intended loop-seam behavior.

This plan becomes the score rather than remaining an untracked event-writing note.
