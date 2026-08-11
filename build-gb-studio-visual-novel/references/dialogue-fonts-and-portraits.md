# Dialogue, fonts, and portraits

## Japanese font pages

Treat text selection, byte mapping, physical font tiles, runtime page selection, and compiler output as one contract.

1. Normalize source-visible strings to NFC.
2. Form atomic units. A message is one unit; both labels of one choice share a unit; a SpriteText payload is one unit.
3. Extract only the glyphs used by those units.
4. Pack each unit wholly into one page. Duplicate common glyphs across pages when needed.
5. Fail if a single unit needs more safe codes than one page provides.
6. Build `.gbsres` metadata from a template produced by the exact GB Studio version.

Use this input shape with the bundled packer; placing both choice labels in one `texts` array makes the page assignment atomic:

```json
{"units":[{"id":"choice:scene:1","texts":["はい","いいえ"]}]}
```

The packer emits indexed PNGs, mapping JSON, assignments, and hashes. It intentionally does not emit `.gbsres` files because their schema and IDs belong to the target-version project generator.

For the GB Studio 4.3.x text path validated by this skill, physical tiles represent byte codes 32 through 255. Keep all 224 physical slots present. Exclude these syntax-sensitive codes from mappings and leave their physical tiles blank:

- `0x25`: runtime formatted-text prefix;
- `0x5C`: assembler escape prefix.

This leaves 222 safe mapped codes per page. Map code `N` to physical tile `N - 32`; do not compact the PNG around reserved holes. Use palette index 0 for glyph pixels and index 3 for the background. A visually black PNG can be an index-order failure, not a missing glyph.

Prepend `!F:<font-id>!` to every message, choice label, and non-empty SpriteText. The tag makes the compiler encode following Unicode text with the same page selected at runtime. Validate all of these surfaces:

- every visible character exists in the selected mapping;
- no mapped value is below 32 or equals a reserved code;
- font resource IDs agree with inline tags;
- generated visible text matches the normalized source;
- compiled scene assembly contains the expected page control and encoded bytes.

Do not bundle a third-party BDF in a reusable skill. Keep the original download, license, source hash, and any modification notes in the project.

## Speaker-label line

Make the speaker visually distinct from the body before font-page packing. For Japanese dialogue, use this default rendering:

```text
【話者】
本文
```

- Render `【{speaker}】\n{sourceText}` for a named speaker.
- Render narration as `sourceText` with no empty or decorated speaker line.
- Normalize the speaker, delimiters, newline, and body as one atomic message unit so `【` and `】` are included in the selected font page.
- Keep `speaker`, `sourceText`, and `generatedText` separately in the manifest.
- Record `dialogueRuntime.speakerLabelFormat` as `【{speaker}】` and validate the manifest, generated `EVENT_TEXT`, selected font mapping, and compiled bytes against it.
- For this inline-label style, set named messages to `EVENT_TEXT.textY = 0`. The label occupies the upper frame row while the three body lines begin below it.
- Keep unlabeled narration at `EVENT_TEXT.textY = 1`; do not move narration upward merely because spoken lines use Y=0.
- Store `namedSpeakerTextY`, `narrationTextY`, and `speakerLabelOverlapsFrame` in authoritative runtime data and copy the resolved `textY` into each manifest message record.
- Validate the policy in every generated hardware-mode event and inspect a native 160x144 runtime capture for frame collision, label legibility, and body-line clipping.

If a project deliberately uses a name box, avatar, or another label style, declare that format and its Y policy explicitly instead of silently omitting the distinction.

## Dialogue window and input

Use an instant overlay speed for entry and exit unless animation is explicitly requested. Verify behavior with real input:

1. while typewriter text is incomplete, A reveals the rest;
2. that A press is consumed by completion;
3. the next A closes or advances the message.

Do not add a hidden wait or an input latch that turns this into three presses. Do not change it to one press that both completes and dismisses the message.

Dynamic font loading can overwrite UI tiles or move the text allocation pointer. Inspect the target engine's UI implementation and reserve its actual frame-tile range. Before each framed message or choice:

- reload or restore frame tiles;
- reset the text buffer to the first safe text tile;
- set the selected font page;
- set the speaker tone;
- then display the overlay.

Engine tile numbers and buffer addresses are version-specific. Record the engine version and hash any override instead of copying constants from another game.

For a title prompt drawn into the background or overlay tilemap, clear or restore the exact prompt rows before switching scenes. Capture the next frame and check for horizontal lines, stale glyphs, or palette remnants.

## Speaker tones

Represent narration and every speaker explicitly. Store tone frequency and duration in data rather than scattering literals through events. Apply the tone immediately before every message so branch joins and narration cannot inherit the previous character's sound. Treat voice-to-tone replacement as an audio substitution in the import manifest.

## Portrait conversion

For each source expression cell:

1. remove the keyed or transparent background;
2. skip transparent rows above the first opaque pixel;
3. preserve the full horizontal alpha extent;
4. choose a face-to-bust crop;
5. scale with nearest-neighbor into an inner box;
6. center it inside a transparent Canvas gutter;
7. generate a native-scale contact sheet for all expressions.

A proven 40 by 48 layout uses a 38 by 46 inner box and one transparent pixel on each edge. Use exact GB Studio sprite index colors `E0F8CF`, `86C06C`, and `071821`; put the intended character colors in OBJ slots from lightest to darkest.

Track expression and placement state per character. A speaker change does not imply that every other portrait disappears. Keep the most recent visible portraits until a source hide, scene rule, or scanline limit removes them.

For sprites overlapping the same scanline:

    tiles_per_portrait = ceil(portrait_width / 8)
    maximum_portraits = floor(10 / tiles_per_portrait)

A 40-pixel portrait uses five sprites per scanline, so two aligned portraits are safe and three are not. Validate actual vertical overlap as well as total sprite count.

## Event stills

Hide every portrait before showing a full event still. Do not reveal a portrait merely because a character speaks while the still remains active. On leaving the still, restore only the visual state required by the destination segment; do not resurrect stale branch-local expressions.

Validate at native scale: background or still, dialogue frame, text, palette, portrait crop, portrait position, and scanline occupancy.
