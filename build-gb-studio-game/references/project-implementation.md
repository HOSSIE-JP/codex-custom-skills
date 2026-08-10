# Project implementation

## Source of truth

Determine whether the project is editor-authored, generator-authored, or mixed.

- For generator-authored resources, make the generator deterministic and treat it as authoritative.
- Fix the authoritative generator before regenerating derived `.gbsres` files. A direct resource patch is only a diagnostic, never the final fix.
- Use stable IDs derived from semantic keys so regeneration does not rewrite every reference.
- Preserve hand-authored resources and unrelated changes.
- Derive resource fields from a project or template created by the same GB Studio version. Do not invent schema fields from memory.
- Save a scoped backup before replacing a resource tree.
- When the normal editor may contain unsaved work, generate and validate in an isolated copy, close the editor, recheck its processes, and reflect only the verified resource subset.
- After a targeted regeneration, compare normalized JSON with intended fields removed. Fail if IDs, animation structure, palettes, source slices, or unrelated metadata changed.

## Scene and event graph

Represent the requested flow as an explicit directed graph before generating scenes. Give every terminal or retry branch a known destination.

Validate the graph after generation:

- every scene ID is unique;
- every EVENT_SWITCH_SCENE target exists;
- every actor reference belongs to the current scene;
- every event ID is present and unique;
- every referenced variable and asset exists;
- every conditional branch has a safe fallback;
- no required scene is unreachable.

When duplicating nested conditional structures, create fresh event objects and fresh IDs for each branch. Reusing the same fallback event object can produce duplicate editor IDs.

## Interactive scenes

For menus, selection screens, and battles:

1. Deactivate the player actor when the scene is UI-driven.
2. Initialize cursor and state variables.
3. Draw or show the initial visual state.
4. Install left, right, accept, and cancel callbacks.
5. Clamp or wrap the cursor intentionally.
6. Remove all scene-local callbacks before changing scenes.
7. Reinstall callbacks on the destination scene.

Do not use a blocking event loop to poll input. It can prevent GB Studio input scripts from running and make a visually correct screen unresponsive.

For each input callback, verify that the callback contains events and that the input name matches the target GB Studio version. Test the physical direction and the Web keyboard mapping.

## State machines and rules

Keep state explicit. Common variables include selection, cursor, player life, opponent life, round, player action, opponent action, outcome, progression stage, clear flags, and scratch state.

Set random or opponent decisions before exposing player input when the rules require simultaneous choice. Validate the complete rule table with fixed values; for rock-paper-scissors, test all nine pairs.

Apply bounds at every mutation. A draw must not alter lives. A loss must not underflow player life. A win must not skip or repeat a progression stage. Final branches must occur exactly once.

Use a dedicated retry state for short loops such as a draw. Reset it on normal entry so it cannot leak across character selection or reload.

## Save data

Use one documented save slot and an explicit list of persisted variables.

- On boot, check whether saved data exists before peeking values.
- Initialize fresh values when no save exists.
- Save after an observable milestone, not midway through a transition.
- Reload the emulator and verify the values and destination scene.
- Run clean-state tests in an isolated profile or clear storage deliberately.

## Generator validation

Make generation fail early when invariants are broken. At minimum check:

- expected scene and resource counts;
- ID uniqueness;
- valid scene, actor, variable, sprite, background, and music references;
- required input callbacks and their buttons;
- absence of blocking loops in interactive scenes;
- state and life bounds;
- metasprite frame counts and coordinate invariants.

Keep generator validation separate from runtime playthrough validation. Both are required.

For imports from another engine, write a machine-readable manifest that records source hashes, normalized command counts, consumed commands, generated resources, and external gates. Unknown commands and count mismatches must fail instead of disappearing from the output.
