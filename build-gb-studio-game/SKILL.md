---
name: build-gb-studio-game
description: Build, repair, export, and quality-assure GB Studio games for Game Boy and Game Boy Color. Use for empty or existing GB Studio projects, .gbsproj/.gbsres editing, scene and input flow, GBC asset conversion, DMG four-shade background conversion and dark-tone correction, sprite/metasprite layout, music integration, ROM/Web export, built-in emulator testing, save-data verification, or bugs where the editor view differs from source PNG assets. For dialogue-heavy visual novels, use this shared foundation together with build-gb-studio-visual-novel.
---

# Build GB Studio Game

## Goal

Deliver a GB Studio project that opens cleanly, builds with the intended GB Studio version, and can be played through its required paths. Treat generated assets, editor resources, exported artifacts, and runtime behavior as separate verification surfaces.

## Load the relevant guidance

- Read references/project-implementation.md before creating or changing scenes, variables, input handlers, generated .gbsres files, or save flow.
- Read references/assets-and-metasprites.md before generating or converting art, editing sprite resources, diagnosing split or scrambled frames, or changing palette and tile budgets.
- Read references/dmg-four-shade-backgrounds.md before converting backgrounds for DMG or mixed-mode projects, correcting crushed dark tones, or fitting four-shade art into the 192-unique-tile budget.
- Read references/runtime-and-release-qa.md before exporting, driving the built-in emulator, writing a playthrough harness, or declaring the game complete.
- Run scripts/validate_metasprite_layout.py for sheet-based sprites whose Canvas composition must reproduce source PNG frames.
- For dialogue-heavy visual novels, Japanese multi-page fonts, branching script imports, persistent portraits, or event stills, also use `build-gb-studio-visual-novel` and load its VN-specific references.

## Workflow

### 1. Establish the real project state

1. Read repository instructions and inspect the full workspace before editing.
2. Locate the .gbsproj file, project resources, asset directories, generators, validators, build outputs, and the installed GB Studio version.
3. Determine which files are authoritative. If a generator owns .gbsres files, fix the generator and regenerate; do not patch only derived output.
4. Preserve unrelated user changes. Close the normal editor before external regeneration so stale in-memory state cannot overwrite disk changes.
5. Test the target-version editor save in a disposable copy before normalizing generated resources; selecting a resource may recompute fields such as `numTiles`.
6. Create a scoped restore archive before a broad regeneration or schema migration.

### 2. Define acceptance criteria as observable paths

Translate the request into a matrix that includes:

- boot, logo, title, menu, selection, cancel, and wrap behavior;
- every player input and cursor boundary;
- normal, win, loss, draw, retry, game-over, victory, and ending branches;
- every character or difficulty and every progression stage;
- life, round, score, and state limits;
- save creation, clean boot without save data, and reload persistence;
- ROM and Web exports when both are requested.

Do not equate a successful build with a playable game.

### 3. Implement a bounded state machine

Model scenes and variables explicitly. Initialize state before installing input callbacks. Remove scene-local input callbacks before transitions and install the next scene's callbacks after entry. Avoid blocking loops in interactive scenes.

Keep event IDs, scene IDs, actor IDs, variable IDs, and symbols stable and unique. Validate all references after generation. See references/project-implementation.md.

### 4. Build assets for the final display size

Retain source art separately from converted GBC assets. Crop characters for readability at native resolution; a face or bust crop is usually clearer than shrinking a full-body sheet into a small sprite.

For GBC-only backgrounds, resize to the 160-pixel target width before cropping or composing. Do not pre-emptively reduce resolution for a guessed 192-tile limit; measure the actual target-version build and only degrade when the real budget requires it.

Quantize deliberately, use nearest-neighbor scaling after pixel conversion, measure color and unique-tile budgets, and inspect contact sheets at native size. Keep sprite index colors separate from the intended OBJ palette. See references/assets-and-metasprites.md.

For DMG and `Color + Monochrome` backgrounds, estimate four tone classes per image from perceptual luminance. Exclude uniform dialogue or UI bands from threshold estimation, but render and validate the complete 160 by 144 image. Require meaningful use of all four DMG shades, not merely four RGB entries. Measure unique 8 by 8 tiles after every conversion and relax the adaptive thresholds only as far as required to fit the 192-tile limit. See references/dmg-four-shade-backgrounds.md.

### 5. Treat metasprite Canvas layout as data, not as a PNG preview

GB Studio sprite tiles are 8 by 16 pixels. PNG sliceY is top-down, while the metasprite Canvas Y coordinate is bottom-up. For a top-aligned source frame:

    canvas_y = canvas_height - 16 - (slice_y - source_frame_top)

For horizontal frame sheets, keep source sliceX separate from the X displayed by the editor. GB Studio 4.3.1 applies this child offset:

    editor_offset_x = max(0, canvas_width / 2 - 8)
    editor_x = stored_x + editor_offset_x
    compiler_relative_x = stored_x - canvas_origin_x
    slice_x = source_frame_left + editor_x

For a 40-pixel Canvas the editor offset is 12 pixels, so a valid resource can store negative tile X. Verify every populated frame by reconstructing the editor-visible Canvas and comparing it with the intended source crop. Run:

    python scripts/validate_metasprite_layout.py PATH_TO_PROJECT --pattern "assets/sprites/**/*.png.gbsres"

Use --require-populated-frames N when every checked sheet must contain exactly N populated frames.
Use `--expect-compiler-relative-x=-20,-12,-4,4,12` when a layout change must preserve that exact runtime-relative X vector. Use `--editor-grid-offset-x none` only for a deliberately legacy stored-coordinate check.

### 6. Integrate music and timing as gameplay

Use a format and driver supported by the project version. Register the resource through GB Studio rather than merely copying a file. Test start, stop, loop, transitions, and cues in the built game; timing that compiles can still feel or behave incorrectly.

### 7. Build through the actual GB Studio toolchain

Open and save the project with the target GB Studio version. Inspect the editor representation of fragile resources. Export official ROM and Web builds, collect warnings, compare embedded ROM hashes, and keep the exact artifacts used for runtime testing.

When automating the desktop editor, quote the project path, use an isolated user-data profile and a dedicated remote-debugging port, and discover version-specific editor actions from that installation instead of hardcoding module numbers. Verify the document is unmodified before closing it.

### 8. Test through real input and visible state

Start from a fresh isolated save state. Drive the built-in emulator with normal key events, wait for observable scene or variable changes, and capture screenshots and a trace. Retry a missed input only while asserting that the game remains in the expected source scene.

Cover the acceptance matrix, including negative and persistence paths. Deterministic variable overrides may shorten repeated combat, but first prove that ordinary cursor input works and record every override in the evidence.

### 9. Run adversarial final gates

Before handoff, confirm:

- project validation reports no missing or duplicate IDs and no invalid references;
- all required inputs have non-empty callbacks and interactive scenes have no blocking loop;
- all required sprites pass stored, editor-visible, and compiler-relative coordinate checks plus Canvas reconstruction;
- source and converted asset dimensions, palettes, and tile counts fit the target;
- every required DMG background preserves ordered dark detail, uses all four shades meaningfully in its artwork region, and records its thresholds, shade histogram, and unique-tile count;
- official builds finish without unexplained warnings;
- ROM and Web ROM hashes match when they should;
- the complete playthrough evidence passes from a clean state;
- temporary inspectors, isolated editor processes, and stale diagnostic files are removed;
- external gaps such as flash-cart or physical-device testing are stated explicitly.

Report exact artifacts, hashes, test counts, warnings, and remaining external gates. Never claim completion from screenshots, schema checks, or compilation alone.
