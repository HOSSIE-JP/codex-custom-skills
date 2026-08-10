# GB layout, conversion, and release gates

## Layout policies

Use `messageSafeWide` for scenes with a four-line dialogue area and `fullscreenStill` for event CGs without dialogue UI.

For `messageSafeWide`, compose artwork into the top 160x96 and reserve the lower 48 pixels for dialogue. For `fullscreenStill`, fill all 160x144 pixels and reject flat lower bands inherited from storyboard/caption templates.

Keep title/logo/menu text deterministic and clear prompt tiles before transition.

## Quantization defaults

Measure exact 160x144 output, at most four colors per 8x8 tile, at most seven background palettes, and at most 384 unique tiles. These are authoring gates, not substitutes for the target-version compiler. Record any measured project-specific override in the project brief.

Prefer flat source art and strong silhouettes over destructive post-quantization. Inspect a native-size contact sheet.

## Generated-resource ownership

Identify the project generator that owns backgrounds, scenes, fonts, music, manifests, and `.gbsres`. Change the authority and regenerate; do not patch a derived resource alone. Keep stable semantic IDs and fail stale outputs or invalid references.

## Official build and runtime evidence

Use the intended GB Studio version. Close the normal editor before regeneration. Quote non-ASCII paths and use an isolated user-data profile and dedicated port for automation.

Export ROM and Web through the official editor action. Capture warnings, size, ROM SHA-256, and Web ROM SHA-256. Drive the built-in emulator with real input from a clean state and capture changed visual cuts. State flash-cart or physical-display checks as external gates.
