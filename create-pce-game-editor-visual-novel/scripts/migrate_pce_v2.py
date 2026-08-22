from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pce_vn_common import ValidationError, load_json, sha256_file, write_json


ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


def canonical_payload(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_id(prefix: str, value: Any, used: set[str]) -> str:
    digest = hashlib.sha256(canonical_payload(value)).hexdigest()
    for width in range(12, 65, 4):
        candidate = f"{prefix}.migrated.{digest[:width]}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    raise ValidationError(f"cannot assign unique content ID for {prefix}")


def preserve_or_map(prefix: str, raw: Any, context: Any, used: set[str]) -> str:
    value = str(raw or "")
    if ID_RE.fullmatch(value) and value not in used:
        used.add(value)
        return value
    return content_id(prefix, {"raw": value, "context": context}, used)


def semantic_cue(cue_id: str, command_type: str, command: dict[str, Any]) -> dict[str, Any]:
    action = str(command.get("action", ""))
    playback = "start" if action == "play" else "stop" if action == "stop" else "not-applicable"
    visual_types = {"background", "sprite", "spritemove", "effect", "spritetext", "cache"}
    return {
        "id": cue_id,
        "kind": "audio" if command_type == "audio" else "visual" if command_type in visual_types else "interaction",
        "emotion": "要レビュー",
        "narrativePurpose": f"移行元の{command_type or 'unknown'}演出が担う物語上の役割を確定する。",
        "characters": [],
        "visibleContent": "移行元の画面意図を再確認する。" if command_type in visual_types else "",
        "musicFunction": "移行元の音楽機能を再確認する。" if command_type == "audio" else "",
        "playbackIntent": playback,
    }


def migrate(document: Any, source_hash: str, project_id: str = "project.migrated") -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(document, dict) or document.get("version") != 2:
        raise ValidationError("input must be a PCE VN scene document with version 2")
    if not ID_RE.fullmatch(project_id):
        raise ValidationError("projectId must be a stable lowercase ASCII ID")
    scenes = document.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValidationError("PCE v2 document.scenes must be a non-empty array")
    used: set[str] = set()
    raw_to_scene: dict[str, str] = {}
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValidationError(f"scene {index} must be an object")
        raw = str(scene.get("id", ""))
        if raw in raw_to_scene:
            raise ValidationError(f"duplicate PCE scene ID: {raw}")
        raw_to_scene[raw] = preserve_or_map("scene", raw, {"scene": scene, "index": index}, used)

    speaker_map: dict[str, str] = {"": "narrator"}
    state_map: dict[str, str] = {}
    state_defs: dict[str, dict[str, Any]] = {}
    shared_scenes: list[dict[str, Any]] = []
    cues: list[dict[str, Any]] = []
    cue_map: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    outgoing: dict[str, set[str]] = {target: set() for target in raw_to_scene.values()}

    def speaker_id(raw: Any) -> str:
        name = str(raw or "")
        if name not in speaker_map:
            speaker_map[name] = preserve_or_map("character", name.lower(), {"displayName": name}, used)
        return speaker_map[name]

    def state_id(raw: Any) -> str:
        name = str(raw or "")
        if name not in state_map:
            state_map[name] = preserve_or_map("state", name.lower(), {"sourceVariable": name}, used)
            state_defs[state_map[name]] = {"id": state_map[name], "type": "integer", "initial": 0}
        return state_map[name]

    for scene_index, source_scene in enumerate(scenes):
        raw_scene_id = str(source_scene.get("id", ""))
        scene_id = raw_to_scene[raw_scene_id]
        commands = source_scene.get("commands", [])
        if not isinstance(commands, list):
            raise ValidationError(f"scene {raw_scene_id}.commands must be an array")
        entries: list[dict[str, Any]] = []
        terminal_emitted = False
        for command_index, command in enumerate(commands):
            if not isinstance(command, dict):
                raise ValidationError(f"scene {raw_scene_id} command {command_index} must be an object")
            command_type = str(command.get("type", ""))
            identity = {"scene": raw_scene_id, "command": command, "ordinalAmongDuplicates": sum(1 for prior in commands[:command_index] if prior == command)}
            if command_type == "message":
                entries.append({"id": content_id("line", identity, used), "type": "line", "speaker": speaker_id(command.get("speaker")), "text": str(command.get("text", ""))})
            elif command_type == "choice":
                options = command.get("choices", [])
                direct = command_index == len(commands) - 1 and isinstance(options, list) and len(options) >= 2 and all(isinstance(option, dict) and str(option.get("targetSceneId", "")) in raw_to_scene for option in options)
                if direct:
                    variable = str(command.get("variableName", "")).strip()
                    canonical_variable = state_id(variable) if variable else ""
                    converted = []
                    for option_index, option in enumerate(options):
                        target = raw_to_scene[str(option["targetSceneId"])]
                        outgoing[scene_id].add(target)
                        item = {"id": content_id("option", {**identity, "option": option, "optionIndex": option_index}, used), "text": str(option.get("label", option.get("text", ""))), "targetSceneId": target}
                        if canonical_variable:
                            item["setState"] = {canonical_variable: int(option.get("value", option_index))}
                        converted.append(item)
                    entries.append({"id": content_id("choice", identity, used), "type": "choice", "options": converted})
                    terminal_emitted = True
                else:
                    add_ambiguous_cue(entries, cues, cue_map, ambiguities, scene_id, identity, command, used, "PCE choice is not a terminal direct scene branch; reconstruct IF/SWITCH/GOTO semantics manually")
            elif command_type == "jump":
                target_raw = str(command.get("sceneId", ""))
                if command_index == len(commands) - 1 and target_raw in raw_to_scene:
                    target = raw_to_scene[target_raw]
                    entries.append({"id": content_id("jump", identity, used), "type": "jump", "targetSceneId": target})
                    outgoing[scene_id].add(target)
                    terminal_emitted = True
                else:
                    add_ambiguous_cue(entries, cues, cue_map, ambiguities, scene_id, identity, command, used, "PCE jump is unresolved or not terminal")
            elif command_type in {"variable", "var"}:
                variable = state_id(command.get("variableName", command.get("variable", "")))
                operation = str(command.get("operation", "set"))
                if operation in {"define", "set", "add", "sub", "subtract"}:
                    if operation == "define":
                        state_defs[variable]["initial"] = int(command.get("value", 0))
                    entries.append({"id": content_id("stateentry", identity, used), "type": "state", "variableId": variable, "operation": "set" if operation in {"define", "set"} else "add" if operation == "add" else "subtract", "value": int(command.get("value", 0)), "min": int(command.get("min", -32768)), "max": int(command.get("max", 32767))})
                else:
                    add_ambiguous_cue(entries, cues, cue_map, ambiguities, scene_id, identity, command, used, "PCE variable operation is outside canonical set/add/subtract/toggle")
            elif command_type == "comment":
                ambiguities.append({"id": content_id("ambiguity", identity, used), "sceneId": scene_id, "commandIndex": command_index, "commandType": command_type, "reason": "Editor-only comment retained for human review", "rawCommand": command})
            else:
                add_ambiguous_cue(entries, cues, cue_map, ambiguities, scene_id, identity, command, used, "Presentation/audio/control command has no machine-inferable narrative intent")
        shared_scene: dict[str, Any] = {"id": scene_id, "summary": "移行内容を要レビュー", "entries": entries}
        raw_next = str(source_scene.get("nextSceneId", ""))
        if terminal_emitted:
            if raw_next and raw_next in raw_to_scene and raw_to_scene[raw_next] not in outgoing[scene_id]:
                ambiguities.append({"id": content_id("ambiguity", {"scene": raw_scene_id, "next": raw_next}, used), "sceneId": scene_id, "reason": "nextSceneId conflicts with terminal choice/jump", "rawNextSceneId": raw_next})
        elif raw_next in raw_to_scene:
            shared_scene["nextSceneId"] = raw_to_scene[raw_next]
            outgoing[scene_id].add(raw_to_scene[raw_next])
        elif raw_next:
            ambiguities.append({"id": content_id("ambiguity", {"scene": raw_scene_id, "next": raw_next}, used), "sceneId": scene_id, "reason": "nextSceneId is unresolved", "rawNextSceneId": raw_next})
        shared_scenes.append(shared_scene)

    terminal = [scene_id for scene_id in raw_to_scene.values() if not outgoing[scene_id]]
    if not terminal:
        terminal = [shared_scenes[-1]["id"]]
        ambiguities.append({"id": content_id("ambiguity", {"endingPlaceholder": terminal[0]}, used), "sceneId": terminal[0], "reason": "No terminal scene could be inferred; review ending flow"})
    endings = [{"id": content_id("ending", {"sceneId": scene_id}, used), "title": "移行エンディング要レビュー", "sceneId": scene_id} for scene_id in terminal]
    start_raw = str(document.get("startScene", str(scenes[0].get("id", ""))))
    start = raw_to_scene.get(start_raw, shared_scenes[0]["id"])
    if start_raw not in raw_to_scene:
        ambiguities.append({"id": content_id("ambiguity", {"startScene": start_raw}, used), "reason": "startScene is unresolved", "rawStartScene": start_raw})
    shared = {"formatVersion": 2, "projectId": project_id, "revision": 1, "status": "REVIEW_REQUIRED", "startSceneId": start, "stateVariables": list(state_defs.values()), "cues": cues, "endings": endings, "scenes": shared_scenes}
    mapping = {"formatVersion": 1, "sourceFormat": "pce-vn-scenes-v2", "sourceSha256": source_hash, "pceSettings": document.get("settings", {}), "sceneIds": [{"sourceSceneId": raw, "sharedSceneId": mapped} for raw, mapped in raw_to_scene.items()], "stateIds": [{"sourceVariableId": raw, "sharedStateId": mapped} for raw, mapped in state_map.items()], "speakerIds": [{"sourceSpeaker": raw, "sharedCharacterId": mapped} for raw, mapped in speaker_map.items()], "cues": cue_map}
    suggested_characters = [{"id": mapped, "displayName": raw, "ageCategory": "要レビュー", "role": "要レビュー", "desire": "要レビュー", "obstacle": "要レビュー"} for raw, mapped in speaker_map.items() if raw]
    report = {"formatVersion": 1, "status": "REVIEW_REQUIRED", "sourceSha256": source_hash, "ambiguityCount": len(ambiguities), "suggestedCharacters": suggested_characters, "ambiguities": ambiguities, "instruction": "Merge suggested characters/state into the full pack, resolve every ambiguity, rerun shared validation, and obtain human approval."}
    return shared, mapping, report


def add_ambiguous_cue(entries: list[dict[str, Any]], cues: list[dict[str, Any]], cue_map: list[dict[str, Any]], ambiguities: list[dict[str, Any]], scene_id: str, identity: Any, command: dict[str, Any], used: set[str], reason: str) -> None:
    cue_id = content_id("cue", identity, used)
    use_id = content_id("cueentry", {"cueId": cue_id, "identity": identity}, used)
    entries.append({"id": use_id, "type": "cue", "cueId": cue_id})
    cues.append(semantic_cue(cue_id, str(command.get("type", "unknown")), command))
    cue_map.append({"cueId": cue_id, "commands": [command]})
    ambiguities.append({"id": content_id("ambiguity", {"cueId": cue_id, "reason": reason}, used), "sceneId": scene_id, "sourceEntryId": use_id, "cueId": cue_id, "commandType": str(command.get("type", "")), "reason": reason, "rawCommand": command})


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate PCE VN v2 scenes into a canonical review-required shared-script skeleton.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--project-id", default="project.migrated")
    parser.add_argument("--script-out", type=Path, required=True)
    parser.add_argument("--cue-map-out", type=Path, required=True)
    parser.add_argument("--ambiguities-out", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        shared, cue_map, report = migrate(load_json(args.input), sha256_file(args.input), args.project_id)
        for path in (args.script_out, args.cue_map_out, args.ambiguities_out):
            if path.exists() and not args.force:
                raise ValidationError(f"Refusing to overwrite existing file: {path}; pass --force explicitly")
        write_json(args.script_out, shared, args.force); write_json(args.cue_map_out, cue_map, args.force); write_json(args.ambiguities_out, report, args.force)
        print(f"REVIEW_REQUIRED: {len(shared['scenes'])} scenes, {report['ambiguityCount']} ambiguities")
    except (ValidationError, ValueError, TypeError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
