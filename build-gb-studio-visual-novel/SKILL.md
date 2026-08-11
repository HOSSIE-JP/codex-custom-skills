---
name: build-gb-studio-visual-novel
description: Build, port, repair, and validate dialogue-heavy visual novels in GB Studio for Game Boy Color. Use for branching story scripts, deterministic imports from another engine, Japanese bitmap fonts and multi-page encoding, dialogue windows and typewriter input, speaker text sounds, persistent face or bust portraits, expression state, event stills, VN-specific audio substitution, or bugs involving garbled text, damaged window frames, portrait visibility, and scene-state carryover. Use together with build-gb-studio-game for shared GB Studio assets, editor safety, official exports, and emulator QA.
---

# Build GB Studio Visual Novel

## Goal

Deliver a deterministic GB Studio visual novel whose source text, branches, fonts, portraits, stills, audio cues, generated resources, and compiled output agree. Use `build-gb-studio-game` as the shared foundation; keep this skill focused on VN behavior and import integrity.

## Load the relevant guidance

- Read `references/dialogue-fonts-and-portraits.md` before implementing Japanese text, window behavior, title prompts, text sounds, portraits, expressions, or event stills.
- Read `references/deterministic-vn-imports.md` before importing scripts from another engine, splitting source scenes, generating stable resources, translating audio, or writing an import manifest.
- Run `scripts/pack_vn_font_pages.py` when the script needs deterministic atomic multi-page BDF packing.
- Run `scripts/validate_vn_text_encoding.py` after an official GB Studio build when Japanese compiler bytes must match the selected runtime font page.

## Workflow

### 1. Establish target and source authority

1. Identify the exact GB Studio and engine version, GBC mode, sprite mode, music driver, project schema, and official build path.
2. Determine whether the VN is editor-authored, generator-authored, or imported. Patch the authoritative generator, never only its generated `.gbsres` output.
3. Inventory source scenes, commands, messages, choices, labels, jumps, backgrounds, expressions, stills, songs, voices, and effects before generation.
4. Decide observable acceptance behavior for dialogue advance, window timing, title input, timeout, portrait persistence, stills, branch joins, ending, and return flow.

### 2. Normalize the story graph

Convert source data to a normalized intermediate representation before emitting GB Studio resources. Give every command a source location and every generated ID a stable semantic key.

Split GB Studio scenes at background changes when necessary. Carry background, expression, portrait visibility, music, and other visual state across generated segments and branch-only source scenes. Give every jump, choice arm, timeout, and ending a valid target.

Fail on unknown commands, duplicate IDs, unresolved references, unreachable required content, missing joins, or source-command count mismatch. Do not silently drop a command because the target has no direct equivalent.

### 3. Build Japanese text atomically

Normalize visible text consistently and group strings that must use one font page. A message is one atomic unit; both labels of a single choice belong to the same unit.

For Japanese dialogue, render a visible first-line speaker label such as `【話者】` before the body; leave narration unlabeled. Apply the label before glyph extraction and page packing so the delimiters and speaker name are guaranteed to exist on the selected page. For this inline-label layout, default named messages to `textY=0` so the label overlaps the upper frame row and keep narration at `textY=1`. Record the label format and both Y policies in the import manifest, validate every generated event, and inspect a native runtime capture.

Pack only glyphs used by the script. Keep GB Studio compiler and runtime page selection coupled with `!F:<font-id>!` before every message, choice label, and SpriteText payload. Exclude syntax-sensitive byte values and keep physical PNG tile positions aligned with byte codes.

Validate the generated mapping, PNG indices, event tags, visible text, and compiled assembly bytes. An editor preview or readable JSON string is not proof that the ROM encodes the same page.

### 4. Implement dialogue presentation

Show and hide the dialogue overlay instantly unless the request explicitly asks for animation. Preserve the standard two-stage typewriter input: A while text is rendering completes the current text; the next A closes or advances it.

Reserve or reload frame tiles and reset the text buffer before every framed overlay when dynamic fonts share UI VRAM. Derive addresses from the target engine and hash any engine override; do not reuse addresses from another version by assumption.

Clear or restore the exact title-prompt tilemap region before leaving the title so prompt rows and horizontal lines cannot leak into the next frame. Assign text tones by speaker and treat narration as an explicit speaker class.

### 5. Compose VN visuals for GBC

Resize GBC-only backgrounds to the 160-pixel target width before cropping. Reserve the dialogue region in the composition rather than destroying source detail to satisfy an unmeasured tile estimate.

Convert large standing art to readable face or bust portraits. Remove transparent headers, preserve the complete alpha extent, fit inside a transparent gutter, and use GB Studio index colors plus a deliberate OBJ palette.

Track each character's latest expression and side independently. Keep portraits visible across dialogue when scanline limits permit, hide all portraits during event stills, and restore only the state required after the still. Compute simultaneous portrait capacity from the ten-sprites-per-scanline limit.

### 6. Translate audio intentionally

Replace unsupported voice clips with speaker-specific text tones unless voice playback is explicitly in scope. Map source music channels and cues to the selected GB Studio driver, replace streaming or CD audio with named BGM or jingles, and document every substitution in the manifest.

Test music start, stop, loop, scene carryover, jingles, text tones, warnings, and effects in the built game. A copied asset that is not registered and triggered is not integrated.

### 7. Validate generated and compiled output

Require the import manifest to prove full source consumption, stable references, font assignments, source hashes, generated counts, substitutions, and external gates. Compare normalized source and generated visible text.

Use the exact GB Studio version to save a disposable copy and produce official ROM and Web exports. Apply the common build, hash, editor, and emulator gates from `build-gb-studio-game`.

Before handoff, try to disprove completion:

- Can a font page render black blocks or the wrong glyph despite valid JSON?
- Can text overwrite window-frame VRAM?
- Can one A press both complete and dismiss text?
- Can a title prompt leave a line in the next scene?
- Can a still leave a portrait visible?
- Can three aligned portraits exceed the scanline limit?
- Can an editor Canvas fix move compiler-relative sprite coordinates?
- Can any source command, message, or branch disappear from the manifest?

Report focused automated coverage separately from any full manual playthrough or physical-hardware gate delegated to the user.
