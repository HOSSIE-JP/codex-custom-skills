"""Apply a PCE-layer-only menu shell (title/scenario-select carousel and
"return to title" ending loopback) on top of an already-emitted PCE scene
document.

Title screens, scenario-select carousels, and "return to title" navigation
are PCE menu plumbing, not story content, so they must never be expressed in
the shared, engine-neutral `script.json` (its endings must stay terminal —
see `write-visual-novel-scenario`'s `validate_vn_core.py` `ending-flow`
rule). This script is the sanctioned place to add that plumbing: it runs
strictly after `emit_pce_scenes.py`, against its output, and never touches
any shared-pack file.

Each selector scene is: one background + two spritetext overlays + three
inputcheck commands (confirm falls through to a jump into the scenario's
first scene; left/right jump to a same-scene label that jumps to the
neighboring selector). See references/menu-shell-and-title-screen.md.

Usage:
  python apply_pce_menu_shell.py --scenes <pce-vn-scenes.json> \
      --config <menu-shell-config.json> --out <pce-vn-scenes.json> \
      [--assets <pce-assets.json> --assets-out <pce-assets.json>] [--force]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pce_vn_common import ValidationError, load_json, write_json


DEFAULT_WAIT_FRAMES = 240
DEFAULT_FADE_FRAMES = 90
DEFAULT_ARROW_LABEL = "← シナリオ選択 →"
# SpriteText draws one glyph per VN_GLYPH_W (12px) pitch against a 256px-wide
# screen (see vn_engine_config.h / vn_port_sprite.c draw_spritetext_slots_impl).
# Centering the title line is just (screen width - text pixel width) / 2.
SPRITETEXT_GLYPH_PX = 12
SCREEN_WIDTH_PX = 256


def centered_spritetext_x(text: str) -> int:
    return max(0, (SCREEN_WIDTH_PX - SPRITETEXT_GLYPH_PX * len(text)) // 2)


def _scenario_field(scenario: dict[str, Any], field: str) -> Any:
    if field not in scenario:
        raise ValidationError(f"scenario config missing required field: {field!r} in {scenario!r}")
    return scenario[field]


def build_selector_scene(scenario: dict[str, Any], prev_id: str, next_id: str) -> dict[str, Any]:
    selector_id = _scenario_field(scenario, "selectorId")
    slug = _scenario_field(scenario, "slug")
    display_name = _scenario_field(scenario, "displayName")
    title_bg_asset_id = _scenario_field(scenario, "titleBgAssetId")
    start_scene_id = _scenario_field(scenario, "startSceneId")
    arrow_label = scenario.get("arrowLabel", DEFAULT_ARROW_LABEL)
    stop_channel_on_entry = scenario.get("selectorAudioStopChannel", 0)
    return {
        "id": selector_id,
        "name": f"シナリオ選択/{slug}_{display_name}",
        "fullScreenBg": False,
        "commands": [
            # Defensive: stop any audio still playing from wherever the player
            # arrived from (an ending's own trailer already stops "bgm" on its
            # own channel, but a fresh, unconditional "all" stop here covers
            # every other path into the selector, e.g. a future scenario
            # jumping straight back without its own trailer).
            {"type": "audio", "kind": "psg", "action": "stop", "assetId": "", "channel": stop_channel_on_entry, "target": "all"},
            {"type": "background", "assetId": title_bg_asset_id, "transition": "fade", "fadeOutFrames": 30, "fadeInFrames": 30, "x": 2, "y": 1},
            {"type": "spritetext", "slot": 0, "text": arrow_label, "x": 70, "y": 150, "color": "#ffffff", "blinkFrames": 60, "visible": True},
            {"type": "spritetext", "slot": 1, "text": display_name, "x": centered_spritetext_x(display_name), "y": 172, "color": "#ffffff", "blinkFrames": 0, "visible": True},
            {"type": "inputcheck", "buttons": ["run", "i"], "mode": "async", "targetLabel": ""},
            {"type": "inputcheck", "buttons": ["right"], "mode": "async", "targetLabel": "NEXT_SCR"},
            {"type": "inputcheck", "buttons": ["left"], "mode": "sync", "targetLabel": "PREV_SCR"},
            {"type": "comment", "text": "シナリオ開始", "color": ""},
            {"type": "jump", "sceneId": start_scene_id},
            {"type": "comment", "text": "次のシナリオ", "color": ""},
            {"type": "label", "name": "NEXT_SCR"},
            {"type": "jump", "sceneId": next_id},
            {"type": "comment", "text": "前のシナリオ", "color": ""},
            {"type": "label", "name": "PREV_SCR"},
            {"type": "jump", "sceneId": prev_id},
        ],
        "nextSceneId": "",
    }


def ending_trailer(selector_id: str, stop_channel: int, wait_frames: int, fade_frames: int) -> list[dict[str, Any]]:
    return [
        {"type": "wait", "frames": wait_frames},
        {"type": "effect", "effect": "fadeOut", "frames": fade_frames, "intensity": 0, "color": "#000000"},
        {"type": "audio", "kind": "psg", "action": "stop", "assetId": "", "channel": stop_channel, "target": "bgm"},
        {"type": "jump", "sceneId": selector_id},
    ]


def apply_menu_shell(scenes_doc: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if config.get("formatVersion") != 1:
        raise ValidationError("menu-shell config must have formatVersion 1")
    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValidationError("menu-shell config.scenarios must be a non-empty array")

    if not isinstance(scenes_doc.get("scenes"), list):
        raise ValidationError("scenes document must have a scenes array")
    scenes = {scene["id"]: scene for scene in scenes_doc["scenes"] if isinstance(scene, dict) and "id" in scene}
    if len(scenes) != len(scenes_doc["scenes"]):
        raise ValidationError("scenes document contains a scene without a stable id")

    selector_ids: list[str] = []
    seen_selector_ids: set[str] = set()
    for scenario in scenarios:
        selector_id = _scenario_field(scenario, "selectorId")
        if selector_id in seen_selector_ids:
            raise ValidationError(f"duplicate selectorId in menu-shell config: {selector_id}")
        seen_selector_ids.add(selector_id)
        if selector_id in scenes:
            raise ValidationError(f"selector scene id collides with an existing scene id: {selector_id}")
        selector_ids.append(selector_id)

    for scenario in scenarios:
        start_scene_id = _scenario_field(scenario, "startSceneId")
        if start_scene_id not in scenes:
            raise ValidationError(f"scenario {scenario.get('selectorId')!r}: startSceneId not found in scenes document: {start_scene_id}")
        ending_scene_ids = scenario.get("endingSceneIds", [])
        if not isinstance(ending_scene_ids, list):
            raise ValidationError(f"scenario {scenario.get('selectorId')!r}: endingSceneIds must be an array")
        for ending_id in ending_scene_ids:
            if ending_id not in scenes:
                raise ValidationError(f"scenario {scenario.get('selectorId')!r}: endingSceneIds entry not found in scenes document: {ending_id}")

    for scenario in scenarios:
        wait_frames = int(scenario.get("endingWaitFrames", DEFAULT_WAIT_FRAMES))
        fade_frames = int(scenario.get("endingFadeFrames", DEFAULT_FADE_FRAMES))
        stop_channel = int(scenario.get("endingBgmStopChannel", 0))
        selector_id = scenario["selectorId"]
        for ending_id in scenario.get("endingSceneIds", []):
            scene = scenes[ending_id]
            if scene.get("nextSceneId"):
                raise ValidationError(f"ending scene {ending_id} already has a nextSceneId, refusing to double-append a menu-shell tail")
            terminal_types = {"choice", "jump"}
            commands = scene.get("commands") if isinstance(scene.get("commands"), list) else []
            if commands and commands[-1].get("type") in terminal_types:
                raise ValidationError(f"ending scene {ending_id} already ends in {commands[-1]['type']!r}, refusing to double-append a menu-shell tail")
            scene["commands"] = commands + ending_trailer(selector_id, stop_channel, wait_frames, fade_frames)

    selector_scenes = []
    for index, scenario in enumerate(scenarios):
        prev_id = selector_ids[index - 1] if index > 0 else selector_ids[-1]
        next_id = selector_ids[index + 1] if index + 1 < len(selector_ids) else selector_ids[0]
        selector_scenes.append(build_selector_scene(scenario, prev_id, next_id))

    scenes_doc = dict(scenes_doc)
    scenes_doc["scenes"] = selector_scenes + list(scenes_doc["scenes"])
    scenes_doc["startScene"] = selector_ids[0]
    return scenes_doc


def apply_asset_names(asset_doc: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Optional: rewrite asset `name` fields to a "<category>/<scenarioSlug>/<shortId>"
    breadcrumb, per each scenario's `assetNameRules`. Never touches `id`."""
    assets = asset_doc.get("assets")
    if not isinstance(assets, list):
        return asset_doc
    for scenario in config.get("scenarios", []):
        slug = scenario.get("slug", "")
        rules = scenario.get("assetNameRules", [])
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_id = str(asset.get("id", ""))
            asset_type = asset.get("type", "")
            for rule in rules:
                match_type = rule.get("assetType")
                id_prefix = rule.get("idPrefix", "")
                if match_type not in (None, asset_type):
                    continue
                if id_prefix and not asset_id.startswith(id_prefix):
                    continue
                short_id = asset_id[len(id_prefix):] if id_prefix else asset_id
                category = rule.get("category", asset_type)
                asset["name"] = f"{category}/{slug}/{short_id}"
                break
    return asset_doc


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply the PCE-only title/scenario-select menu shell to an emitted scene document.")
    parser.add_argument("--scenes", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--assets", type=Path, help="Optional assets/pce-assets.json to rewrite name fields on")
    parser.add_argument("--assets-out", type=Path, help="Output path for --assets; defaults to overwriting --assets in place")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        scenes_doc = load_json(args.scenes)
        config = load_json(args.config)
        result = apply_menu_shell(scenes_doc, config)
        write_json(args.out, result, args.force)
        selector_count = len(config.get("scenarios", []))
        print(f"OK: {len(result['scenes'])} scenes ({selector_count} selector scene(s)), startScene={result['startScene']}")
        if args.assets:
            asset_doc = load_json(args.assets)
            asset_result = apply_asset_names(asset_doc, config)
            out_path = args.assets_out or args.assets
            write_json(out_path, asset_result, True if out_path == args.assets else args.force)
            print(f"OK: asset names updated -> {out_path}")
    except ValidationError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
