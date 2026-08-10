# Architecture patterns

## Contents

- [Start from observable responsibilities](#start-from-observable-responsibilities)
- [Recommended layers](#recommended-layers)
- [Pure domain state plus runtime adapter](#pattern-pure-domain-state-plus-runtime-adapter)
- [View consumes state and events](#pattern-view-consumes-state-and-events)
- [Retained UI replaces SpriteBatch screens](#pattern-retained-ui-replaces-spritebatch-screens)
- [Scene router plus overlay stack](#pattern-scene-router-plus-overlay-stack)
- [Compatibility service interfaces](#pattern-compatibility-service-interfaces)
- [Grid/custom collision remains pure](#pattern-gridcustom-collision-remains-pure)
- [Camera as a view of logical pose](#pattern-camera-as-a-view-of-logical-pose)
- [Versioned local persistence](#pattern-versioned-local-persistence)
- [Deterministic content manifest](#pattern-deterministic-content-manifest)
- [Choosing Godot C# vs GDScript](#choosing-godot-c-vs-gdscript)
- [Migration dependency order](#migration-dependency-order)
- [Anti-patterns](#anti-patterns)

## Start from observable responsibilities

Do not map one source class to one Godot node automatically. For each class, identify:

1. authoritative mutable state;
2. fixed-step gameplay behavior;
3. presentation behavior;
4. tree/lifetime dependencies;
5. input and emitted events;
6. loaded assets and external services;
7. serialization requirements.

Then choose the smallest target construct that owns one coherent responsibility.

## Recommended layers

```text
Main scene
├── Screen router / transition host
├── Global services (audio, settings, input-device tracking)
└── Current screen
    ├── Runtime controller
    │   ├── Pure run/domain state
    │   └── Fixed-step rules / AI / collision
    ├── World view (2D or 3D)
    │   ├── Static environment
    │   ├── Entity views
    │   └── Stable transient-effects root
    └── HUD / menus / modal overlays
```

Keep this conceptual shape even when a small game combines nodes. It creates test seams and prevents UI/rendering from becoming authoritative game state.

## Pattern: pure domain state plus runtime adapter

Use a plain data object or `RefCounted` class for run state, maze/layout, rules, scoring, inventory, and deterministic RNG. Use a `Node` runtime adapter to:

- receive `_physics_process` and InputMap actions;
- advance domain state;
- emit semantic events such as `entity_hit`, `floor_completed`, or `item_opened`;
- coordinate view and audio services without putting engine nodes in saved state.

Benefits: headless tests, deterministic replay, easier C#-to-GDScript translation, and freedom to replace rendering.

## Pattern: view consumes state and events

Use `Node2D`/`Node3D` for environment and entity views. The view may interpolate presentation but must not independently decide damage, score, placement, or completion. Reconcile views by stable entity IDs.

Create transient hit/death/reward effects under a stable effects root. Pass a world-space transform snapshot with the event so freeing or moving the entity cannot relocate an effect.

## Pattern: retained UI replaces SpriteBatch screens

Convert each coherent screen to a `Control` scene or constructed hierarchy:

- use containers/anchors for layout;
- use TextureRect/AtlasTexture for source sprite regions;
- use CanvasLayer for stable HUD ordering;
- use `_draw` only for highly dynamic primitives such as minimaps or graphs;
- preserve the source internal resolution and letterbox policy before making layouts responsive.

Keep menu selection state separate from button visuals so keyboard/controller focus and mouse interaction share one action path.

## Pattern: scene router plus overlay stack

Represent base screens and modal overlays separately. Define operations such as:

```text
go_to(base_screen, payload)
push_overlay(overlay, payload)
pop_overlay()
```

The router owns fades, input blocking, pause state, and return targets. Overlays should not recreate or discard the underlying gameplay runtime unless the source does.

Pause design:

- pause the SceneTree or authoritative runtime;
- keep only router/overlay input and UI always-processing;
- ensure gameplay screens, world views, hand/HUD animation as appropriate, timers, and tweens are pauseable;
- pause relevant audio buses/players;
- test nested overlays such as Pause -> Settings -> Key Config -> Settings -> Pause -> Resume.

## Pattern: compatibility service interfaces

Preserve stable source vocabulary at subsystem boundaries when it reduces risk:

```text
AudioService.play_cue(source_cue_name)
AssetManifest.resolve(source_logical_name)
ScreenRouter.go_to(source_screen_role)
ProfileStore.load/save/update
```

Translate legacy implementation details inside the service/manifest rather than scattering renamed paths and cue variants through gameplay code.

Do not create an autoload for every source manager. Prefer autoloads only for truly cross-screen lifetime: settings, audio policy, input-device tracking, routing, and session/profile state.

## Pattern: grid/custom collision remains pure

If XNA gameplay uses discrete grid movement or order-dependent AABB checks, keep those rules as pure logic. Use Godot physics for presentation queries or free movement only when semantics match. A wholesale switch to `CharacterBody3D` can change corner behavior, event ordering, tunneling, and deterministic placement.

## Pattern: camera as a view of logical pose

Store a logical pose/direction in gameplay state. The view converts it to `Camera2D`/`Camera3D` transforms and interpolates movement/turns. This prevents camera tween progress from becoming the source of truth.

Define once:

- source and target forward/up axes;
- world units per source unit/cell;
- horizontal vs vertical FOV;
- near/far planes and aspect policy;
- model-facing correction.

For multiple views (split screen, stereo, render targets), share simulation and derive all cameras from the same logical pose in one update.

## Pattern: versioned local persistence

Use a versioned document under `user://`. Validate types, ranges, paths, and image sizes before mutating current state. Write defaults for missing data; migrate known older versions; preserve a readable error and safe session fallback for unavailable storage.

Separate user preference settings from run/game state when their lifetimes differ. Document platform storage locations and deletion behavior.

## Pattern: deterministic content manifest

Create a machine-generated manifest that maps source logical names/cues to normalized Godot resources and conversion metadata. Include source path, destination path, asset type, conversion tool/version/options, expected dimensions or counts, and unresolved/error status.

Generate destination names deterministically. Refuse ambiguous normalized collisions rather than choosing whichever file traversal finds first.

## Choosing Godot C# vs GDScript

### Prefer Godot C# when

- large pure C# libraries can remain engine-independent;
- existing tests/tooling are valuable;
- reflection/generics/data models would be costly to rewrite;
- target platforms support the selected Godot .NET build.

### Prefer GDScript when

- the port relies heavily on Godot scenes/resources/signals;
- rapid UI/render iteration matters more than source reuse;
- Web or other target constraints favor the standard engine build;
- source code is small enough that behavior-first rewriting is safer than adapter layers.

### Mixed-language guardrail

Use a language boundary only around a stable, testable API. Avoid alternating languages per class or mirroring the old inheritance tree across interop calls.

## Migration dependency order

Choose vertical slices based on dependency direction:

```text
constants/data -> pure rules -> runtime adapter -> services -> view/HUD -> complete screen flow
```

Asset conversion should follow slice demand, not “convert everything and hope.” After the conversion process is proven, bulk-convert and validate the remaining inventory.

## Anti-patterns

- One Godot node that manually calls every old `Update` and `Draw` method.
- A global service locator reproducing every XNA manager.
- Engine nodes embedded in save/domain state.
- Presentation tweens deciding collision or completion.
- Duplicate simulations for multiple viewports.
- Asset paths hard-coded throughout translated gameplay.
- Calling a subsystem ported because it compiles without a behavioral gate.
