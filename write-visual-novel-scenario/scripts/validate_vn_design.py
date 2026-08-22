from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from validate_vn_core import forbidden_cue_fields
from vn_common import ID_RE, ValidationError, contained, dump_json, load_json, sha256_file


DESIGN_FILES = ("project-brief.json", "character-bible.json", "scenario-design.json", "language-rules.json")


def meaningful(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(meaningful(item) for item in value.values())
    if isinstance(value, list):
        return any(meaningful(item) for item in value)
    return value is not None


def item_id(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("id") or value.get("lensId") or value.get("choiceId") or "")
    return ""


def stable_unique(items: list[Any], label: str, issue: Any, *, id_getter: Any = item_id) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        identifier = str(id_getter(item))
        location = f"{label}[{index}]"
        if not ID_RE.fullmatch(identifier):
            issue("error", location, "stable-id", f"invalid stable ID: {identifier!r}")
        elif identifier in seen:
            issue("error", location, "duplicate-id", f"duplicate stable ID: {identifier}")
        seen.add(identifier)
    return seen


def collect_plan_references(value: Any) -> tuple[set[str], set[str]]:
    state_refs: set[str] = set()
    scene_refs: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in {"variableid", "statevariableid"} and isinstance(child, str):
                state_refs.add(child)
            elif normalized in {"statereads", "statewrites", "statevariables"} and isinstance(child, list):
                state_refs.update(str(item.get("id")) if isinstance(item, dict) else str(item) for item in child)
            elif normalized == "setstate" and isinstance(child, dict):
                state_refs.update(map(str, child.keys()))
            if normalized.endswith("sceneid") and isinstance(child, str):
                scene_refs.add(child)
            elif normalized.endswith("sceneids") and isinstance(child, list):
                scene_refs.update(map(str, child))
            nested_states, nested_scenes = collect_plan_references(child)
            state_refs.update(nested_states); scene_refs.update(nested_scenes)
    elif isinstance(value, list):
        for child in value:
            nested_states, nested_scenes = collect_plan_references(child)
            state_refs.update(nested_states); scene_refs.update(nested_scenes)
    return state_refs, scene_refs


def validate_design(data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    brief, bible, design, rules = (data[name] for name in DESIGN_FILES)
    issues: list[dict[str, str]] = []

    def issue(severity: str, location: str, rule: str, detail: str) -> None:
        issues.append({"severity": severity, "location": location, "rule": rule, "detail": detail})

    for name, value in data.items():
        if value.get("formatVersion") != 2:
            issue("error", name, "format-version", "formatVersion must be 2")
    project_ids = {str(value.get("projectId", "")) for value in (brief, bible, design)}
    project_id = next(iter(project_ids), "")
    if len(project_ids) != 1 or not project_id or "replace-with" in project_id:
        issue("error", "design-pack", "project-id", f"projectId must be populated and identical: {sorted(project_ids)}")
    if brief.get("language") != "ja":
        issue("error", "project-brief.json", "language", "language must be ja")
    revision, status = design.get("revision"), design.get("status")
    if not isinstance(revision, int) or revision < 1:
        issue("error", "scenario-design.json", "revision", "revision must be a positive integer")
    if status not in {"REVIEW_REQUIRED", "APPROVED"}:
        issue("error", "scenario-design.json", "design-status", "status must be REVIEW_REQUIRED or APPROVED")
    elif status == "REVIEW_REQUIRED" and design.get("approvedRevision") is not None:
        issue("error", "scenario-design.json", "approval-revision", "REVIEW_REQUIRED must have approvedRevision=null")
    elif status == "APPROVED" and design.get("approvedRevision") != revision:
        issue("error", "scenario-design.json", "approval-revision", "APPROVED requires approvedRevision equal to revision")

    characters = bible.get("characters") if isinstance(bible.get("characters"), list) else []
    character_ids = stable_unique(characters, "character-bible.json:characters", issue)
    explicit_major = [item for item in characters if isinstance(item, dict) and (item.get("major") is True or str(item.get("importance", "")).lower() in {"major", "main", "protagonist"} or "主人公" in str(item.get("role", "")) or "主要" in str(item.get("role", "")))]
    major_characters = explicit_major or characters
    if not major_characters:
        issue("error", "character-bible.json", "major-character", "at least one major character is required")
    arcs = {str(item.get("characterId") or item.get("id")): item for item in (design.get("characterArcs") or []) if isinstance(item, dict)}
    for character in major_characters:
        if not isinstance(character, dict):
            continue
        identifier = str(character.get("id", "")); arc = arcs.get(identifier, {})
        for field in ("desire", "obstacle"):
            if not meaningful(character.get(field)) and not meaningful(arc.get(field)):
                issue("error", identifier, "major-character-motivation", f"major character needs {field}")
        if not any(meaningful(character.get(key)) for key in ("change", "arc", "changeArc", "transformation")) and not any(meaningful(arc.get(key)) for key in ("change", "arc", "changeArc", "transformation")):
            issue("error", identifier, "major-character-change", "major character needs an intended change or explicit constancy arc")
        if not meaningful(character.get("voice")):
            issue("error", identifier, "major-character-voice", "major character needs non-empty voice/style guidance")
    allowed = {str(item) for item in (rules.get("allowedSpeakers") or [])}
    if allowed != character_ids | {"narrator"}:
        issue("error", "language-rules.json", "allowed-speakers", f"expected narrator plus character IDs: {sorted(character_ids | {'narrator'})}")

    candidates = design.get("structureLensCandidates") if isinstance(design.get("structureLensCandidates"), list) else []
    candidate_ids = stable_unique(candidates, "scenario-design.json:structureLensCandidates", issue)
    if len(candidates) < 2:
        issue("error", "scenario-design.json", "structure-lens-count", "at least two plausible structure lenses are required")
    selected_items = design.get("selectedStructureLenses") if isinstance(design.get("selectedStructureLenses"), list) else []
    selected_ids = {item_id(item) for item in selected_items}
    selected_reasons = {item_id(item): item for item in selected_items if isinstance(item, dict)}
    if not selected_ids:
        issue("error", "scenario-design.json", "selected-structure-lens", "select at least one structure lens")
    for unknown in sorted(selected_ids - candidate_ids):
        issue("error", unknown, "selected-structure-lens", "selected lens is not a candidate")
    if candidate_ids and not (candidate_ids - selected_ids):
        issue("error", "scenario-design.json", "rejected-structure-lens", "retain at least one rejected alternative with a reason")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            issue("error", item_id(candidate), "structure-lens-reason", "lens candidates must be objects with decision reasons")
            continue
        identifier = item_id(candidate)
        if identifier in selected_ids:
            selected_item = selected_reasons.get(identifier, {})
            if not any(meaningful(source.get(key)) for source in (candidate, selected_item) for key in ("selectionReason", "fitReason", "decisionReason", "reason")):
                issue("error", identifier, "structure-lens-reason", "selected lens needs a selection reason")
        elif not any(meaningful(candidate.get(key)) for key in ("rejectionReason", "reasonNotSelected", "decisionReason")):
            issue("error", identifier, "structure-lens-reason", "rejected lens needs a rejection reason")

    beats = design.get("beats") if isinstance(design.get("beats"), list) else []
    if not beats:
        issue("error", "scenario-design.json", "beats", "beats must be non-empty")
    else:
        stable_unique(beats, "scenario-design.json:beats", issue)
    scene_boxes = design.get("sceneBoxes") if isinstance(design.get("sceneBoxes"), list) else []
    if not scene_boxes:
        issue("error", "scenario-design.json", "scene-boxes", "sceneBoxes must be non-empty")
    scene_ids = stable_unique(scene_boxes, "scenario-design.json:sceneBoxes", issue)
    expected_minutes = brief.get("expectedMinutes")
    duration = 0.0; duration_valid = isinstance(expected_minutes, (int, float)) and not isinstance(expected_minutes, bool)
    for index, scene in enumerate(scene_boxes):
        minutes = scene.get("estimatedMinutes", scene.get("minutes")) if isinstance(scene, dict) else None
        if not isinstance(minutes, (int, float)) or isinstance(minutes, bool) or minutes < 0:
            issue("error", f"scenario-design.json:sceneBoxes[{index}]", "scene-duration", "scene needs non-negative minutes/estimatedMinutes")
            duration_valid = False
        else:
            duration += float(minutes)
    if not isinstance(expected_minutes, (int, float)) or isinstance(expected_minutes, bool):
        issue("error", "project-brief.json", "expected-minutes", "expectedMinutes must be numeric at design review")
    elif duration_valid and not math.isclose(float(expected_minutes), duration, abs_tol=1e-6):
        issue("error", "scenario-design.json", "duration-total", f"scene minutes total {duration:g} != expectedMinutes {expected_minutes}")

    branch_plan = design.get("branchAndJoinPlan") if isinstance(design.get("branchAndJoinPlan"), list) else []
    choices = [item for item in branch_plan if isinstance(item, dict) and (str(item.get("type") or item.get("kind")).lower() == "choice" or "choiceId" in item or "options" in item)]
    choice_ids = stable_unique(choices, "scenario-design.json:branchAndJoinPlan.choice", issue, id_getter=lambda item: str(item.get("choiceId") or item.get("id") or ""))
    for choice in choices:
        options = choice.get("options") if isinstance(choice.get("options"), list) else []
        if len(options) < 2:
            issue("error", str(choice.get("choiceId") or choice.get("id")), "choice-options", "choice plan needs at least two options")
        stable_unique(options, f"choice:{choice.get('choiceId') or choice.get('id')}:options", issue)
    endings = design.get("endingPlan") if isinstance(design.get("endingPlan"), list) else []
    ending_ids = stable_unique(endings, "scenario-design.json:endingPlan", issue)
    branching = brief.get("branching") if isinstance(brief.get("branching"), dict) else {}
    if branching.get("choiceCount") != len(choice_ids):
        issue("error", "project-brief.json", "choice-count", f"choiceCount={branching.get('choiceCount')!r}, design={len(choice_ids)}")
    if branching.get("endingCount") != len(ending_ids):
        issue("error", "project-brief.json", "ending-count", f"endingCount={branching.get('endingCount')!r}, design={len(ending_ids)}")
    declared_states = {str(item.get("id")) if isinstance(item, dict) else str(item) for item in (branching.get("stateVariables") or [])}
    state_refs, scene_refs = collect_plan_references([branch_plan, endings])
    for unknown in sorted(state_refs - declared_states):
        issue("error", unknown, "unknown-state-reference", "branch/join plan references undeclared state")
    for unknown in sorted(scene_refs - scene_ids):
        issue("error", unknown, "unknown-scene-reference", "branch/join/ending plan references unknown scene")

    cues = design.get("semanticCuePlan") if isinstance(design.get("semanticCuePlan"), list) else []
    stable_unique(cues, "scenario-design.json:semanticCuePlan", issue)
    for index, cue in enumerate(cues):
        for field_path in forbidden_cue_fields(cue, f"scenario-design.json:semanticCuePlan[{index}]"):
            issue("error", field_path, "engine-neutral-cue", "engine/asset implementation field is forbidden")
        if isinstance(cue, dict):
            unknown_characters = {str(item) for item in (cue.get("characters") or [])} - character_ids
            if unknown_characters:
                issue("error", str(cue.get("id", "")), "cue-character", f"unknown characters: {sorted(unknown_characters)}")

    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    return {"status": "fail" if errors else "pass", "mode": "design-only", "designStatus": status, "revision": revision, "statistics": {"characters": len(characters), "structureLenses": len(candidates), "beats": len(beats), "sceneBoxes": len(scene_boxes), "plannedMinutes": duration, "choices": len(choice_ids), "endings": len(ending_ids), "semanticCues": len(cues), "errors": len(errors), "warnings": len(warnings)}, "issues": issues}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the script-independent Japanese VN design-review stage.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--authoring-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True); authoring = contained(root, args.authoring_dir, must_exist=True); report_path = contained(root, args.report)
        paths = {name: contained(root, authoring / name, must_exist=True) for name in DESIGN_FILES}
        data = {name: load_json(path) for name, path in paths.items()}
        report = validate_design(data)
        hashes = {name: sha256_file(path) for name, path in sorted(paths.items())}
        canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("ascii")
        report["sourceSha256"] = hashes; report["sourceAggregateSha256"] = hashlib.sha256(canonical).hexdigest(); dump_json(report_path, report)
        print(json.dumps({"status": report["status"], "mode": "design-only", **report["statistics"]}, ensure_ascii=False))
        if report["status"] != "pass": raise SystemExit(1)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr); raise SystemExit(2) from exc


if __name__ == "__main__": main()
