# Trigger-scope tests

Use these examples to check Skill metadata and scope. “Invoke” means this Skill should be selected automatically or explicitly. “Do not invoke” means another general coding/Godot skill is more appropriate.

## Should invoke

1. “Analyze this Microsoft.Xna.Framework 3.1 game and create a Godot 4 migration plan.”
2. “Port our MonoGame SpriteBatch screens and ContentManager assets to Godot.”
3. “Convert these GameComponent and DrawableGameComponent classes into a Godot scene architecture.”
4. “Inventory every Content.Load call, XACT cue, SpriteFont, and custom content processor before migration.”
5. “Migrate an XNA dungeon game to Godot without changing its fixed-step behavior.”
6. “Why do models face backward and particles spawn in the wrong place after our XNA-to-Godot port?”
7. “Create a vertical-slice port from an old Xbox XNA project, with local fallbacks for Gamer Services.”
8. “Validate that this Godot project contains all assets referenced by the original XNA Content Pipeline.”
9. “XNAゲームをGodotへ移植し、画面・入力・音声・セーブを段階的に再現して。”
10. “Use `$xna-to-godot-migration` to scan this source tree and report blockers before writing code.”

## Should not invoke

1. “Build a new Godot platformer from scratch.”
2. “Explain how `_physics_process` differs from `_process` in Godot.”
3. “Refactor this ordinary .NET console application.”
4. “Upgrade a MonoGame project from .NET 6 to .NET 8 but keep MonoGame.”
5. “Create a Blender model and import it into Godot.”
6. “Fix a typo in this existing Godot menu.”
7. “Convert Unity MonoBehaviour code to Godot.”
8. “Package an already completed Godot game for Steam.”

## Boundary cases

- “Replace XNA with MonoGame” should not invoke unless Godot migration/porting is also requested.
- “Import an XNB into Godot” should invoke when it is part of reconstructing an XNA/MonoGame game; a one-off file conversion may only need an asset tool.
- “Fix pause in a Godot port” should invoke only when source XNA semantics or migration regressions must be compared; an unrelated Godot pause bug should not.
- “Review a Godot C# game” should not invoke unless the review concerns XNA/MonoGame compatibility or migration fidelity.

## Generalization checks

The Skill passes scope review when it:

- asks which project is authoritative instead of assuming a known directory name;
- detects both XNA and MonoGame project/content formats;
- supports 2D and 3D, C# and GDScript targets;
- does not assume a dungeon, fixed resolution, XACT, Xbox, Web, or Japanese assets;
- reports absent subsystems as not present rather than forcing every mapping;
- preserves source behavior and surfaces ambiguous decisions instead of applying project-specific balance fixes.
