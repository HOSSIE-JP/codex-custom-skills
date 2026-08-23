from __future__ import annotations

import argparse
import copy
from collections import Counter
from pathlib import Path
from typing import Any

from pce_vn_common import ValidationError, load_json, load_shared_pack, pce_id, write_json


ALLOWED_CUE_COMMANDS = {"background", "sprite", "spritemove", "audio", "effect", "wait", "spritetext", "cache"}


def cue_mapping(document: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(document, dict) or document.get("formatVersion") != 1:
        raise ValidationError("cue map must be a formatVersion 1 object")
    entries = document.get("cues")
    if not isinstance(entries, list):
        raise ValidationError("cue map.cues must be an array")
    result: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("cueId"), str):
            raise ValidationError(f"cue map entry {index} requires cueId")
        cue_id = entry["cueId"]
        if cue_id in result:
            raise ValidationError(f"duplicate cue mapping: {cue_id}")
        commands, omission = entry.get("commands", []), entry.get("omission")
        if not isinstance(commands, list):
            raise ValidationError(f"cue mapping {cue_id}.commands must be an array")
        if not commands and not (isinstance(omission, dict) and str(omission.get("reason", "")).strip()):
            raise ValidationError(f"cue mapping {cue_id} needs commands or an omission reason")
        if commands and omission is not None:
            raise ValidationError(f"cue mapping {cue_id} cannot contain both commands and omission")
        for command_index, command in enumerate(commands):
            validate_cue_command(cue_id, command_index, command)
        result[cue_id] = entry
    return result


def validate_cue_command(cue_id: str, index: int, command: Any) -> None:
    if not isinstance(command, dict):
        raise ValidationError(f"cue {cue_id} command {index} must be an object")
    command_type = command.get("type")
    if command_type not in ALLOWED_CUE_COMMANDS:
        raise ValidationError(f"cue {cue_id} uses unknown or unsupported PCE command: {command_type}")
    if command_type == "audio":
        if command.get("kind") != "psg":
            raise ValidationError(f"cue {cue_id} audio must use kind=psg; voice/ADPCM/CD-DA authoring is out of scope")
        if command.get("action", "play") not in {"play", "stop"}:
            raise ValidationError(f"cue {cue_id} PSG action must be play or stop")
        if command.get("action", "play") == "play" and not command.get("assetId"):
            raise ValidationError(f"cue {cue_id} PSG play command requires assetId")
    if command_type == "background" and not command.get("assetId"):
        raise ValidationError(f"cue {cue_id} background requires assetId")
    if command_type == "sprite" and command.get("visible", True) and not command.get("assetId"):
        raise ValidationError(f"cue {cue_id} visible sprite requires assetId")
    if command_type == "cache" and command.get("scope") == "adpcm":
        raise ValidationError(f"cue {cue_id} cannot author ADPCM cache commands")


def scalar_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{label} must be an integer for the current PCE variable command")
    return value


def scene_breadcrumb_name(project_slug: str, pce_scene_id: str) -> str:
    """"<projectSlug>/<shortId>" editor-UI breadcrumb, matching the same id-stays-flat/
    name-carries-breadcrumb convention as apply_pce_menu_shell.py's selector scenes and
    apply_asset_names(). A leading "scene_" is stripped from the id for readability
    (e.g. pce id "scene_prologue" -> name "<slug>/prologue"); never touches `id`."""
    short_id = pce_scene_id[len("scene_"):] if pce_scene_id.startswith("scene_") else pce_scene_id
    return f"{project_slug}/{short_id}"


