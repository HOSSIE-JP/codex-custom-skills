# Menu shell and title screen

`scripts/apply_pce_menu_shell.py` builds a title-screen / scenario-select carousel and a "return to title" ending loopback directly on top of an already-emitted PCE scene document. The script and its tests (`tests/test_scripts.py`'s `MenuShellTests`) are the authoritative, runnable spec for the generated structure — this file explains the pattern and the reasoning behind it, not a transcript of any specific project's file. Do not point at another project's checkout to "confirm" this structure; run the script and its tests instead.

## Hard boundary: PCE-only, post-emission-only

This structure must live **only** in the final PCE-format scene document (`assets/pce-vn-scenes.json`), never in the shared engine-neutral `script.json`. `write-visual-novel-scenario`'s own validator (`validate_vn_core.py`, the `ending-flow` rule) requires every declared ending scene to have **no outgoing flow at all** — so "loop back to title" cannot be expressed as shared-pack content. Add it as a post-processing step applied to `emit_pce_scenes.py`'s output, after emission, never by editing the shared `script.json`.

## `name` vs `id`: breadcrumbs are editor-UI only

Scene/asset `id` values are never restructured with slashes or numeric prefixes — only `name` changes.

- A selectable route's PCE scene keeps a flat `id` (e.g. `scenario_a`, no slashes) — `apply_pce_menu_shell.py` never rewrites `id`.
- Its **`name`** field carries a slash-delimited breadcrumb for editor-UI grouping only, e.g. `"name": "シナリオ選択/01_シナリオA"`. Zero runtime effect — jumps, `startScene`, and `NEXT_SCR`/`PREV_SCR` labels all resolve by `id`, never by `name`, so an unrelated story scene elsewhere in the same document can use a completely different `name` convention (e.g. a migration-tool breadcrumb) without conflict.
- Same pattern in `pce-assets.json`: asset `id` stays flat (e.g. `bg_scenario_a_title`), `name` gets a breadcrumb (e.g. `"BG/シナリオA/title"`) via `apply_asset_names()`.

## Selector scene structure (carousel)

Each selectable route gets one PCE scene with `commands`:

1. one `background` (that route's title art);
2. two `spritetext` overlays — a fixed arrow label (e.g. `"← シナリオ選択 →"`) and the route's display name;
3. three `inputcheck` commands:
   - confirm: `{buttons:["run","i"], mode:"async", targetLabel:""}` — falls through to the very next command when not triggered, which is a `jump` straight into that route's first story scene;
   - right: `{mode:"async", targetLabel:"NEXT_SCR"}` — jumps to a same-scene `label` that then jumps to the neighboring selector scene's `id`;
   - left: `{mode:"sync", targetLabel:"PREV_SCR"}` — same pattern, opposite direction.

Forms a circular carousel: wraps last-to-first and back. With only one scenario registered, both `NEXT_SCR`/`PREV_SCR` targets point back at the selector's own `id` (self-loop) — the correct degenerate case, not a bug.

## Ending "return to title" tail

`ending_trailer()` in `apply_pce_menu_shell.py` appends this after a route's final message (values illustrative; `wait`/`fade` frame counts and the stop `channel` are configurable per scenario, see below):

```json
[
  { "type": "wait", "frames": 240 },
  { "type": "effect", "effect": "fadeOut", "frames": 90, "intensity": 0, "color": "#000000" },
  { "type": "audio", "kind": "psg", "action": "stop", "assetId": "", "channel": 0, "target": "bgm" },
  { "type": "jump", "sceneId": "scenario_a" }
]
```

## Applying it: `scripts/apply_pce_menu_shell.py`

A committed, reusable post-processing script. It reads the freshly emitted PCE scene document and:

1. appends the ending-loopback tail above to each configured ending scene;
2. prepends one generated selector scene per configured scenario;
3. sets `startScene` to the first selector's id;
4. rewrites `name` fields on both scenes and assets per the breadcrumb convention above.

Parameterized by a small config, one entry per selectable route — copy [assets/templates/menu-shell-config.json](../assets/templates/menu-shell-config.json):

```json
{
  "formatVersion": 1,
  "scenarios": [
    {
      "selectorId": "01_scenario_a",
      "slug": "scenario_a",
      "displayName": "シナリオA",
      "titleBgAssetId": "bg_scenario_a_title",
      "startSceneId": "scene_scenario_a_01",
      "endingSceneIds": ["scene_scenario_a_ending_true", "scene_scenario_a_ending_normal"]
    }
  ]
}
```

```powershell
python "<skill-dir>\scripts\apply_pce_menu_shell.py" --scenes "<pce-vn-scenes.json>" --config "<menu-shell-config.json>" --out "<pce-vn-scenes.json>" --force
```

Run the real CD preflight (see [cd-build-recipe.md](cd-build-recipe.md)) against the output before building — the menu shell is new scene content and must pass the same checks as emitted content.

## Title/selector stills

Whenever an image-prompt-generation document is produced for a scenario that will get a selector entry, it must include one title/scenario-select event-still prompt, referencing the same character/background anchor sheets as the rest of that scenario's stills for visual consistency. This is a standing rule, not a one-off — apply it every time, for every scenario. See [images-and-sprites.md](images-and-sprites.md).
