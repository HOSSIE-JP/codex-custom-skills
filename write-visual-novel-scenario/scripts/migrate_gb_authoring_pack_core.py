from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from vn_common import ID_RE, ValidationError, content_id, contained, dump_json, load_json


TEMPLATES = Path(__file__).resolve().parents[1] / "assets" / "templates"


def template(name: str) -> dict[str, Any]: return load_json(TEMPLATES / name)


def stable(value: Any, prefix: str, payload: Any, used: set[str]) -> str:
    identifier = str(value or "")
    if ID_RE.fullmatch(identifier) and identifier not in used:
        used.add(identifier); return identifier
    return content_id(prefix, payload, used)


def history_count(script: dict[str, Any]) -> int:
    endings = {str(item.get("sceneId")) for item in script["endings"]}
    flows: dict[str, list[str]] = {}
    for scene in script["scenes"]:
        scene_id = scene["id"]
        if scene_id in endings: flows[scene_id] = []
        elif scene.get("nextSceneId"): flows[scene_id] = [scene["nextSceneId"]]
        elif scene["entries"] and scene["entries"][-1].get("type") == "choice": flows[scene_id] = [item["targetSceneId"] for item in scene["entries"][-1]["options"]]
        elif scene["entries"] and scene["entries"][-1].get("type") == "jump": flows[scene_id] = [scene["entries"][-1]["targetSceneId"]]
        else: flows[scene_id] = []
    memo: dict[str, int] = {}; visiting: set[str] = set()
    def count(scene_id: str) -> int:
        if scene_id in memo: return memo[scene_id]
        if scene_id in visiting: raise ValidationError("legacy graph contains a cycle; finite history count needs manual redesign")
        visiting.add(scene_id)
        result = 1 if scene_id in endings else sum(count(target) for target in flows.get(scene_id, []))
        visiting.remove(scene_id); memo[scene_id] = result; return result
    return count(script["startSceneId"])


