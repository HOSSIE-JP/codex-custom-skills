# Voice design prompts (optional)

An optional, recognized skill deliverable: a standalone markdown file, one "VoiceDesign prompt" per speaking character, meant to be pasted into an external TTS voice-design tool (e.g. Irodori-TTS VoiceDesign) to synthesize a reference voice profile per character before that voice is used for line-by-line dialogue synthesis.

Keep this file separate from the image-prompts document — mirror its structure/spirit, but never merge the two.

## Per-character entry contents

- age/gender target — explicitly force a *child* voice for young characters, since TTS tools default to adult;
- accent/dialect;
- pitch/timbre;
- pace/rhythm;
- default emotional baseline;
- a reference sample line.

All of this reformats existing `character-bible.json` fields — `voice.style` and `sampleLine` — into TTS-prompt language. No new authoring is needed beyond reformatting.

## Scope boundary

Actual audio synthesis and ADPCM authoring remain out of scope for this skill (unchanged). The mechanical next step — per-line batch synthesis — is already built into the editor and documented in `PLUGIN.md`'s "VN Irodori-TTS バッチ出力 API" section: the `vn:exportIrodoriBatch` and `vn:inspectIrodoriVoiceAssignments` IPC channels (per-speaker CSV export from the scene doc, and CSV-verified ADPCM-to-message reassignment). Cross-reference that section rather than re-describing it here; it needs no new tooling from this skill.
