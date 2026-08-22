from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pce_vn_common import ValidationError, load_json, load_shared_pack, path_record, shared_modules, write_json


def validate_consumption(value: Any, aggregate: str) -> None:
    if not isinstance(value, dict) or value.get("ok") is not True:
        raise ValidationError("consumption report must have ok=true")
    expected, consumed = value.get("expected", {}), value.get("consumed", {})
    if expected.get("entries") != consumed.get("entries") or expected.get("entryTypes") != consumed.get("entryTypes") or expected.get("cueUses") != consumed.get("cueUses"):
        raise ValidationError("consumption counts do not match")
    if value.get("unconsumedEntryIds"):
        raise ValidationError("consumption report contains unconsumed entry IDs")
    if value.get("sharedSourceAggregateSha256") != aggregate:
        raise ValidationError("consumption report aggregate SHA is stale")


def validate_asset_map(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or value.get("formatVersion") != 1 or not isinstance(value.get("assets"), list):
        raise ValidationError("asset map must be a formatVersion 1 object with assets[]")
    seen: set[str] = set()
    for index, asset in enumerate(value["assets"]):
        if not isinstance(asset, dict):
            raise ValidationError(f"asset map entry {index} must be an object")
        source_id = asset.get("sharedAssetId", asset.get("sharedCueId"))
        if not isinstance(source_id, str) or not source_id or source_id in seen:
            raise ValidationError(f"asset map entry {index} needs a unique sharedAssetId or sharedCueId")
        seen.add(source_id)
        omission = asset.get("omission")
        if not asset.get("pceAssetId") and not (isinstance(omission, dict) and str(omission.get("reason", "")).strip()):
            raise ValidationError(f"asset mapping {source_id} needs pceAssetId or an omission reason")
    return value["assets"]


def build_mappings(script: dict[str, Any], source_map: dict[str, Any], cue_map: dict[str, Any], consumption: dict[str, Any]) -> list[dict[str, Any]]:
    omissions = {item["sourceEntryId"]: item["reason"] for item in consumption.get("omittedCueUses", [])}
    mappings: list[dict[str, Any]] = []
    for item in source_map.get("entries", []):
        refs = [f"pce-scene:{item['pceSceneId']}:command:{index}" for index in item.get("commandIndexes", [])]
        reason = omissions.get(item["sourceEntryId"], "")
        if not refs:
            refs = [f"pce-scene:{item['pceSceneId']}:explicit-omission"]
        mappings.append({"sharedId": item["sourceEntryId"], "action": "substituted" if reason else "consumed", "targetRefs": refs, "reason": reason})
        for option in item.get("options", []):
            mappings.append({"sharedId": option["sourceOptionId"], "action": "consumed", "targetRefs": [f"pce-scene:{item['pceSceneId']}:command:{item['commandIndexes'][0]}:option:{option['pceOptionIndex']}"], "reason": ""})
    cue_records = cue_map.get("cues", []) if isinstance(cue_map, dict) else []
    for item in cue_records:
        reason = str((item.get("omission") or {}).get("reason", ""))
        mappings.append({"sharedId": item["cueId"], "action": "substituted" if reason else "consumed", "targetRefs": [f"pce-cue-map:{item['cueId']}"], "reason": reason})
    scene_ids = {item["sourceSceneId"]: item["pceSceneId"] for item in source_map.get("sceneIds", [])}
    for ending in script.get("endings", []):
        pce_scene = scene_ids.get(ending["sceneId"])
        if not pce_scene:
            raise ValidationError(f"ending {ending['id']} has no PCE scene mapping")
        mappings.append({"sharedId": ending["id"], "action": "consumed", "targetRefs": [f"pce-scene:{pce_scene}:ending"], "reason": ""})
    return sorted(mappings, key=lambda item: item["sharedId"])


def build_manifest(
    pack: Path,
    validation_path: Path,
    scene_path: Path,
    source_map_path: Path,
    cue_map_path: Path,
    asset_map_path: Path,
    consumption_path: Path,
    generated_paths: list[Path],
    target: str,
    root: Path | None,
    verification_path: Path | None,
) -> dict[str, Any]:
    data, _, aggregate, paths = load_shared_pack(pack, require_approved=True, validation_report=validation_path)
    script = data["script.json"]
    pce_scenes = load_json(scene_path)
    if not isinstance(pce_scenes, dict) or pce_scenes.get("version") != 2:
        raise ValidationError("PCE scene output must have version 2")
    source_map = load_json(source_map_path)
    cue_map = load_json(cue_map_path)
    assets = validate_asset_map(load_json(asset_map_path))
    consumption = load_json(consumption_path)
    validate_consumption(consumption, aggregate)
    if source_map.get("sharedSourceAggregateSha256") != aggregate:
        raise ValidationError("source map aggregate SHA is stale")
    mappings = build_mappings(script, source_map, cue_map, consumption)
    base_manifest = {"formatVersion": 1, "target": f"pce-game-editor:{'cd-rom2' if target == 'cd' else 'hucard'}", "sharedSourceAggregateSha256": aggregate, "mappings": mappings}
    _, _, integration_validator = shared_modules()
    integration_report = integration_validator.validate_manifest(script, base_manifest, aggregate)
    if integration_report.get("status") != "pass":
        details = "; ".join(item.get("detail", "integration error") for item in integration_report.get("issues", []))
        raise ValidationError("shared integration manifest validation failed: " + details)
    verification: dict[str, Any] = {"cdPreflight": "not-run", "focusedTests": "not-run", "fullTests": "not-run", "build": "not-run", "mainPath": "not-run", "endingPaths": [], "physicalHardware": "external-gate"}
    if verification_path:
        supplied = load_json(verification_path)
        if not isinstance(supplied, dict):
            raise ValidationError("verification JSON must be an object")
        verification.update(supplied)
    inputs = [path_record(path, root) for path in [*paths.values(), validation_path, source_map_path, cue_map_path, asset_map_path, consumption_path]]
    generated = [path_record(path, root) for path in generated_paths]
    return {
        **base_manifest,
        "generator": "create-pce-game-editor-visual-novel",
        "targetMedia": "cd-rom2" if target == "cd" else "hucard",
        "sharedPack": {"revision": script["revision"], "status": script["status"], "sourceAggregateSha256": aggregate, "sourceFiles": {name: path_record(path, root) for name, path in sorted(paths.items())}},
        "sharedIntegrationValidation": integration_report,
        "pceScenes": path_record(scene_path, root),
        "inputs": sorted(inputs, key=lambda item: item["path"]),
        "generated": sorted(generated, key=lambda item: item["path"]),
        "assets": assets,
        "consumption": consumption,
        "verification": verification,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate a hash-linked PCE VN integration manifest.")
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--shared-validation", type=Path, required=True)
    parser.add_argument("--pce-scenes", type=Path, required=True)
    parser.add_argument("--source-map", type=Path, required=True)
    parser.add_argument("--cue-map", type=Path, required=True)
    parser.add_argument("--asset-map", type=Path, required=True)
    parser.add_argument("--consumption", type=Path, required=True)
    parser.add_argument("--generated", type=Path, action="append", default=[])
    parser.add_argument("--target", choices=("cd", "hucard"), required=True)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--verification", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build_manifest(args.pack, args.shared_validation, args.pce_scenes, args.source_map, args.cue_map, args.asset_map, args.consumption, args.generated, args.target, args.root, args.verification)
        write_json(args.out, manifest, args.force)
        print(f"OK: {manifest['targetMedia']} manifest, aggregate={manifest['sharedSourceAggregateSha256']}, mappings={len(manifest['mappings'])}")
    except ValidationError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
