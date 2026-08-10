# GB layout, conversion, menu, and release gates

## Contents

- Layout policies
- Seam-resistant GBC conversion
- Choice menus
- Generated-resource ownership
- Official build and runtime evidence

## Layout policies

Use `messageSafeWide` for scenes with a four-line dialogue area and `fullscreenStill` for event CGs without dialogue UI.

For `messageSafeWide`, compose artwork into the top 160x96 and reserve the lower 48 pixels for dialogue. Preserve that UI band exactly during posterization and palette fitting. For `fullscreenStill`, fill all 160x144 pixels and reject flat lower bands inherited from storyboard or caption templates.

Keep title, logo, and menu text deterministic and clear prompt tiles before transition.

## Seam-resistant GBC conversion

The legal limits are at most four colors per 8x8 tile, at most seven background palettes, and at most 384 unique tiles. Treat them as ceilings, not quality targets.

Use this order:

1. compose the final 160x144 screen and protect deterministic UI pixels;
2. reduce near-duplicate art colors with one shared no-dither global palette, commonly 24 to 32 colors;
3. derive tile palettes from that shared color set;
4. assign palettes with a spatial penalty for unnecessary changes between neighboring tiles;
5. quantize each tile to its assigned four-color palette;
6. validate tile count, palette count, UI colors, and native-size appearance.

Starting quality budgets are five palettes for content and four for deterministic title or logo screens when the art permits. Increase only with visual evidence. Independent best-fit palettes per tile often produce 8x8 hue or value seams even when every tile is technically valid.

Do not use dithering to hide palette errors in flat cel art. Prefer broad same-color regions, hard value steps, dark connected outlines, and lower micro-detail. Record both the hardware ceiling and the observed palette histogram. Inspect representative 160x144 cuts and a GBC/DMG contact sheet; compiler warning count alone does not prove good reduction.

## Choice menus

Use the dialogue-width layout for two or three options when labels need the normal message-window width. Avoid a narrow right-side menu that clips Japanese or crowds three rows.

Add a short input-release wait immediately before every menu, especially after a fullscreen still or message closed with A. A six-frame wait is a proven starting point; tune only with runtime evidence. Keep B cancel disabled when the design requires a committed choice.

Validate three layers:

1. source resource: option count, labels, target IDs, full-width layout, and input guard;
2. compiled output: `.MENUITEM` up/down links and option indices;
3. runtime: wait for typewriter completion, then test first, middle, and last options with visible real input.

If hidden Electron or CDP automation always selects the first option while generated links are correct, treat focus and timing as a harness limitation. Do not collapse a valid three-choice design to two solely to satisfy broken hidden automation. Require a visible or manual gate.

## Generated-resource ownership

Identify the project generator that owns backgrounds, scenes, fonts, music, manifests, and `.gbsres`. Change the authority and regenerate; do not patch a derived resource alone. Keep stable semantic IDs and fail stale outputs or invalid references.

## Official build and runtime evidence

Use the intended GB Studio version. Close the normal editor before regeneration. Quote non-ASCII paths and use an isolated user-data profile and dedicated port for automation.

Export ROM and Web through the official editor action. Capture warnings, size, ROM SHA-256, Web ROM SHA-256, and the mixed-mode header when applicable. Drive the built-in emulator with real input from a clean state, capture changed visual cuts, and verify ending return/reset. State flash-cart, physical display, physical audio, and any visible-menu input check as external gates when they were not run.
