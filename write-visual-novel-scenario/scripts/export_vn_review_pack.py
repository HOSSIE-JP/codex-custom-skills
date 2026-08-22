from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from validate_vn_scenario import validate_pack
from vn_common import ValidationError, contained, dump_json, load_json, sha256_file, source_hashes, source_paths


PASS_NAMES = ("mechanical", "readAloud", "characterVoice", "expositionAndBranchJoins")


def fenced(value: Any) -> list[str]:
    return ["```json", json.dumps(value, ensure_ascii=False, indent=2), "```"]


def require_self_review(review: dict[str, Any]) -> list[str]:
    if review.get("status") != "complete":
        raise ValidationError("self-review status must be complete before export")
    passes = review.get("passes") if isinstance(review.get("passes"), dict) else {}
    concerns: list[str] = []
    for name in PASS_NAMES:
        value = passes.get(name) if isinstance(passes.get(name), dict) else {}
        if value.get("status") != "complete" or not str(value.get("evidence", "")).strip():
            raise ValidationError(f"self-review pass needs complete status and evidence: {name}")
        revisions = value.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            raise ValidationError(f"self-review pass needs a concrete revision or explicit no-change record: {name}")
        concerns.extend(str(item) for item in (value.get("remainingConcerns") or []) if str(item).strip())
    return concerns


def risk_recommendation(brief: dict[str, Any], concerns: list[str]) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    minutes = brief.get("expectedMinutes")
    if isinstance(minutes, (int, float)) and minutes >= 90:
        score += 2; reasons.append("long-form runtime (90+ minutes)")
    elif isinstance(minutes, (int, float)) and minutes >= 30:
        score += 1; reasons.append("extended runtime (30+ minutes)")
    endings = int((brief.get("branching") or {}).get("endingCount", 0))
    if endings >= 4:
        score += 2; reasons.append("four or more endings")
    elif endings >= 2:
        score += 1; reasons.append("multiple endings")
    risk = brief.get("reviewRisk") if isinstance(brief.get("reviewRisk"), dict) else {}
    if risk.get("usesDialect"):
        score += 1; reasons.append("dialect or regional voice")
    if risk.get("usesSpecializedFacts"):
        score += 2; reasons.append("specialized factual claims")
    topics = [str(item) for item in risk.get("sensitiveTopics") or [] if str(item).strip()]
    if topics:
        score += 2; reasons.append("sensitive topics: " + ", ".join(topics))
    if concerns:
        score += 2; reasons.append(f"{len(concerns)} unresolved self-review concern(s)")
    level = "strongly-recommended" if score >= 5 else "recommended" if score >= 3 else "optional-but-consult-user"
    return {"score": score, "level": level, "reasons": reasons, "unresolvedConcerns": concerns}


