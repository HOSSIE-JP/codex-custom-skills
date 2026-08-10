---
name: xna-to-godot-migration
description: Analyze and migrate XNA or MonoGame games using Microsoft.Xna.Framework, Content Pipeline/ContentManager, SpriteBatch, Game/GameComponent/DrawableGameComponent, XACT, and related APIs to Godot 4. Use for XNA-to-Godot porting or migration planning, staged implementation, asset conversion, lifecycle/input/audio/scene/UI/collision/camera/save-data translation, and validation; including requests phrased as XNA, MonoGame, Godot, 移植, 移行, migration, or porting. Do not use for ordinary Godot-only development or unrelated C# refactoring.
---

# XNA to Godot Migration

Migrate an XNA or MonoGame game without silently redesigning it. Establish evidence from source, content projects, assets, and a runnable baseline; then deliver a Godot port in small, testable stages.

## Non-negotiable rules

1. Treat the original project as read-only. Work in a new Godot directory or a dedicated branch/worktree.
2. Inspect before editing. Identify the authoritative executable project when a solution contains samples, tools, pipelines, or platform variants.
3. Preserve behavior, timing, presentation, balance, and content unless the user explicitly approves a change.
4. Separate facts, inferences, assumptions, and open questions. Do not implement an uncertain interpretation as fact.
5. Separate mechanical translations from design decisions. Automate only transformations with verifiable inputs and outputs.
6. Keep the project bootable. Build and run after every migration stage.
7. Replace unsupported platform services with an explicit fallback or report them as unsupported; never silently drop them.
8. Finish with changed files, validation evidence, unsupported items, fidelity gaps, and human decisions still required.

## Start with discovery

1. Locate `.sln`, `.csproj`, `.contentproj`, `.mgcb`, source roots, content roots, custom Content Pipeline extensions, and prebuilt binaries.
2. Determine framework/version, platform targets, C# language level, graphics profile, back-buffer size, fixed-step policy, and entry-point `Game` subclass.
3. Identify all `Game`, `GameComponent`, `DrawableGameComponent`, screen-manager, service, and global/static state relationships.
4. Inventory `Content.Load<T>`, pipeline asset names, runtime file access, dynamically constructed asset names, XACT cues, effects, fonts, models, video, localization, and save data.
5. Capture a behavioral baseline when runnable: screen flow, inputs, frame timing, screenshots/video, audio cue mapping, random seed behavior, collision, camera, and save paths.
6. Run the read-only scanner and save its JSON report outside the source tree unless the user requests otherwise:

   ```text
   python scripts/scan_xna_project.py <xna-root> --json
   ```

7. Produce a migration plan before implementation. Include scope, authoritative source, target Godot version/language/renderer/platforms, asset toolchain, phase gates, risks, fallbacks, and exclusions.

Read [migration-checklist.md](references/migration-checklist.md) during discovery and at each gate. Read [xna-godot-mapping.md](references/xna-godot-mapping.md) while building the dependency inventory.

## Classify every dependency

Maintain a table with: source symbol/file, XNA dependency, behavior, assets, state owner, target Godot construct, conversion class, validation, and status.

Use these conversion classes:

- **Mechanical**: namespace removal, type substitutions, constant conversion, asset path normalization, simple input action mapping.
- **Mechanical with verification**: coordinate/vector conversion, frame-count-to-seconds conversion, blend/sampler state translation, audio cue manifests, static model conversion.
- **Design decision**: scene boundaries, singleton ownership, save schema, custom shader behavior, collision representation, async loading, platform-service fallback.
- **Blocked or human review**: missing source assets, opaque XNB-only content, licensing, ambiguous source bugs, unavailable services, visual/audio choices without a baseline.

Do not let a scanner result decide architecture. Use it to find evidence and omissions.

## Map architecture before converting code

Read [architecture-patterns.md](references/architecture-patterns.md). Create a project-specific mapping before implementation:

- `Game` orchestration -> main scene plus focused autoload services.
- `GameComponent` -> `Node` or plain data/logic object.
- `DrawableGameComponent` -> `Node2D`, `Control`, `Node3D`, or a composed scene.
- `Update` -> `_physics_process` for deterministic gameplay or `_process` for presentation.
- `Draw`/`SpriteBatch` -> retained nodes first; `_draw`, canvas APIs, or rendering servers only when justified.
- screen stack -> scene router plus modal overlays with explicit pause and input ownership.
- global content/audio/input services -> narrow autoload services with stable interfaces.
- tightly coupled simulation/rendering -> pure domain state, runtime controller, and view/HUD layers.

Choose Godot C# when shared libraries or incremental code reuse dominate. Choose GDScript when engine integration, portability, Web export, or rapid scene iteration dominates. Record the choice; do not mix languages without a concrete benefit.

