# Voice design prompts (optional)

An optional, recognized skill deliverable: a standalone markdown file, one "VoiceDesign prompt" per speaking character, meant to be pasted into an external TTS voice-design tool (e.g. Irodori-TTS VoiceDesign) to synthesize a reference voice profile per character before that voice is used for line-by-line dialogue synthesis.

Keep this file separate from the image-prompts document — mirror its structure/spirit, but never merge the two.

## Prompt style: short, Japanese, audio-only

VoiceDesign interprets voice qualities (pitch, huskiness, pace, emotional restraint) more reliably from a short, concrete instruction than from a long descriptive one. Write each character's actual VoiceDesign prompt to this spec, not the looser style of the surrounding prose:

- Japanese, not English.
- About 1-2 sentences.
- No character background, relationships, or story context — that belongs in `character-bible.json`, not here.
- Only traits that actually change the audio: age, pitch, huskiness, pace, emotional restraint, and (if needed) a short dialect tag like "強い地方訛り" or "東北訛り". Do not force every category into every character — include only what is actually distinctive for that voice.
- No per-line-varying performance direction (e.g. "gets more talkative in key scenes", "stutters when startled"). Those describe how a specific line reads, not the base voice; VoiceDesign only needs the stable baseline.
- No duplicate phrasing — each clause should add a new fact, not restate the previous one in different words.
- Explicitly state age up front for any young/child character, since TTS tools default to an adult voice otherwise (e.g. "12歳の少女。").

Target granularity example: `70代の男性。低く強くしゃがれたダミ声で、強い地方訛りがある。ゆっくり寡黙に話し、感情を抑えた重い響き。`

## Per-character entry contents

- age/gender target;
- accent/dialect (short tag only, per the style rule above);
- pitch/timbre;
- huskiness, if distinctive;
- pace;
- baseline emotional restraint/energy (not per-line variation);
- a reference sample line (kept separate from the VoiceDesign prompt itself, for use as VoiceDesign preview text).

Source this from existing `character-bible.json` fields — `voice.style` and `sampleLine` — but do not transcribe `voice.style` verbatim: it is written for narrative/authoring purposes and typically contains background and per-line acting detail that must be stripped out per the style rule above before it becomes a VoiceDesign prompt.

## Scope boundary

Actual audio synthesis and ADPCM authoring remain out of scope for this skill (unchanged). The mechanical next step — per-line batch synthesis — is already built into the editor and documented in `PLUGIN.md`'s "VN Irodori-TTS バッチ出力 API" section: the `vn:exportIrodoriBatch` and `vn:inspectIrodoriVoiceAssignments` IPC channels (per-speaker CSV export from the scene doc, and CSV-verified ADPCM-to-message reassignment). Cross-reference that section rather than re-describing it here; it needs no new tooling from this skill.
