from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, Callable

from vn_common import ID_RE, ValidationError, all_shared_ids, contained, dump_json, load_json, source_hashes, source_paths


STATUSES = {"REVIEW_REQUIRED", "APPROVED"}
EXTERNAL_STATUSES = {"pending-user-decision", "awaiting-external-review", "proceeding-provisionally", "waived-by-user", "complete"}
ENTRY_TYPES = {"line", "choice", "jump", "state", "cue"}
STATE_TYPES = {"boolean", "integer", "string"}
PLAYBACK_INTENTS = {"start", "continue", "stop", "not-applicable"}


def matches_type(value: Any, state_type: str) -> bool:
    return (state_type == "boolean" and isinstance(value, bool)) or (state_type == "integer" and isinstance(value, int) and not isinstance(value, bool)) or (state_type == "string" and isinstance(value, str))


def forbidden_cue_fields(value: Any, location: str = "cue") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            forbidden = (
                ("asset" in normalized and "id" in normalized)
                or any(token in normalized for token in ("file", "path", "resolution", "dimension", "width", "height", "format", "engine", "command"))
            )
            if forbidden:
                found.append(f"{location}.{key}")
            found.extend(forbidden_cue_fields(child, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(forbidden_cue_fields(child, f"{location}[{index}]"))
    return found


def validate_pack(data: dict[str, dict[str, Any]], *, require_approved: bool = False) -> dict[str, Any]:
    brief, bible, design, script, rules = (data[name] for name in ("project-brief.json", "character-bible.json", "scenario-design.json", "script.json", "language-rules.json"))
    issues: list[dict[str, str]] = []

    def issue(severity: str, location: str, rule: str, detail: str) -> None:
        issues.append({"severity": severity, "location": location, "rule": rule, "detail": detail})

    for name, value in data.items():
        if value.get("formatVersion") != 2:
            issue("error", name, "format-version", "formatVersion must be 2")
    project_ids = {str(value.get("projectId", "")) for name, value in data.items() if name not in {"language-rules.json", "self-review.json"}}
    project_id = next(iter(project_ids), "")
    if len(project_ids) != 1 or not project_id or "replace-with" in project_id:
        issue("error", "authoring-pack", "project-id", f"projectId must be populated and identical: {sorted(project_ids)}")
    if brief.get("language") != "ja":
        issue("error", "project-brief.json", "language", "language must be ja")

    revision = design.get("revision")
    if design.get("status") not in STATUSES or script.get("status") not in STATUSES:
        issue("error", "authoring-pack", "approval-status", f"design and script status must be in {sorted(STATUSES)}")
    if not isinstance(revision, int) or revision < 1 or script.get("revision") != revision:
        issue("error", "authoring-pack", "revision", "positive design revision must match script revision")
    if design.get("status") == "APPROVED" and design.get("approvedRevision") != revision:
        issue("error", "scenario-design.json", "approval-revision", "approvedRevision must match revision")
    if script.get("status") == "APPROVED" and design.get("status") != "APPROVED":
        issue("error", "script.json", "approval-order", "script cannot be approved before design")
    approved = design.get("status") == script.get("status") == "APPROVED" and design.get("approvedRevision") == revision
    if require_approved and not approved:
        issue("error", "authoring-pack", "approval-gate", "approved design and script are required")
    external = brief.get("externalReview") if isinstance(brief.get("externalReview"), dict) else {}
    if external.get("status") not in EXTERNAL_STATUSES:
        issue("error", "project-brief.json", "external-review-status", f"invalid status: {external.get('status')}")
    if not isinstance(external.get("externalTransmissionApproved", False), bool):
        issue("error", "project-brief.json", "transmission-approval", "externalTransmissionApproved must be boolean")

    character_ids: set[str] = set()
    for index, character in enumerate(bible.get("characters") or []):
        location = f"character-bible.json:characters[{index}]"
        identifier = str(character.get("id", "")) if isinstance(character, dict) else ""
        if not ID_RE.fullmatch(identifier) or identifier in character_ids:
            issue("error", location, "character-id", f"invalid or duplicate ID: {identifier!r}")
        character_ids.add(identifier)
        if isinstance(character, dict) and character.get("age") is None and not str(character.get("ageCategory", "")).strip():
            issue("error", location, "age", "exact age or ageCategory is required")
        for field in ("displayName", "role", "desire", "obstacle"):
            if isinstance(character, dict) and not str(character.get(field, "")).strip():
                issue("warning", location, "bible-completeness", f"missing {field}")
    allowed = {str(item) for item in (rules.get("allowedSpeakers") or [])}
    expected_allowed = character_ids | {"narrator"}
    if allowed != expected_allowed:
        issue("error", "language-rules.json", "allowed-speakers", f"expected {sorted(expected_allowed)}, found {sorted(allowed)}")

    state_defs: dict[str, dict[str, Any]] = {}
    for index, definition in enumerate(script.get("stateVariables") or []):
        location = f"script.json:stateVariables[{index}]"
        identifier = str(definition.get("id", "")) if isinstance(definition, dict) else ""
        if not ID_RE.fullmatch(identifier) or identifier in state_defs:
            issue("error", location, "state-id", f"invalid or duplicate state ID: {identifier!r}")
            continue
        state_defs[identifier] = definition
        state_type = str(definition.get("type", ""))
        if state_type not in STATE_TYPES or "initial" not in definition or not matches_type(definition.get("initial"), state_type):
            issue("error", location, "state-definition", "type must be boolean/integer/string and initial must match")
    brief_state = (brief.get("branching") or {}).get("stateVariables") if isinstance(brief.get("branching"), dict) else []
    brief_state_ids = {str(item.get("id")) if isinstance(item, dict) else str(item) for item in (brief_state or [])}
    if brief_state_ids != set(state_defs):
        issue("error", "project-brief.json", "state-declaration-match", f"brief={sorted(brief_state_ids)}, script={sorted(state_defs)}")

    cue_defs: dict[str, dict[str, Any]] = {}
    for index, cue in enumerate(script.get("cues") or []):
        location = f"script.json:cues[{index}]"
        identifier = str(cue.get("id", "")) if isinstance(cue, dict) else ""
        if not ID_RE.fullmatch(identifier) or identifier in cue_defs:
            issue("error", location, "cue-id", f"invalid or duplicate cue ID: {identifier!r}")
            continue
        cue_defs[identifier] = cue
        for field_path in forbidden_cue_fields(cue, location):
            issue("error", field_path, "engine-neutral-cue", "engine/asset implementation field is forbidden")
        for field in ("kind", "emotion", "narrativePurpose", "characters", "visibleContent", "musicFunction", "playbackIntent"):
            if field not in cue:
                issue("error", location, "cue-field", f"missing {field}")
        if cue.get("playbackIntent") not in PLAYBACK_INTENTS:
            issue("error", location, "cue-playback", f"invalid playbackIntent: {cue.get('playbackIntent')}")
        unknown = {str(item) for item in (cue.get("characters") or [])} - character_ids
        if unknown:
            issue("error", location, "cue-character", f"unknown characters: {sorted(unknown)}")

    scenes = script.get("scenes") if isinstance(script.get("scenes"), list) else []
    scene_ids = [str(scene.get("id", "")) if isinstance(scene, dict) else "" for scene in scenes]
    known_scenes = set(scene_ids)
    if any(not ID_RE.fullmatch(value) for value in scene_ids) or len(scene_ids) != len(known_scenes):
        issue("error", "script.json", "scene-id", "scene IDs must be valid and unique")
    start = str(script.get("startSceneId", ""))
    if start not in known_scenes:
        issue("error", "script.json", "start-scene", f"unknown startSceneId: {start}")

    ending_ids: set[str] = set()
    ending_scenes: dict[str, str] = {}
    for index, ending in enumerate(script.get("endings") or []):
        location = f"script.json:endings[{index}]"
        identifier, scene_id = str(ending.get("id", "")), str(ending.get("sceneId", ""))
        if not ID_RE.fullmatch(identifier) or identifier in ending_ids:
            issue("error", location, "ending-id", f"invalid or duplicate ending ID: {identifier!r}")
        if scene_id not in known_scenes or scene_id in ending_scenes:
            issue("error", location, "ending-scene", f"unknown or multiply assigned ending scene: {scene_id}")
        ending_ids.add(identifier); ending_scenes[scene_id] = identifier

    edges: dict[str, list[str]] = {scene_id: [] for scene_id in known_scenes}
    flows: dict[str, tuple[str, list[str]]] = {}
    entry_ids: set[str] = set(); option_ids: set[str] = set(); cue_uses: set[str] = set(); state_reads: set[str] = set(); state_writes: set[str] = set()
    choice_count = 0; line_count = 0

    def read_when(value: Any, location: str) -> None:
        if value is None:
            return
        if not isinstance(value, dict) or "variableId" not in value or "equals" not in value:
            issue("error", location, "state-condition", "when needs variableId and equals"); return
        variable = str(value.get("variableId"))
        if variable not in state_defs:
            issue("error", location, "state-read", f"unknown variable: {variable}")
        elif not matches_type(value.get("equals"), str(state_defs[variable].get("type"))):
            issue("error", location, "state-read-type", f"wrong equals type for {variable}")
        else:
            state_reads.add(variable)

    def write_assignment(variable: str, value: Any, location: str) -> None:
        if variable not in state_defs:
            issue("error", location, "state-write", f"unknown variable: {variable}")
        elif not matches_type(value, str(state_defs[variable].get("type"))):
            issue("error", location, "state-write-type", f"wrong value type for {variable}")
        else:
            state_writes.add(variable)

    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("id", "")); entries = scene.get("entries") if isinstance(scene.get("entries"), list) else []
        terminals = [entry for entry in entries if isinstance(entry, dict) and entry.get("type") in {"choice", "jump"}]
        if terminals and (len(terminals) != 1 or not entries or entries[-1] is not terminals[0]):
            issue("error", scene_id, "terminal-flow", "choice/jump must be the single terminal entry")
        next_scene = scene.get("nextSceneId")
        if next_scene is not None:
            if terminals:
                issue("error", scene_id, "duplicate-flow", "nextSceneId cannot coexist with terminal choice/jump")
            elif str(next_scene) not in known_scenes:
                issue("error", scene_id, "next-scene", f"unknown target: {next_scene}")
            else:
                edges[scene_id].append(str(next_scene)); flows[scene_id] = ("linear", [str(next_scene)])
        for index, entry in enumerate(entries):
            location = f"{scene_id}:entries[{index}]"
            if not isinstance(entry, dict):
                issue("error", location, "entry-object", "entry must be an object"); continue
            kind, identifier = str(entry.get("type", "")), str(entry.get("id", ""))
            if kind not in ENTRY_TYPES:
                issue("error", location, "entry-type", f"unknown type: {kind}")
            if not ID_RE.fullmatch(identifier) or identifier in entry_ids:
                issue("error", location, "entry-id", f"invalid or duplicate ID: {identifier!r}")
            entry_ids.add(identifier); read_when(entry.get("when"), location)
            if kind == "line":
                line_count += 1
                if entry.get("speaker") not in allowed:
                    issue("error", location, "speaker", f"unknown speaker: {entry.get('speaker')}")
                if not str(entry.get("text", "")).strip():
                    issue("error", location, "line-text", "visible text is empty")
            elif kind == "cue":
                cue_id = str(entry.get("cueId", "")); cue_uses.add(cue_id)
                if cue_id not in cue_defs:
                    issue("error", location, "cue-reference", f"unknown cueId: {cue_id}")
            elif kind == "state":
                variable, operation = str(entry.get("variableId", "")), str(entry.get("operation", ""))
                if operation not in {"set", "add", "subtract", "toggle"}:
                    issue("error", location, "state-operation", f"invalid operation: {operation}")
                elif variable in state_defs:
                    state_type = str(state_defs[variable].get("type"))
                    if operation == "toggle" and state_type != "boolean": issue("error", location, "state-operation-type", "toggle requires boolean")
                    elif operation in {"add", "subtract"} and state_type != "integer": issue("error", location, "state-operation-type", "add/subtract require integer")
                    elif operation != "toggle": write_assignment(variable, entry.get("value"), location)
                    else: state_writes.add(variable)
                else: write_assignment(variable, entry.get("value"), location)
                for bound in ("min", "max"):
                    if bound in entry and (not isinstance(entry[bound], int) or isinstance(entry[bound], bool)):
                        issue("error", location, "state-bound", f"{bound} must be integer")
            elif kind == "jump":
                target = str(entry.get("targetSceneId", ""))
                if target not in known_scenes: issue("error", location, "jump-target", f"unknown target: {target}")
                else: edges[scene_id].append(target); flows[scene_id] = ("linear", [target])
            elif kind == "choice":
                choice_count += 1; options = entry.get("options") if isinstance(entry.get("options"), list) else []
                if len(options) < 2: issue("error", location, "choice-options", "at least two options required")
                targets: list[str] = []
                for option_index, option in enumerate(options):
                    option_location = f"{location}:options[{option_index}]"
                    option_id = str(option.get("id", "")) if isinstance(option, dict) else ""
                    if not ID_RE.fullmatch(option_id) or option_id in option_ids: issue("error", option_location, "option-id", f"invalid or duplicate ID: {option_id!r}")
                    option_ids.add(option_id)
                    if not isinstance(option, dict) or not str(option.get("text", "")).strip(): issue("error", option_location, "option-text", "visible text is empty")
                    target = str(option.get("targetSceneId", "")) if isinstance(option, dict) else ""; targets.append(target)
                    if target not in known_scenes: issue("error", option_location, "choice-target", f"unknown target: {target}")
                    else: edges[scene_id].append(target)
                    read_when(option.get("when") if isinstance(option, dict) else None, option_location)
                    for variable, value in ((option.get("setState") or {}).items() if isinstance(option, dict) and isinstance(option.get("setState"), dict) else []): write_assignment(str(variable), value, option_location)
                flows[scene_id] = ("choice", targets)
        if scene_id in ending_scenes:
            if edges[scene_id]: issue("error", scene_id, "ending-flow", "ending scene must have no outgoing flow")
            flows[scene_id] = ("ending", [])
        elif scene_id not in flows:
            issue("error", scene_id, "dead-end", "non-ending scene needs nextSceneId, choice, or jump")

    try: all_shared_ids(script)
    except ValidationError as exc: issue("error", "script.json", "global-id-uniqueness", str(exc))
    for cue_id in sorted(set(cue_defs) - cue_uses): issue("warning", cue_id, "unused-cue", "cue is never referenced")
    for variable in sorted(set(state_defs) - (state_reads | state_writes)): issue("warning", variable, "unused-state", "state is never read or written")

    reachable: set[str] = set(); queue: deque[str] = deque([start] if start in known_scenes else [])
    while queue:
        current = queue.popleft()
        if current in reachable: continue
        reachable.add(current); queue.extend(target for target in edges.get(current, []) if target not in reachable)
    for scene_id in sorted(known_scenes - reachable): issue("error", scene_id, "unreachable-scene", "unreachable from startSceneId")
    reachable_endings = {ending_scenes[scene_id] for scene_id in reachable if scene_id in ending_scenes}
    for ending_id in sorted(ending_ids - reachable_endings): issue("error", ending_id, "unreachable-ending", "ending is unreachable")

    memo: dict[str, int] = {}; visiting: set[str] = set(); cycle_reported: set[str] = set()
    def count_histories(scene_id: str) -> int:
        if scene_id in memo: return memo[scene_id]
        if scene_id in visiting:
            if scene_id not in cycle_reported: issue("error", scene_id, "cyclic-flow", "finite choice-history count cannot be proven for a cycle"); cycle_reported.add(scene_id)
            return 0
        if scene_id not in flows: return 0
        visiting.add(scene_id); kind, targets = flows[scene_id]
        count = 1 if kind == "ending" else sum(count_histories(target) for target in targets)
        visiting.remove(scene_id); memo[scene_id] = count; return count
    history_count = count_histories(start) if start in known_scenes else 0
    branching = brief.get("branching") if isinstance(brief.get("branching"), dict) else {}
    for field, actual in (("choiceCount", choice_count), ("endingCount", len(ending_ids)), ("choiceHistoryCount", history_count)):
        if branching.get(field) != actual: issue("error", "project-brief.json", "branching-count", f"{field}={branching.get(field)!r}, calculated={actual}")

    errors = [item for item in issues if item["severity"] == "error"]; warnings = [item for item in issues if item["severity"] == "warning"]
    return {"status": "fail" if errors else "pass", "approved": approved, "statistics": {"scenes": len(scenes), "entries": len(entry_ids), "lines": line_count, "choices": choice_count, "choiceHistoryCount": history_count, "endings": len(ending_ids), "reachableEndings": len(reachable_endings), "stateVariables": len(state_defs), "cues": len(cue_defs), "errors": len(errors), "warnings": len(warnings)}, "reachableScenes": sorted(reachable), "reachableEndings": sorted(reachable_endings), "stateReads": sorted(state_reads), "stateWrites": sorted(state_writes), "issues": issues}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate shared Japanese VN schema, graph, state, stable IDs, and approvals.")
    parser.add_argument("--project-root", type=Path, required=True); parser.add_argument("--authoring-dir", type=Path, required=True); parser.add_argument("--report", type=Path, required=True); parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True); paths = source_paths(root, args.authoring_dir); report_path = contained(root, args.report)
        report = validate_pack({name: load_json(path) for name, path in paths.items()}, require_approved=args.require_approved)
        hashes, aggregate = source_hashes(paths); report["sourceSha256"] = hashes; report["sourceAggregateSha256"] = aggregate; dump_json(report_path, report)
        print(json.dumps({"status": report["status"], "sourceAggregateSha256": aggregate, **report["statistics"]}, ensure_ascii=False))
        if report["status"] != "pass": raise SystemExit(1)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr); raise SystemExit(2) from exc


if __name__ == "__main__": main()