## Migrate in bootable increments

Use this order unless project evidence demands another dependency order:

1. **Skeleton**: create `project.godot`, main scene, target resolution/stretch/renderer, input actions, empty router, and one visible boot screen.
2. **Pure logic**: port rules, state machines, grids, scoring, deterministic RNG, and collision queries without rendering dependencies. Add headless tests.
3. **Core services**: input, audio cue compatibility, settings/profile/save paths, localization, and scene routing.
4. **Asset slice**: migrate only assets required for one complete vertical slice. Keep a reproducible manifest and conversion script.
5. **Vertical slice**: reproduce one real flow from input through simulation, rendering, audio, pause, and return/navigation.
6. **Feature expansion**: add remaining screens, entities, effects, content, saves, and platform fallbacks one group at a time.
7. **Parity and hardening**: compare timing, framing, orientation, UI layout, particles, cue choice, pause behavior, culling, persistence, and exports.

At each stage: parse/build, launch, exercise inputs, inspect visuals, listen to cues, run focused tests, and update the migration report. Do not accumulate multiple unverified subsystems.

## Preserve lifecycle and timing semantics

- Translate fixed `Update` logic to a fixed physics tick. Express frame-based durations as `frames / original_fps` seconds and test boundary frames.
- Use `delta` for variable-rate presentation. Do not multiply logic twice when moving already time-scaled XNA code.
- Define matrix/vector conventions at the boundary. Verify handedness, forward axis, vertical axis, winding, UV origin, camera projection, model pivots, and animation scale axes with known fixtures.
- Preserve RNG call order when deterministic behavior matters. Store and expose seeds in tests.
- Give pauseable gameplay nodes and timers pause-aware process modes while keeping only pause UI/input active.
- Replace static globals deliberately. Keep authoritative mutable state in one owner and communicate with signals or narrow methods.

## Migrate content from sources, not compiled artifacts

1. Resolve logical Content Pipeline names to source files and processor settings. Detect names built by string concatenation.
2. Prefer original PNG/JPG/TGA, WAV/OGG, font descriptions and font files, model sources, shader sources, and video sources. Treat XNB as a last-resort extraction problem.
3. Preserve import semantics: color key, premultiplication, filtering, mipmaps, loop points, volume, random cue variants, model scale/orientation, and shader parameters.
4. Normalize paths for cross-platform use; detect absolute paths, backslashes, case-only mismatches, duplicate normalized names, non-UTF encodings, and filename collisions.
5. Keep original logical asset/cue names in manifests when that reduces code churn.
6. Validate counts, dimensions/duration, channels, model AABB/materials/UV/winding, font glyph coverage, and unresolved references.

Read [common-pitfalls.md](references/common-pitfalls.md) before converting particles, models, audio, custom pipeline outputs, or pause behavior.

## Validate the Godot project

Run the bundled validator in read-only analysis mode:

```text
python scripts/validate_godot_project.py <godot-root> --json
```

Use `--strict` only in CI or when missing resources should fail the command. Use `--include-dev` when test fixtures and migration tools must also be audited; they are excluded by default because they commonly contain deliberate missing-resource and machine-local path fixtures. Supplement static validation with:

- headless tests for pure logic, timing, RNG, placement, collision, saves, and migrations;
- integration tests for complete screen flows, pause/resume, controller disconnect, and media skip;
- reference captures at the original internal resolution for UI, FOV, orientation, particles, and effects;
- cue-by-cue audio checks for category, volume, loop, variation, and pause behavior;
- clean Windows/Web or other requested exports plus smoke launches on target hardware/browser.

Static validation cannot prove behavioral or visual parity.

## Report the migration

End each milestone with:

1. Scope completed and files changed.
2. Mechanical conversions performed.
3. Design decisions made, with evidence and trade-offs.
4. Verification commands and results.
5. Known fidelity gaps and unsupported platform features.
6. Missing assets, licensing/tooling constraints, and human review items.
7. Assumptions that must be confirmed before the next phase.

Use `Not started / In progress / Ported / Verified / Blocked / Intentionally excluded` statuses. Never label a feature complete based only on compilation.

## Reference routing

- Read [xna-godot-mapping.md](references/xna-godot-mapping.md) for API, asset, and service mappings.
- Read [migration-checklist.md](references/migration-checklist.md) to plan and audit a full migration.
- Read [common-pitfalls.md](references/common-pitfalls.md) when behavior, visuals, audio, timing, assets, or exports diverge.
- Read [architecture-patterns.md](references/architecture-patterns.md) before choosing scene, node, service, state, pause, or rendering ownership.
- Read [trigger-tests.md](references/trigger-tests.md) when evaluating whether this Skill is too broad or too project-specific.
