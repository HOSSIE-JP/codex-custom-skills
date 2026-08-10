# Migration checklist

Mark each item `Not started`, `In progress`, `Ported`, `Verified`, `Blocked`, or `Intentionally excluded`. “Builds” is not equivalent to “Verified.”

## Contents

- [1. Safety and scope](#1-safety-and-scope)
- [2. Source and project inventory](#2-source-and-project-inventory)
- [3. Dependency inventory](#3-dependency-inventory)
- [4. Behavioral baseline](#4-behavioral-baseline)
- [5. Architecture plan](#5-architecture-plan)
- [6. Godot skeleton](#6-godot-skeleton)
- [7. Pure logic](#7-pure-logic)
- [8. Assets and Content Pipeline removal](#8-assets-and-content-pipeline-removal)
- [9. Runtime systems](#9-runtime-systems)
- [10. Vertical slice gate](#10-vertical-slice-gate)
- [11. Full parity and robustness](#11-full-parity-and-robustness)
- [12. Final report](#12-final-report)

## 1. Safety and scope

- [ ] Confirm the original source tree will not be edited.
- [ ] Create a new Godot directory or dedicated branch/worktree.
- [ ] Record existing dirty files and preserve user changes.
- [ ] Identify the authoritative game project among samples, tools, tests, and platform variants.
- [ ] Record target Godot version, language, renderer, OS/browser, architecture, resolution, and frame/tick rate.
- [ ] Define included game flow and explicit exclusions.
- [ ] Record licensing and redistribution questions without inventing answers.

## 2. Source and project inventory

- [ ] Locate solutions/projects and determine XNA/MonoGame version.
- [ ] Find the `Game` entry point and startup configuration.
- [ ] List `GameComponent` and `DrawableGameComponent` subclasses.
- [ ] Map screen/state flow, overlays, fades, loading, pause, and exit paths.
- [ ] Map mutable global/static state and event subscriptions.
- [ ] Inventory platform-specific APIs and conditional compilation.
- [ ] Record screen size, graphics profile, fixed-step settings, and device reset handling.
- [ ] Run `scan_xna_project.py` and archive the report.

## 3. Dependency inventory

- [ ] List Content Pipeline imports/processors/readers/writers.
- [ ] Extract all literal `Content.Load<T>` names.
- [ ] Review dynamic content names built from variables or concatenation.
- [ ] Inventory SpriteBatch calls, render targets, states, shaders, models, and particles.
- [ ] Inventory keyboard, mouse, controller, vibration, and device-change behavior.
- [ ] Inventory SoundEffect/Song/MediaPlayer and XACT cues/categories/variations.
- [ ] Inventory collision, camera, coordinate, unit, and projection conventions.
- [ ] Inventory save/profile/localization/runtime file access.
- [ ] Classify each item as mechanical, verify-required, design decision, or blocked.

## 4. Behavioral baseline

- [ ] Build and run the original when possible.
- [ ] Record build/tool versions and required external dependencies.
- [ ] Capture every screen at the internal resolution.
- [ ] Record a representative gameplay path and timing.
- [ ] Record camera framing/FOV, model facing, animation, particles, and blend behavior.
- [ ] Record cue names, music per scene/stage, volumes, loops, and random variants.
- [ ] Record default controls, held/pressed/repeat semantics, and controller prompts.
- [ ] Record RNG seed behavior and any deterministic fixtures.
- [ ] If the original cannot run, label all inferred behavior and sources of evidence.

## 5. Architecture plan

- [ ] Choose Godot C#, GDScript, or a justified combination.
- [ ] Map XNA classes to scenes, nodes, pure objects, and services.
- [ ] Define authoritative game/run/save state owners.
- [ ] Separate simulation, presentation, HUD, and asset services.
- [ ] Define scene routing, overlay stacking, pause, and input ownership.
- [ ] Define asset manifests and reproducible conversion scripts.
- [ ] Define unit, integration, visual, audio, and export test gates.
- [ ] Review [architecture-patterns.md](architecture-patterns.md).

## 6. Godot skeleton

- [ ] Create `project.godot` and a bootable main scene.
- [ ] Configure viewport size, stretch, renderer, physics tick, and target feature set.
- [ ] Add InputMap actions with keyboard/controller defaults.
- [ ] Add only essential autoloads with narrow responsibilities.
- [ ] Implement a visible boot screen and route to one empty gameplay scene.
- [ ] Parse/build and smoke-launch before continuing.

## 7. Pure logic

- [ ] Port enums, constants, state, game rules, scoring, grids, and algorithms.
- [ ] Preserve integer/float boundary behavior.
- [ ] Convert frame durations to seconds using the original tick rate.
- [ ] Make RNG seedable and test call-order-sensitive results.
- [ ] Add headless tests for rules, collision, placement, and transitions.
- [ ] Keep pure logic independent of `Node`, rendering, and loaded assets where practical.

## 8. Assets and Content Pipeline removal

- [ ] Locate original source assets instead of relying on XNB.
- [ ] Capture importer/processor settings before removing pipeline dependencies.
- [ ] Detect absolute paths, backslashes, case mismatches, and normalized-name collisions.
- [ ] Decode text using known encodings; never assume UTF-8 for legacy projects.
- [ ] Convert a minimal vertical-slice asset set first.
- [ ] Validate image sizes/alpha/filtering/atlas regions.
- [ ] Validate model hierarchy/AABB/scale/facing/winding/UV/materials/animation.
- [ ] Validate audio duration/channels/loop/cue/category/variation.
- [ ] Validate font licensing and glyph coverage.
- [ ] Port shaders against the selected renderer/platform.
- [ ] Generate a manifest and prove unresolved references are zero.

## 9. Runtime systems

- [ ] Input preserves pressed/held/released and device switching.
- [ ] Audio preserves cue mapping, categories, music transitions, pause, and polyphony.
- [ ] Scene routing preserves flow, fades, popups, loading, and back navigation.
- [ ] UI matches the internal resolution and survives aspect-ratio changes.
- [ ] Collision preserves source ordering and boundary semantics.
- [ ] Camera matches source FOV, height, clipping, and orientation.
- [ ] Save data uses `user://`, versioning, validation, and safe fallback.
- [ ] Unsupported online/platform features have an approved fallback or exclusion.
- [ ] Pause stops gameplay, timers, tweens, enemies, particles, and countdown while pause UI remains interactive.

## 10. Vertical slice gate

- [ ] Start from a clean boot.
- [ ] Navigate using keyboard and controller.
- [ ] Enter real gameplay, move, collide, attack/interact, and hear correct cues.
- [ ] Pause/resume without background progress.
- [ ] Reach a result/next/return transition.
- [ ] Compare screenshots/video/audio to the baseline.
- [ ] Fix discrepancies before expanding scope.

## 11. Full parity and robustness

- [ ] Complete all requested game flows, difficulties/stages, endings, and failure paths.
- [ ] Verify particles in local/global coordinates and after parent movement/freeing.
- [ ] Verify countdown boundary display and game-over trigger timing.
- [ ] Verify culling never exposes missing geometry; use fog only as a presentation choice.
- [ ] Verify save corruption, absent devices, missing media, and fallback behavior.
- [ ] Run long lifecycle/stability tests for duplicate signals and leaks.
- [ ] Test clean target exports on real OS/browser/hardware.
- [ ] Run `validate_godot_project.py` and resolve or document findings.

## 12. Final report

- [ ] List changed/generated files and conversion tools.
- [ ] List commands and exact pass/fail results.
- [ ] Report content counts and unresolved references.
- [ ] Report fidelity gaps and known regressions.
- [ ] Report unsupported/excluded features and fallbacks.
- [ ] Report assumptions and human decisions still required.
- [ ] Provide target build paths and launch instructions.
- [ ] Confirm the original project remains untouched.
