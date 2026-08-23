---
name: compose-pce-psg
description: Compose and revise original PC Engine / TurboGrafx-16 PSG BGM, songs, sound effects, jingles, and loops from a high-level musical score, then generate a deterministic PCE Game Editor version 2 PSG JSON and music audit. Use for HuC6280 six-channel composition or an import-ready *.psg.json; stop before project integration, builds, or playback QA.
---

# Compose PCE PSG

Turn a musical brief into an original, editable high-level score and a deterministic PCE Game Editor PSG asset. Creative decisions belong in the score; scripts calculate pitch periods, expand motifs and durations, detect structural problems, and produce audit evidence.

## Workflow

1. Read [request-template.md](references/request-template.md) and normalize purpose, emotion, scene function, profile, form, density, and loop intent. Ask only when a missing choice materially changes the music.
2. Read the selected profile and relevant review lenses in [music-theory-lenses.md](references/music-theory-lenses.md). Treat them as diagnostic lenses with counterexamples, never as universal composition laws.
3. Copy [score-template.json](assets/score-template.json) outside the skill directory. Author form, harmony or modal plan, motifs, part roles, channel allocation, ranges, and notes according to [score-format.md](references/score-format.md).
4. Compose in four passes:
   - form and motif recurrence/variation;
   - melody, harmony or modal center, and voice leading;
   - rhythm, rests, density, register, timbre, and channel balance;
   - loop seam and repetition-fatigue review.
5. Record each pass in `review.passes`. Do not mark audition complete unless a person actually listened to a preview, PCE Game Editor playback, emulator, or hardware.
6. Generate all standard artifacts:

   ```powershell
   node "<skill-dir>\scripts\compose-pce-psg.js" --score "<score.json>" --out "<output-dir>"
   ```

   Add `--preview` only when an approximate WAV is useful for audition. It is not a hardware-faithful render or a standard deliverable.
7. Read both audit files. Fix `technical-error` findings and address or explicitly waive each `profile-warning`. Static analysis alone cannot prove naturalness.
8. Verify the SHA chain:

   ```powershell
   node "<skill-dir>\scripts\verify-pce-psg-artifacts.js" --audit "<output-dir>\<id>.audit.json"
   ```

9. Deliver the score, PSG JSON, audit JSON, and audit Markdown. State whether audition is complete or still an external gate.

## Essential constraints

- New work uses score schema version 2 and one of `tonal`, `modal`, `ambient`, `action`, or `sfx-jingle`.
- Note names or MIDI notes are authoritative. The generator derives 12-TET A4=440 Hz periods with the current HuC6280 clock formula and rejects an explicit period that disagrees.
- The grid is fixed at four steps per quarter note. True swing, triplets, microtonality, and continuous pitch bend are outside version 2.
- Use at most six monophonic channels. The generator rejects overlapping notes on one channel rather than stealing a voice. Noise is valid only on channels 4 and 5.
- PCE Game Editor output remains one version 2 `psg-song` or `psg-sfx` asset, with at most 4096 steps and 2048 pattern events.
- A song loops over the complete asset. Use `intentionalDiscontinuity` only when an audible seam is a deliberate composition choice.
- Do not reproduce a copyrighted melody. Convert references into abstract tempo, register, texture, rhythm, energy, and form traits.
- `transform.transpose` is additive on top of the occurrence's literal `note`; note-name range comparison (`range.min`/`range.max`) is chromatic within the octave, not alphabetical (e.g. `F2 < Bb2`); and `form[].function` (≤128 chars), `review.notes[]` entries (≤256 chars), and `review.passes.<pass>.notes` (≤512 chars) all have real enforced length caps. See [score-format.md](references/score-format.md).

## Legacy scores

For an existing schema version 1 event score, migrate without inferring harmony, motifs, tonality, or style:

```powershell
node "<skill-dir>\scripts\migrate-pce-psg-score.js" --score "<v1-score.json>" --out "<output-dir>"
```

Migrated `legacyExact` parts preserve the old PSG JSON bytes. Their audit intentionally skips musical-style conclusions.

## Scope boundary

Stop before importing the asset into PCE Game Editor, registering scene cues, modifying a project, building HuCARD or CD-ROM2 media, or claiming emulator/hardware playback. Those checks belong to the PCE integration skill. CD-DA, ADPCM, voice generation, external DAW production, MusicXML, and engraved notation are outside this skill.

## Output contract

Standard output contains exactly:

- `<id>.score.json`: normalized editable score and recorded review decisions.
- `<id>.psg.json`: import-ready PCE Game Editor version 2 asset.
- `<id>.audit.json`: hashes, objective metrics, findings, and review state.
- `<id>.audit.md`: human-readable audit.

An optional `<id>.preview.wav` is produced only with `--preview`.
