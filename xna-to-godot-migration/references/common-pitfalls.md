# Common migration pitfalls

## Contents

- [Choosing the wrong source of truth](#choosing-the-wrong-source-of-truth)
- [Treating XNB as the asset source](#treating-xnb-as-the-asset-source)
- [Missing dynamic content references](#missing-dynamic-content-references)
- [Legacy paths and encodings](#legacy-paths-and-encodings)
- [Line-for-line lifecycle ports](#line-for-line-lifecycle-ports)
- [Fixed-frame logic running at variable rate](#fixed-frame-logic-running-at-variable-rate)
- [Countdown off by one](#countdown-off-by-one)
- [Pause UI works but gameplay continues](#pause-ui-works-but-gameplay-continues)
- [SpriteBatch semantics lost](#spritebatch-semantics-lost)
- [UI replaced with debug labels](#ui-replaced-with-debug-labels)
- [Model facing, scale, or pivot is wrong](#model-facing-scale-or-pivot-is-wrong)
- [Camera framing differs despite matching FOV number](#camera-framing-differs-despite-matching-fov-number)
- [Over-aggressive culling exposes black space](#over-aggressive-culling-exposes-black-space)
- [Particles spawn in unrelated positions](#particles-spawn-in-unrelated-positions)
- [Particle amount tuning misses the real mismatch](#particle-amount-tuning-misses-the-real-mismatch)
- [Audio files migrated but cues are wrong](#audio-files-migrated-but-cues-are-wrong)
- [Font replacement changes layout](#font-replacement-changes-layout)
- [Save data copied to the executable directory](#save-data-copied-to-the-executable-directory)
- [Source bugs silently fixed](#source-bugs-silently-fixed)
- [Platform features disappear](#platform-features-disappear)
- [Build-only validation](#build-only-validation)
- [Generalized examples retained from a real migration](#generalized-examples-retained-from-a-real-migration)

## Choosing the wrong source of truth

**Failure:** Porting a sample, console project, stale branch, or pipeline test instead of the shipped desktop game.

**Countermeasure:** Compare entry points, project references, content roots, configuration, and reachable screen flow. Declare one authoritative project and treat the rest as evidence or exclusions.

## Treating XNB as the asset source

**Failure:** Importing compiled XNB directly or extracting it without accounting for custom processors and lost metadata.

**Countermeasure:** Resolve logical names through `.contentproj`/`.mgcb` to original sources. Record processor parameters, color keys, mipmaps, premultiplication, scale, and custom readers. Use XNB extraction only when no source exists and label fidelity risk.

## Missing dynamic content references

**Failure:** A regex finds literal `Content.Load` calls but misses names assembled from stage, character, language, or frame indexes.

**Countermeasure:** Flag every non-literal load expression. Expand its domain from constants, loops, enums, and data tables. Verify the manifest against runtime paths and expected counts.

## Legacy paths and encodings

**Failure:** Windows-only absolute paths, backslashes, case-only mismatches, Japanese encodings, or normalized filename collisions work locally and fail on export/Web/Linux.

**Countermeasure:** Scan raw bytes and try the documented/project encoding after UTF-8. Normalize destination names deterministically, keep a source-to-destination manifest, and detect collisions before copying. Validate case using actual directory entries.

## Line-for-line lifecycle ports

**Failure:** Recreating one giant `Game` node with a manual `Update`/`Draw` dispatcher, causing hidden ordering, pause, and ownership bugs.

**Countermeasure:** Keep pure state and algorithms, but map ownership to scenes/nodes/services. Use explicit process priority only where source order is observable. Test complete transitions, not isolated callbacks.

## Fixed-frame logic running at variable rate

**Failure:** Frame counters are decremented in `_process`, or already time-scaled values are multiplied by `delta` again.

**Countermeasure:** Identify the original fixed tick. Convert `N` frames to `N / fps` seconds or retain integer ticks in `_physics_process`. Test first/last active frames and countdown display boundaries.

## Countdown off by one

**Failure:** The HUD displays `1` while the underlying float is below one and game-over already triggers.

**Countermeasure:** Define whether display uses floor, ceil, or integer ticks and when expiration occurs. Derive both display and transition from one authoritative clock. Test values around zero and exactly one tick.

## Pause UI works but gameplay continues

**Failure:** A parent viewport or root is set to always-process so gameplay, tweens, timers, particles, or audio inherit that mode.

**Countermeasure:** Keep only the overlay/input branch active. Mark the normal screen, simulation, 3D view, presentation layers, and gameplay timers pauseable. Test state and positions over real elapsed time while paused, including nested settings menus.

## SpriteBatch semantics lost

**Failure:** Draw order, source regions, origin, flip, blend, sampler, or premultiplied alpha changes when replacing calls with UI nodes.

**Countermeasure:** Record every `Begin` state and Draw overload. Group retained nodes by CanvasLayer/z-order and reproduce atlas regions/pivots. Compare transparent edges and additive effects against reference captures.

## UI replaced with debug labels

**Failure:** Logic is visible but the original texture-based HUD, frames, controller diagrams, and typography are never reconstructed.

**Countermeasure:** Trace SpriteBatch keys and source rectangles back to sprite sheets and source images. Rebuild original composition at the internal resolution. Use a substitute font only when the original is unavailable and report it.

## Model facing, scale, or pivot is wrong

**Failure:** An enemy shows its back, stairs sink into the floor, a chest floats, or death scaling collapses along the wrong axis.

**Countermeasure:** Validate imported AABB and pivot with known floor/contact points. Document source forward/up axes and handedness. Apply conversion once at the import/scene boundary; keep animation scale relative to the corrected base transform.

## Camera framing differs despite matching FOV number

**Failure:** A wall fills the ported view although the source shows floor and side walls.

**Countermeasure:** Determine whether FOV is horizontal or vertical, and match aspect, camera height, near plane, projection matrix, viewport, and world scale. Compare a fixed pose at the original internal resolution.

## Over-aggressive culling exposes black space

**Failure:** Optimization removes distant floor/walls visible through corridors.

**Countermeasure:** Establish conservative visibility first. Cull using cells/frustum plus a margin, and account for alternate/stereo views. Increase render extent before using distance fog to hide the transition. Test long sight lines and rapid turns.

## Particles spawn in unrelated positions

**Failure:** Hit/death/chest particles use a local coordinate as global, inherit a moved parent transform, or are reparented after emission.

**Countermeasure:** Define the event position in world space once. Convert with `to_global`/`to_local` at the ownership boundary. Add transient effects to a stable world effects root and snapshot the transform before freeing the source entity. Test from multiple cells, rotations, and moving parents.

## Particle “amount” tuning misses the real mismatch

**Failure:** Increasing particle count makes the effect obscure the screen but still looks wrong because lifetime, spread, velocity, scale, color curve, emission shape, or blend mode differs.

**Countermeasure:** Reconstruct the distribution and time curve before tuning amount. Capture frames at spawn, midpoint, and end. Tune in camera pixels/world units at the original resolution.

## Audio files migrated but cues are wrong

**Failure:** The correct WAV/OGG files exist, yet the wrong floor music plays, random variants disappear, kill sounds trigger without player involvement, or pause does not affect categories.

**Countermeasure:** Build a cue manifest from XACT or source calls. Preserve cue names, wave lists, weights, volumes, loops, categories, and triggering conditions. Separate collision/contact events from confirmed damage/death events. Log cue name plus gameplay cause during QA.

## Font replacement changes layout

**Failure:** A substitute font clips text, changes menu widths, lacks Japanese glyphs, or renders outlines differently.

**Countermeasure:** Extract SpriteFont size/spacing/style and glyph set. Choose a licensed fallback, validate glyph coverage, and tune layout/outline at reference resolution. Do not bake source font metrics into unrelated UI constants.

## Save data copied to the executable directory

**Failure:** The port assumes write access next to the executable, fails under installed locations/Web, or leaves undocumented data.

**Countermeasure:** Use `user://`, a versioned schema, validation, migration, and explicit deletion documentation. For Web, account for per-origin Local Storage/IndexedDB persistence. Make portable mode a deliberate optional design, not an implicit path trick.

## Source bugs silently “fixed”

**Failure:** A suspicious condition, balance value, event subscription, or result grade is changed without confirming intended behavior.

**Countermeasure:** Reproduce and document source behavior first. Classify the item as confirmed bug, intentional quirk, test-only override, or ambiguous. Obtain approval for behavior changes and protect them with tests.

## Platform features disappear

**Failure:** Sign-in, achievements, friends, marketplace, trial mode, avatars, vibration, or storage selectors are deleted because Godot has no direct equivalent.

**Countermeasure:** Inventory every platform API. Choose per feature: native plugin, local substitute, safe no-op, UI removal, or explicit exclusion. Report user-visible consequences and required human/product decisions.

## Build-only validation

**Failure:** The project parses and exports, so the migration is called complete despite broken input, visuals, audio, timing, or navigation.

**Countermeasure:** Require staged smoke runs, headless domain tests, screen-flow tests, reference captures, audio cue checks, long lifecycle tests, and clean target exports. Report exactly what was and was not exercised.

## Generalized examples retained from a real migration

- A legacy content tree contained absolute texture paths and case mismatches; deterministic normalization plus a manifest eliminated unresolved references.
- Static models converted successfully but still required AABB, winding, UV, floor contact, and facing checks; conversion success alone did not prove usability.
- XACT cue names were preserved behind a new audio service, reducing gameplay-code churn while categories and random variants moved to data.
- Separating grid simulation from 3D view/HUD enabled deterministic headless tests and later render optimizations without changing rules.
- A pause-input workaround made an entire viewport always-process; explicitly restoring pauseable modes on gameplay branches fixed background progression.
- Effects looked intermittent because local and global positions were mixed; a stable world-effects owner and coordinate snapshots fixed hit, death, and reward effects together.