def emit(
    script: dict[str, Any],
    cue_map: dict[str, dict[str, Any]],
    speaker_names: dict[str, str] | None = None,
    aggregate: str = "",
    project_slug: str = "",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if script.get("formatVersion") != 2 or script.get("status") != "APPROVED" or not isinstance(script.get("revision"), int):
        raise ValidationError("emitter requires an approved canonical formatVersion 2 script")
    scenes = script.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValidationError("script.scenes must be non-empty")
    scene_id_map = {scene["id"]: pce_id(scene["id"], "scene") for scene in scenes}
    state_id_map = {item["id"]: pce_id(item["id"], "state") for item in script.get("stateVariables", [])}
    if len(set(scene_id_map.values())) != len(scene_id_map) or len(set(state_id_map.values())) != len(state_id_map):
        raise ValidationError("canonical IDs collide after deterministic PCE normalization")
    speaker_names = speaker_names or {}
    pce_scenes: list[dict[str, Any]] = []
    source_entries: list[dict[str, Any]] = []
    cue_uses: list[dict[str, Any]] = []
    omitted_cues: list[dict[str, str]] = []
    consumed: Counter[str] = Counter()

    for scene in scenes:
        commands: list[dict[str, Any]] = []
        pce_scene_id = scene_id_map[scene["id"]]
        for entry in scene.get("entries", []):
            entry_id, entry_type = entry["id"], entry["type"]
            command_start = len(commands)
            extra: dict[str, Any] = {}
            if entry.get("when") is not None:
                raise ValidationError(f"entry {entry_id} has a condition; the deterministic PCE subset requires an explicit manual mapping")
            if entry_type == "line":
                speaker_id = str(entry.get("speaker", ""))
                commands.append({"type": "message", "speaker": speaker_names.get(speaker_id, speaker_id), "text": entry["text"], "textColor": "", "voiceAssetId": "", "mouthSlot": None})
            elif entry_type == "choice":
                options = entry.get("options", [])
                if any(option.get("when") is not None for option in options):
                    raise ValidationError(f"choice {entry_id} has conditional options; the deterministic PCE subset rejects when")
                assignments = [option.get("setState") or {} for option in options]
                if any(not isinstance(item, dict) for item in assignments):
                    raise ValidationError(f"choice {entry_id} setState values must be objects")
                assigned = [item for item in assignments if item]
                if assigned and len(assigned) != len(assignments):
                    raise ValidationError(f"choice {entry_id} must assign state on every option or none")
                if any(len(item) != 1 for item in assigned):
                    raise ValidationError(f"choice {entry_id} options must assign exactly one state variable")
                variables = {next(iter(item)) for item in assigned}
                if len(variables) > 1:
                    raise ValidationError(f"choice {entry_id} options must assign one common state variable")
                variable = next(iter(variables), "")
                if variable and variable not in state_id_map:
                    raise ValidationError(f"choice {entry_id} writes unknown state variable: {variable}")
                choices, option_map = [], []
                for option_index, option in enumerate(options):
                    target = option["targetSceneId"]
                    if target not in scene_id_map:
                        raise ValidationError(f"choice option {option['id']} targets unknown scene: {target}")
                    value = scalar_int(assignments[option_index][variable], f"choice option {option['id']} setState") if variable else option_index
                    choices.append({"label": str(option["text"]), "value": value, "targetSceneId": scene_id_map[target]})
                    option_map.append({"sourceOptionId": option["id"], "pceOptionIndex": option_index})
                commands.append({"type": "choice", "variableName": state_id_map.get(variable, ""), "choices": choices, "defaultIndex": 0})
                extra["options"] = option_map
            elif entry_type == "jump":
                target = entry["targetSceneId"]
                if target not in scene_id_map:
                    raise ValidationError(f"jump {entry_id} targets unknown scene: {target}")
                commands.append({"type": "jump", "sceneId": scene_id_map[target]})
            elif entry_type == "state":
                variable = entry["variableId"]
                if variable not in state_id_map:
                    raise ValidationError(f"state {entry_id} writes unknown variable: {variable}")
                operation = entry["operation"]
                pce_operation = {"set": "set", "add": "add", "subtract": "sub"}.get(operation)
                if pce_operation is None:
                    raise ValidationError(f"state {entry_id} operation {operation} needs a manual PCE mapping")
                commands.append({"type": "variable", "variableName": state_id_map[variable], "operation": pce_operation, "value": scalar_int(entry.get("value"), f"state {entry_id}.value"), "min": scalar_int(entry.get("min", -32768), f"state {entry_id}.min"), "max": scalar_int(entry.get("max", 32767), f"state {entry_id}.max")})
            elif entry_type == "cue":
                cue_id = entry["cueId"]
                mapping = cue_map.get(cue_id)
                if mapping is None:
                    raise ValidationError(f"cue entry {entry_id} has no PCE mapping: {cue_id}")
                commands.extend(copy.deepcopy(mapping.get("commands", [])))
                if not mapping.get("commands"):
                    omitted_cues.append({"sourceEntryId": entry_id, "cueId": cue_id, "reason": mapping["omission"]["reason"]})
                cue_uses.append({"sourceEntryId": entry_id, "cueId": cue_id, "pceSceneId": pce_scene_id, "commandIndexes": list(range(command_start, len(commands)))})
            else:
                raise ValidationError(f"entry {entry_id} has unsupported type: {entry_type}")
            consumed[entry_type] += 1
            source_entries.append({"sourceEntryId": entry_id, "sourceType": entry_type, "sourceSceneId": scene["id"], "pceSceneId": pce_scene_id, "commandIndexes": list(range(command_start, len(commands))), **extra})
        next_scene = scene.get("nextSceneId", "")
        pce_scene: dict[str, Any] = {"id": pce_scene_id, "fullScreenBg": False, "commands": commands, "nextSceneId": scene_id_map.get(next_scene, "")}
        if project_slug:
            pce_scene["name"] = scene_breadcrumb_name(project_slug, pce_scene_id)
        pce_scenes.append(pce_scene)

    expected = Counter(entry["type"] for scene in scenes for entry in scene.get("entries", []))
    if consumed != expected:
        raise ValidationError(f"consumption mismatch: expected {dict(expected)}, consumed {dict(consumed)}")
    pce_document = {"version": 2, "settings": {"messageSpeedFrames": 10, "messageAdvanceMode": "button", "messageAutoWaitFrames": 60}, "startScene": scene_id_map[script["startSceneId"]], "scenes": pce_scenes}
    source_map = {"formatVersion": 1, "sharedRevision": script["revision"], "sharedSourceAggregateSha256": aggregate, "sceneIds": [{"sourceSceneId": source, "pceSceneId": target} for source, target in scene_id_map.items()], "stateIds": [{"sourceStateId": source, "pceVariableName": target} for source, target in state_id_map.items()], "entries": source_entries, "cueUses": cue_uses}
    consumption = {"formatVersion": 1, "ok": True, "sharedRevision": script["revision"], "sharedSourceAggregateSha256": aggregate, "expected": {"entries": sum(expected.values()), "entryTypes": dict(sorted(expected.items())), "cueUses": len(cue_uses)}, "consumed": {"entries": len(source_entries), "entryTypes": dict(sorted(consumed.items())), "cueUses": len(cue_uses)}, "generatedCommands": sum(len(scene["commands"]) for scene in pce_scenes), "omittedCueUses": omitted_cues, "unconsumedEntryIds": []}
    return pce_document, source_map, consumption


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit PCE VN v2 scenes from a fully approved shared authoring pack.")
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--shared-validation", type=Path, required=True)
    parser.add_argument("--cue-map", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-map", type=Path, required=True)
    parser.add_argument("--consumption-out", type=Path, required=True)
    parser.add_argument("--project-slug", default="", help="When set, breadcrumbs each emitted scene's editor-UI name field as '<slug>/<shortId>' (id stays flat). Use the same slug passed to apply_pce_menu_shell.py so story scenes and the selector scene share one breadcrumb convention.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        data, _, aggregate, _ = load_shared_pack(args.pack, require_approved=True, validation_report=args.shared_validation)
        script = data["script.json"]
        speakers = {"narrator": ""}
        speakers.update({str(item["id"]): str(item.get("displayName", item["id"])) for item in data["character-bible.json"].get("characters", [])})
        pce_document, source_map, consumption = emit(script, cue_mapping(load_json(args.cue_map)), speakers, aggregate, args.project_slug)
        for path in (args.out, args.source_map, args.consumption_out):
            if path.exists() and not args.force:
                raise ValidationError(f"Refusing to overwrite existing file: {path}; pass --force explicitly")
        write_json(args.out, pce_document, args.force)
        write_json(args.source_map, source_map, args.force)
        write_json(args.consumption_out, consumption, args.force)
        print(f"OK: {len(pce_document['scenes'])} scenes, {consumption['generatedCommands']} commands, aggregate={aggregate}")
    except ValidationError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
