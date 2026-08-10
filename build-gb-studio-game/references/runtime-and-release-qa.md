# Runtime and release QA

## Use the real GB Studio version

Identify the project's GB Studio version and use that installation for saving and exporting. When schema behavior is unclear, inspect a minimal project or bundled sample produced by the same version.

Before disk regeneration:

- save and close the user's normal editor;
- recheck every GB Studio process after the user says it is closed;
- confirm the project document is clean;
- use a backup for broad generated changes.

After regeneration, reopen a disposable project copy, inspect fragile resources in the editor, and use the editor's own save path once to discover normalization. GB Studio may recompute fields such as `numTiles` merely after selecting a sprite. Compare before and after, then apply only intentional changes to the real project.

Quote project paths containing spaces or non-ASCII characters when launching a portable editor. An unquoted path can create a process and debugging port without opening the intended renderer.

## Official build gates

Create ROM and Web exports through GB Studio. Capture:

- version;
- target and color mode;
- warnings and errors;
- ROM byte size and SHA-256;
- Web-embedded ROM SHA-256;
- output paths and timestamps.

Fail when the build output is older than an input that should affect it. Do not validate a stale ROM accidentally.

Treat raw assets, editor resources, editor Canvas rendering, and runtime output as different surfaces. A fix can improve the editor while moving the compiled sprite, or preserve runtime output while changing editor-only metadata. For layout-only changes, compare the affected runtime pixel region against a known-good build when behavior is expected to remain byte-identical.

## Isolated emulator testing

Use a fresh GB Studio user-data profile for repeatable tests. A dedicated remote-debugging port can expose the main editor and built-in emulator as separate pages. Discover save and build actions from the installed editor bundle or live application; numeric Webpack module IDs are version-specific and must not become a permanent API.

Before the first input, assert:

- the expected boot scene is active;
- the emulator is not paused;
- relevant variables contain fresh values;
- local storage or save flags are empty when testing a clean boot.

Drive input with keyDown and keyUp events and a realistic hold. Wait for a scene, cursor, life, or flag transition rather than using fixed sleeps alone.

If an input is occasionally missed, retry only when the current scene is still the expected source scene. Abort on any unexpected scene. This distinguishes harness timing from a game flow defect.

## Minimum playthrough matrix

Test the paths relevant to the game. A menu-driven game should normally cover:

- logo to title to selection;
- left and right movement, wrapping, and boundary behavior;
- cancel back to title;
- acceptance of every selectable option;
- every action icon or command;
- draw or retry;
- win and loss;
- life reaching zero and game over;
- every progression or costume stage;
- every character and difficulty;
- individual victories;
- final ending or all-clear;
- save and reload persistence.

Take screenshots at state boundaries, not merely at launch.

If the user explicitly owns a full manual playthrough, run focused automated regressions for the changed behavior and report the unexecuted matrix as an external acceptance gate. Do not silently convert that delegation into a completion claim.

## Deterministic acceleration

Use debugger variable overrides only to accelerate repetition after normal input has been proven. Record each override and why it is behavior-preserving.

For example, forcing an opponent action can reach win, draw, and loss branches deterministically. Still move the real cursor and press the real acceptance key so input wiring remains under test.

## Evidence format

Write a machine-readable evidence file containing:

- status;
- GB Studio version;
- harness and input method;
- isolation method;
- tested ROM path, size, and hash;
- scenario booleans;
- deterministic overrides;
- screenshots;
- timestamped state trace.

Make the final validator require this evidence and require every mandatory scenario to be true.

## Final adversarial review

Try to disprove completion:

- Can stale editor state overwrite the fix?
- Can a required callback be empty or shadowed?
- Can cursor state escape its range?
- Can a save from a previous run mask the boot path?
- Can a generated asset pass dimensions but fail visual composition?
- Can an editor-visible fix alter compiler-relative sprite coordinates?
- Can selecting and saving one resource normalize unrelated metadata?
- Can ROM and Web contain different builds?
- Can the harness jump directly to states without proving input?
- Can the game pass in emulator but remain unverified on physical hardware?

Report physical flash-cart, controller, audio-device, or display checks as external gates unless they were actually performed.
