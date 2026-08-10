# XNA / MonoGame to Godot mapping

Use this as a decision aid, not a blind substitution table. Prefer a Godot scene/node design that preserves observable behavior over a line-for-line port.

## Contents

- [Lifecycle and ownership](#lifecycle-and-ownership)
- [Time, math, and random](#time-math-and-random)
- [Graphics and SpriteBatch](#graphics-and-spritebatch)
- [Content Pipeline and assets](#content-pipeline-and-assets)
- [Input](#input)
- [Audio and media](#audio-and-media)
- [Scene, UI, collision, camera, and persistence](#scene-ui-collision-camera-and-persistence)
- [C# conversion guidance](#c-conversion-guidance)

## Lifecycle and ownership

| XNA / MonoGame | Godot 4 candidate | Migration notes |
|---|---|---|
| `Game` | main scene `Node` + focused autoloads | Keep boot orchestration in the main scene; do not turn the whole game into one singleton. |
| `Game.Initialize` | `_init`, `_enter_tree`, `_ready` | Create data in `_init`; access the tree and children in `_ready`. |
| `Game.LoadContent` | scene resources, `preload`, `load`, service initialization | Prefer editor/imported resources; avoid a global “load everything” phase unless required. |
| `Game.UnloadContent` | `_exit_tree`, resource ownership, `queue_free` | Most `Resource` objects are reference counted. Explicitly stop external handles and transient players. |
| `Game.Update(GameTime)` | `_physics_process(delta)` or `_process(delta)` | Fixed gameplay belongs in physics; presentation can use variable processing. |
| `Game.Draw(GameTime)` | retained nodes, `_draw`, `RenderingServer` | Split scene construction from per-frame state updates. |
| `GameComponent` | `Node` or `RefCounted` domain service | Use `Node` only when tree lifecycle/signals/process callbacks are useful. |
| `DrawableGameComponent` | `Node2D`, `Control`, `Node3D`, composed scene | Separate simulation from presentation instead of inheriting just to gain Draw. |
| `Game.Components` order | scene tree order, process priority, explicit controller | Make ordering dependencies explicit and test them. |
| `Enabled`, `Visible`, `UpdateOrder`, `DrawOrder` | `process_mode`, `set_process`, `visible`, `process_priority`, CanvasLayer/z-index | Do not assume visibility disables processing. |
| custom screen stack | scene router + modal overlay stack | Define transition, input, pause, and lower-screen update rules explicitly. |

## Time, math, and random

| XNA / MonoGame | Godot 4 candidate | Migration notes |
|---|---|---|
| `GameTime.ElapsedGameTime` | `delta` | Both are seconds conceptually; XNA value is `TimeSpan`. |
| `GameTime.TotalGameTime` | accumulated state or `Time` APIs | Use an accumulated simulation clock when pause/determinism matters. |
| `IsFixedTimeStep`, `TargetElapsedTime` | `physics/common/physics_ticks_per_second` | Preserve the source tick rate before tuning. |
| `Vector2`, `Vector3`, `Quaternion`, `Matrix` | Godot equivalents, `Transform2D`, `Transform3D`, `Basis`, `Projection` | Verify multiplication order, handedness, forward axis, and units. |
| `Rectangle`, `BoundingBox`, `BoundingSphere`, `Ray` | `Rect2`, `AABB`, `SphereShape3D`/math, ray queries | Preserve inclusive/exclusive edge semantics. |
| `Color` | `Color` | Check byte-vs-float constructors and sRGB/linear use. |
| `MathHelper` | `deg_to_rad`, `lerp`, `clamp`, constants | Check angle units at every boundary. |
| `System.Random` | `RandomNumberGenerator` | Seed explicitly and preserve call order for reproducible gameplay. |

## Graphics and SpriteBatch

| XNA / MonoGame | Godot 4 candidate | Migration notes |
|---|---|---|
| `GraphicsDeviceManager` | `project.godot`, `DisplayServer`, `Window` | Configure internal resolution, stretch, renderer, fullscreen, and vsync independently. |
| `GraphicsDevice.Viewport` | `Viewport`, `SubViewport`, camera projection | Viewport mutation often indicates split-screen, compositing, or post-processing. |
| `GraphicsDevice.Clear` | `WorldEnvironment`, viewport clear mode, background control | Preserve clear color and transparency requirements. |
| `SpriteBatch.Begin/End` | `Sprite2D`, `TextureRect`, `Control`, `_draw` | Retained nodes are the default; batch manually only for measured hotspots. |
| `SpriteBatch.Draw(Texture2D, ...)` | `Sprite2D`, `TextureRect`, `draw_texture_rect_region` | Preserve source rectangle, origin, rotation, scale, flip, color, and layer depth. |
| `SpriteBatch.DrawString` | `Label`, `RichTextLabel`, `draw_string` | Preserve alignment, outline/shadow, line breaks, fallback glyphs, and scaling. |
| `SpriteSortMode`, `layerDepth` | tree order, z-index, CanvasLayer | Explicitly map ordering; XNA sort mode changes batching and order. |
| `BlendState` | `CanvasItemMaterial`, `StandardMaterial3D`, shader blend mode | Pay attention to premultiplied alpha and additive particles. |
| `SamplerState` | texture import filtering/repeat + material state | Pixel art and atlases often require nearest/no-mipmap. |
| `RasterizerState`, `DepthStencilState` | material cull/depth flags, viewport/render settings | Verify face winding after coordinate conversion. |
| `RenderTarget2D` | `SubViewport` + `ViewportTexture` | Set update and clear modes; avoid duplicating simulation for multiple views. |
| `BasicEffect` | `StandardMaterial3D` + camera/light | Match vertex colors, texture enablement, lighting, fog, and matrices. |
| custom `Effect` / HLSL | Godot shader | Port semantics and passes, not syntax. Validate uniforms and blend/depth state. |
| `Model`, `ModelMesh`, `ModelBone` | imported glTF scene, `MeshInstance3D`, `Skeleton3D` | Preserve hierarchy, pivots, materials, animation, and bounds. |
| hardware instancing | `MultiMeshInstance3D` | Keep per-instance transforms/colors; add culling without visible holes. |
| XNA particles | `GPUParticles2D/3D`, `CPUParticles`, custom pool | Match spawn space, lifetime, velocity distribution, size/color curves, and ownership. |

## Content Pipeline and assets

| XNA / MonoGame | Godot 4 candidate | Migration notes |
|---|---|---|
| `ContentManager` | imported resources + small asset/service manifests | Remove global Content lifetime assumptions. |
| `Content.Load<T>("logical/name")` | `preload("res://...")`, `load`, manifest lookup | Keep logical names in a manifest when many callers depend on them. |
| `.contentproj` / `.mgcb` | reproducible conversion/import scripts | Capture importer/processor parameters before discarding the pipeline. |
| `.xnb` | original source asset; extraction only as fallback | XNB omits or transforms information and may use custom readers. |
| `Texture2D` | `Texture2D` resource | Validate dimensions, alpha, color space, filtering, repeat, and regions. |
| `SpriteFont` | `FontFile`, `FontVariation`, Theme | Locate the font description and actual font; check licensing and glyph coverage. |
| sprite sheet/custom reader | `AtlasTexture` or JSON/Resource manifest | Preserve key names and exact pixel regions. |
| `.x`, FBX, custom model processor | glTF 2.0 preferred, imported scene | Verify AABB, vertices/faces/materials, winding, UV, scale, and facing. |
| HLSL `.fx` | `.gdshader` | Replace unsupported features per target renderer; compare captures. |
| pipeline XML/custom data | JSON, `.tres`, custom `Resource` | Define schema/version and test parsing/migration. |

## Input

| XNA / MonoGame | Godot 4 candidate | Migration notes |
|---|---|---|
| `Keyboard.GetState` | InputMap + `Input.is_action_pressed` | Preserve held vs just-pressed behavior and key chords. |
| `Mouse.GetState` | `_input`, mouse events, `Input` | Account for stretch/viewport coordinate transforms. |
| `GamePad.GetState` | InputMap, joypad APIs | Dead zones, trigger ranges, button naming, and disconnect behavior need tests. |
| `GamePad.SetVibration` | `Input.start_joy_vibration` | Treat unsupported devices/platforms as a no-op. |
| polling previous/current state | `is_action_just_pressed/released` or explicit state | Keep an explicit state machine when exact repeat behavior matters. |
| controller glyph prompts | input-device tracker + prompt atlas | Switch prompts using the last meaningful device event, not stick noise. |

## Audio and media

| XNA / MonoGame | Godot 4 candidate | Migration notes |
|---|---|---|
| `SoundEffect` / instance | `AudioStreamPlayer*` | Preserve polyphony, pitch, pan, loop, and stop behavior. |
| `Song`, `MediaPlayer` | music `AudioStreamPlayer` | Preserve loop points, transition, pause, and category volume. |
| XACT `AudioEngine`, `WaveBank`, `SoundBank` | audio buses + cue manifest + player pool | Keep cue names; encode categories, variations, weights, volumes, and loops. |
| `Video`, `VideoPlayer` | `VideoStreamPlayer` or frame/image fallback | Validate codec/platform support, aspect, alpha-key/compositing, audio, and skip flow. |

## Scene, UI, collision, camera, and persistence

| XNA / MonoGame pattern | Godot 4 candidate | Migration notes |
|---|---|---|
| screen/state enum | scenes + router | Preserve transition and overlay rules. |
| SpriteBatch HUD | `Control`/containers/CanvasLayer | Rebuild anchors at the original internal resolution, then test letterboxing. |
| custom AABB/grid collision | pure domain collision or physics bodies | Keep pure deterministic collision when source gameplay depends on grid/order semantics. |
| `BoundingBox` entities | `Area3D`, `CharacterBody3D`, shapes | Separate detection from damage/effects. |
| view/projection matrices | `Camera3D` | Match FOV orientation, near/far planes, aspect, and camera height. |
| `StorageDevice`, `TitleContainer`, file IO | `user://`, `FileAccess`, versioned JSON/Resource | Preserve save semantics and define migration/error handling. |
| Gamer Services, Guide, Marketplace, Avatar | local substitute, platform plugin, or explicit exclusion | Requires product decisions and often new UI/assets. |
| localization tables | CSV translations / `TranslationServer` | Preserve fallback rules and missing-string reporting. |

## C# conversion guidance

- Godot C#: change engine-facing inheritance and callbacks first; keep pure C# domain code where feasible.
- GDScript: port behavior in small functions and add typed signatures; do not transliterate C# syntax mechanically.
- In either target, replace event subscription ownership explicitly and disconnect/free transient listeners to avoid duplicate callbacks.
- Preserve integer division, overflow expectations, enum values, collection ordering, nullable behavior, and value-type copy semantics with tests.