def script_markdown(script: dict[str, Any], bible: dict[str, Any], aggregate: str) -> tuple[list[str], dict[str, int]]:
    names = {"narrator": "地の文"}
    names.update({str(item.get("id")): str(item.get("displayName", item.get("id"))) for item in bible.get("characters") or []})
    lines = ["# Scenario script for independent Japanese review", "", "Return prose edits by stable ID with before/after/reason. Submit structural changes separately.", "", f"Source aggregate SHA-256: `{aggregate}`", ""]
    counts = {"scenes": 0, "lines": 0, "choices": 0, "options": 0, "cues": 0, "stateEntries": 0, "endings": len(script.get("endings") or [])}
    for scene in script.get("scenes") or []:
        counts["scenes"] += 1
        lines.extend([f"## `{scene['id']}`", "", str(scene.get("summary", "")), ""])
        for entry in scene.get("entries") or []:
            kind, identifier = str(entry.get("type")), str(entry.get("id"))
            if kind == "line":
                counts["lines"] += 1
                lines.extend([f"[{identifier}] {names.get(str(entry.get('speaker')), str(entry.get('speaker')))}: {entry.get('text', '')}", ""])
            elif kind == "choice":
                counts["choices"] += 1
                lines.extend([f"### CHOICE `{identifier}`", ""])
                if entry.get("prompt"):
                    lines.extend([f"Prompt: {entry['prompt']}", ""])
                for option in entry.get("options") or []:
                    counts["options"] += 1
                    lines.append(f"- [{option['id']}] {option.get('text', '')} -> `{option.get('targetSceneId', '')}`; setState={json.dumps(option.get('setState') or {}, ensure_ascii=False, separators=(',', ':'))}")
                lines.append("")
            elif kind == "cue":
                counts["cues"] += 1
                lines.extend([f"[{identifier}] CUE `{entry.get('cueId', '')}`", ""])
            elif kind == "state":
                counts["stateEntries"] += 1
                lines.extend([f"[{identifier}] STATE {entry.get('variableId')} {entry.get('operation')} {json.dumps(entry.get('value'), ensure_ascii=False)}", ""])
            elif kind == "jump":
                lines.extend([f"[{identifier}] JUMP -> `{entry.get('targetSceneId', '')}`", ""])
        if scene.get("nextSceneId"):
            lines.extend([f"NEXT -> `{scene['nextSceneId']}`", ""])
        for ending in script.get("endings") or []:
            if ending.get("sceneId") == scene.get("id"):
                lines.extend([f"ENDING `{ending.get('id')}`: {ending.get('title', '')}", ""])
        lines.extend(["---", ""])
    return lines, counts


def write_markdown(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export deterministic local Markdown for independent Japanese review.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--authoring-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True)
        paths = source_paths(root, args.authoring_dir)
        out = contained(root, args.out)
        data = {name: load_json(path) for name, path in paths.items()}
        validation = validate_pack(data, require_approved=True)
        if validation["status"] != "pass":
            details = "; ".join(item["detail"] for item in validation["issues"] if item["severity"] == "error")
            raise ValidationError("authoring validation failed: " + details)
        concerns = require_self_review(data["self-review.json"])
        hashes, aggregate = source_hashes(paths)
        recommendation = risk_recommendation(data["project-brief.json"], concerns)
        out.mkdir(parents=True, exist_ok=True)
        concept = ["# Work concept and approved design", "", f"Source aggregate SHA-256: `{aggregate}`", "", "## Project brief", "", *fenced(data["project-brief.json"]), "", "## Approved scenario design", "", *fenced(data["scenario-design.json"])]
        characters = ["# Character settings", "", f"Source aggregate SHA-256: `{aggregate}`", ""]
        for character in data["character-bible.json"].get("characters") or []:
            characters.extend([f"## {character.get('displayName', character.get('id'))} (`{character.get('id')}`)", "", *fenced(character), ""])
        script_lines, counts = script_markdown(data["script.json"], data["character-bible.json"], aggregate)
        outputs = {"01_concept.md": concept, "02_character_settings.md": characters, "03_scenario_script.md": script_lines}
        for name, lines in outputs.items():
            write_markdown(out / name, lines)
        workflow = data["project-brief.json"]["externalReview"]
        manifest = {
            "formatVersion": 2,
            "sourceFiles": {name: {"relativePath": name, "sha256": hashes[name]} for name in sorted(hashes)},
            "sourceAggregateSha256": aggregate,
            "counts": counts,
            "validation": {"approved": validation["approved"], "reachableEndings": validation["reachableEndings"], "choiceHistoryCount": validation["statistics"]["choiceHistoryCount"]},
            "riskRecommendation": recommendation,
            "workflow": {"consultationStatus": workflow["status"], "externalTransmissionApproved": bool(workflow.get("externalTransmissionApproved", False)), "externalTransmissionPerformed": False},
            "files": {name: sha256_file(out / name) for name in sorted(outputs)},
        }
        dump_json(out / "review-manifest.json", manifest)
        print(json.dumps({"status": "pass", "sourceAggregateSha256": aggregate, "riskRecommendation": recommendation, **counts}, ensure_ascii=False))
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