def main() -> None:
    parser = argparse.ArgumentParser(description="One-way migration of a source-backed legacy GB VN authoring pack.")
    parser.add_argument("--project-root", type=Path, required=True); parser.add_argument("--source", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True); source = contained(root, args.source, must_exist=True); out = contained(root, args.out)
        if not source.is_dir(): raise ValidationError("legacy source must be an authoring-pack directory")
        if out.exists() and any(out.iterdir()): raise ValidationError(f"refusing to overwrite non-empty output: {out}")
        scenario_path = source / "scenario.json"
        if not scenario_path.exists():
            if list(source.glob("*.gbsres")): raise ValidationError("generated .gbsres alone is not an authoring source; refusing to infer author intent")
            raise ValidationError("legacy pack needs scenario.json")
        old = load_json(scenario_path); brief_old = load_json(source / "project-brief.json") if (source / "project-brief.json").exists() else {}; bible_old = load_json(source / "character-bible.json") if (source / "character-bible.json").exists() else {}; rules_old = load_json(source / "language-rules.json") if (source / "language-rules.json").exists() else {}
        project_id = str(brief_old.get("projectId") or old.get("projectId") or "migrated-project")
        if not ID_RE.fullmatch(project_id): project_id = "migrated-project"
        used: set[str] = set(); warnings: list[str] = []; unsupported: list[str] = []
        old_scenes = old.get("scenes") if isinstance(old.get("scenes"), list) else []
        scene_map = {str(item.get("id", "")): stable(item.get("id"), "scene", {"legacyScene": item.get("id"), "summary": item.get("summary")}, used) for item in old_scenes}
        scenes: list[dict[str, Any]] = []; endings: list[dict[str, Any]] = []
        for old_scene in old_scenes:
            scene_id = scene_map[str(old_scene.get("id", ""))]; entries: list[dict[str, Any]] = []; is_ending = False; terminal = False
            for command in old_scene.get("script") or []:
                kind = str(command.get("type", "")); payload = {"scene": scene_id, **command}
                if kind == "message": entries.append({"type": "line", "id": stable(command.get("id"), "line", payload, used), "speaker": str(command.get("speaker") or "narrator"), "text": str(command.get("text", ""))})
                elif kind == "choice":
                    choice_id = stable(command.get("id"), "choice", payload, used); options = []
                    for option in command.get("options") or []:
                        converted = {"id": stable(option.get("id"), "option", {"choice": choice_id, **option}, used), "text": str(option.get("text", "")), "targetSceneId": scene_map.get(str(option.get("target", "")), str(option.get("target", "")))}
                        state = option.get("setState") or option.get("state")
                        if isinstance(state, dict) and state: converted["setState"] = state
                        options.append(converted)
                    entry: dict[str, Any] = {"type": "choice", "id": choice_id, "options": options}
                    if command.get("prompt"): entry["prompt"] = command["prompt"]
                    entries.append(entry); terminal = True
                elif kind == "jump": entries.append({"type": "jump", "id": stable(command.get("id"), "jump", payload, used), "targetSceneId": scene_map.get(str(command.get("target", "")), str(command.get("target", "")))}); terminal = True
                elif kind in {"state", "setState"}: entries.append({"type": "state", "id": stable(command.get("id"), "state", payload, used), "variableId": str(command.get("variableId") or command.get("variable") or ""), "operation": str(command.get("operation") or "set"), "value": command.get("value")})
                elif kind == "routeEnding": is_ending = True
                elif kind in {"awaitInput", "returnLogo"}: warnings.append(f"{scene_id}: dropped engine-specific {kind}")
                elif kind in {"messageVariants", "genderMessages"}: unsupported.append(f"{scene_id}: {kind} needs manual narrative conversion")
                else: unsupported.append(f"{scene_id}: unknown command {kind!r}")
            scene: dict[str, Any] = {"id": scene_id, "summary": str(old_scene.get("summary", "migrated legacy scene")), "entries": entries}
            if old_scene.get("nextSceneId") and not terminal: scene["nextSceneId"] = scene_map.get(str(old_scene["nextSceneId"]), str(old_scene["nextSceneId"]))
            if is_ending: endings.append({"id": content_id("ending", {"sceneId": scene_id}, used), "title": str(old_scene.get("endingTitle", "Migrated ending")), "sceneId": scene_id})
            scenes.append(scene)
        if unsupported: raise ValidationError("migration needs manual decisions; " + "; ".join(unsupported))
        state_variables = old.get("stateVariables") or []
        script = {"formatVersion": 2, "projectId": project_id, "revision": 1, "status": "REVIEW_REQUIRED", "startSceneId": scene_map.get(str(old.get("initialScene", "")), str(old.get("initialScene", ""))), "stateVariables": state_variables, "cues": [], "endings": endings, "scenes": scenes}
        brief = template("project-brief.json"); brief.update({"projectId": project_id, "title": str(brief_old.get("title", "Migrated VN")), "audience": str((brief_old.get("experience") or {}).get("audience") or brief_old.get("audience") or "review required"), "expectedMinutes": (brief_old.get("experience") or {}).get("firstPlayMinutes", brief_old.get("expectedMinutes"))})
        choices = [entry for scene in scenes for entry in scene["entries"] if entry.get("type") == "choice"]
        brief["branching"] = {"choiceCount": len(choices), "endingCount": len(endings), "choiceHistoryCount": history_count(script), "stateVariables": [item.get("id") for item in state_variables if isinstance(item, dict)]}
        bible = template("character-bible.json"); bible.update({"projectId": project_id, "characters": bible_old.get("characters") or []})
        design = template("scenario-design.json"); design.update({"projectId": project_id, "premise": str(brief_old.get("premise", "manual reconstruction required")), "reviewNote": "One-way migration; approve structure before integration."})
        rules = template("language-rules.json"); rules["allowedSpeakers"] = sorted({"narrator"} | {str(item.get("id")) for item in bible["characters"] if isinstance(item, dict) and item.get("id")})
        for key in ("awkwardPhrases", "aiLikePatterns", "maxVisibleCharacters"):
            if key in rules_old: rules[key] = rules_old[key]
        values = {"project-brief.json": brief, "character-bible.json": bible, "scenario-design.json": design, "script.json": script, "language-rules.json": rules, "self-review.json": template("self-review.json")}
        out.mkdir(parents=True, exist_ok=True)
        for name, value in values.items(): dump_json(out / name, value)
        dump_json(out / "migration-report.json", {"formatVersion": 1, "status": "review-required", "source": str(source), "canonicalOutput": str(out), "assignedIds": sorted(used), "warnings": warnings})
        print(json.dumps({"status": "review-required", "scenes": len(scenes), "choices": len(choices), "endings": len(endings), "choiceHistoryCount": brief["branching"]["choiceHistoryCount"], "warnings": len(warnings)}, ensure_ascii=False))
    except ValidationError as exc:
        print(str(exc), file=sys.stderr); raise SystemExit(2) from exc


if __name__ == "__main__": main()
