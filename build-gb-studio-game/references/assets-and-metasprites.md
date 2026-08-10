# Assets and metasprites

## Asset pipeline

Keep three layers distinct:

1. source references and generated master art;
2. deterministic conversion inputs and scripts;
3. GB Studio-ready backgrounds, sprites, palettes, and music.

Retain generation prompts and source provenance when image generation is used. Do not destructively overwrite the only high-resolution source.

Inspect supplied references before generating variants. Keep identity, hair, face, palette, and costume logic consistent across stages. For sensitive wardrobe contexts, establish that all depicted characters are adults and follow the user's non-explicit content boundary.

## Compose for Game Boy Color readability

Judge assets at 160 by 144 output size and at the sprite's native pixel dimensions.

- Prefer face or bust crops for character portraits and small battle sprites.
- Use strong silhouettes, separated value groups, and readable facial features.
- Avoid shrinking a full-body reference into a narrow sprite when recognition is the goal.
- Keep critical details away from UI text, life indicators, and hand icons.
- Generate a contact sheet of every state and inspect it without smoothing.

Quantize before final inspection. Use nearest-neighbor resizing after pixel conversion and remove semitransparent fringe pixels. Measure actual RGB colors and unique 8 by 8 tiles; do not assume a visually simple image fits the background budget.

## GBC-only background composition

Treat 160 by 144 as the composition target. For a wider source, first resize once to 160 pixels wide while preserving aspect ratio, then crop or place the result for the intended UI layout. Do not repeatedly lower an intermediate resolution to satisfy a guessed DMG or 192-tile limit.

A full screen contains 20 by 18 tile positions. GBC-only projects can use substantially more scene tiles than a conservative cross-mode estimate, but the engine and UI may still reserve data. Measure the converted image and the official build for the exact target version. Reduce detail only after a measured tile, bank, or palette failure.

## Portrait crop and indexed color

When converting a large portrait or expression cell:

1. remove transparent rows above the first opaque pixel;
2. find and preserve the complete horizontal alpha extent;
3. take a face-to-bust crop rather than shrinking the full body;
4. scale with nearest-neighbor to an inner box;
5. center it inside the Canvas with a transparent gutter.

For a 40 by 48 portrait, a 38 by 46 inner box leaves a one-pixel gutter and prevents edge clipping. Validate every expression, not only the first frame.

GB Studio sprite PNG colors are palette indices, not the final display palette. Use the exact index carrier colors `E0F8CF`, `86C06C`, and `071821` for the three opaque levels, plus transparency. Store the intended character colors in OBJ slots from lightest to darkest. Arbitrary source RGB values can collapse to the default preview even when the PNG has three visible colors.

For overlapping scanlines, a portrait of width `W` consumes `ceil(W / 8)` hardware sprites. The Game Boy limit is ten sprites per scanline, so aligned 40-pixel portraits consume five each and allow at most two. Compute the limit from actual overlap rather than promising three actors from total scene sprite count.

## GB Studio sprite geometry

GB Studio composes sprite resources from 8 by 16 tiles. A source PNG uses a top-left origin. The metasprite Canvas stores Y from the bottom. Keep three horizontal coordinate spaces separate:

    editor_offset_x = max(0, canvas_width / 2 - 8)
    editor_x = stored_x + editor_offset_x
    compiler_relative_x = stored_x - canvas_origin_x

The official GB Studio 4.3.1 `MetaspriteGrid` uses that editor offset. Verify the installed editor implementation again for other versions or pass an explicit offset to the validator.

For a source frame beginning at source_frame_top:

    canvas_y = canvas_height - 16 - (slice_y - source_frame_top)

For a source frame beginning at source_frame_left:

    editor_x = slice_x - source_frame_left
    stored_x = editor_x - editor_offset_x

Equivalent invariants for every tile in one rectangular frame are:

    slice_x - editor_x = source_frame_left
    slice_y + canvas_y = source_frame_top + canvas_height - 16

If sliceY is copied directly into Canvas y, the top and bottom tile rows exchange positions. A three-row bust sprite then appears split into vertical sections even though the raw PNG looks correct.

For a horizontal sheet of three 32 by 48 frames, each frame contains twelve 8 by 16 tiles. Example source offsets are 0, 32, and 64. Within each frame, sliceY values 0, 16, and 32 map to Canvas y values 32, 16, and 0.

For a 40 by 48 Canvas in GB Studio 4.3.1, the editor offset is 12. Stored tile X `-12,-4,4,12,20` displays at `0,8,16,24,32`. If `canvasOriginX` is 8, compiler-relative X is `-20,-12,-4,4,12`. Changing stored X and the origin by the same delta can fix the editor without moving the runtime sprite.

## Exact reconstruction test

Do not stop at checking the coordinate formula. Reconstruct each populated Canvas:

1. crop every 8 by 16 source tile at sliceX and sliceY;
2. apply flipX and flipY when present;
3. add the target editor offset to stored X;
4. paste at editor X and top-down destination canvas_height - 16 - Canvas y;
5. compare the RGBA bytes with the intended source frame crop.

Run the bundled validator:

    python scripts/validate_metasprite_layout.py PROJECT_ROOT --pattern "assets/sprites/**/*.png.gbsres"

For a known animation sheet:

    python scripts/validate_metasprite_layout.py PROJECT_ROOT --pattern "assets/sprites/characters/*_stage_*.png.gbsres" --require-populated-frames 3

For a 40-pixel portrait whose runtime placement must remain fixed:

    python scripts/validate_metasprite_layout.py PROJECT_ROOT --pattern "assets/sprites/portraits/*.png.gbsres" --require-populated-frames 2 --expect-compiler-relative-x=-20,-12,-4,4,12

Use --coordinates-only only when a sprite intentionally reuses or transforms source tiles and exact source-crop equality is not expected.

`--editor-grid-offset-x none` can reproduce a legacy stored-coordinate crop, but it does not prove that the current editor shows the full Canvas. If `auto` fails and `none` passes, inspect the resource in the target editor for a left gap or right overflow before accepting legacy mode.

## Visual QA

Inspect at least:

- raw PNG sheet;
- index carrier colors and the selected OBJ palette;
- GB Studio tile palette;
- each frame's Canvas;
- the actor in the actual scene;
- the exported game at native scale.

A correct PNG does not prove a correct .gbsres Canvas, and a correct Canvas does not prove correct actor placement or palette selection. Compare stored resource data, editor-visible composition, and runtime placement independently.
