from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def fenced_json(value: Any) -> list[str]:
    return ["```json", json.dumps(value, ensure_ascii=False, indent=2), "```"]


def validate_graph(scenario: dict[str, Any]) -> set[str]:
    scenes = scenario.get("scenes") or []
    ids = [str(scene.get("id", "")) for scene in scenes]
    if not ids or any(not scene_id for scene_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("scene IDs must be non-empty and unique")
    known = set(ids)
    if scenario.get("initialScene") not in known:
        raise ValueError("initialScene must reference an existing scene")
    for scene in scenes:
        for item in scene.get("script") or []:
            if item.get("type") == "jump" and item.get("target") not in known:
                raise ValueError(f"{scene['id']}: unknown jump target {item.get('target')}")
            if item.get("type") == "choice":
                for option in item.get("options") or []:
                    if option.get("target") not in known:
                        raise ValueError(f"{scene['id']}: unknown choice target {option.get('target')}")
    return known


def concept_markdown(brief: dict[str, Any], sha: str) -> list[str]:
    return [
        "# Work concept source",
        "",
        "This file is an exact structured export for an external Japanese-language reviewer. Preserve story facts, branch semantics, content boundaries, and runtime constraints unless proposing a separate structural change.",
        "",
        f"Scenario SHA-256: `{sha}`",
        "",
        "## Project brief",
        "",
        *fenced_json(brief),
    ]


def characters_markdown(bible: dict[str, Any], sha: str) -> list[str]:
    lines = [
        "# Character settings source",
        "",
        "Review voice, terms of address, fear, desire, pressure response, age, appearance, proportion, and wardrobe locks before revising the script.",
        "",
        f"Scenario SHA-256: `{sha}`",
        "",
    ]
    for character in bible.get("characters") or []:
        lines.extend([f"## {character.get('displayName', character.get('id', 'character'))} (`{character.get('id', '')}`)", "", *fenced_json(character), ""])
    return lines


def script_markdown(scenario: dict[str, Any], bible: dict[str, Any], sha: str) -> tuple[list[str], dict[str, int]]:
    names = {"": "narration"}
    names.update({str(item.get("id")): str(item.get("displayName", item.get("id"))) for item in bible.get("characters") or []})
    lines = [
        "# Scenario script for external review",
        "",
        "Return prose edits as `reference ID | before | after | reason`. Put branch or event changes in a separate structural proposal.",
        "",
        f"Scenario SHA-256: `{sha}`",
        "",
        f"Initial scene: `{scenario.get('initialScene', '')}`",
        "",
    ]
    counts = {"scenes": 0, "messages": 0, "choices": 0, "options": 0, "variants": 0}
    review_ids: set[str] = set()
    for scene_number, scene in enumerate(scenario.get("scenes") or [], 1):
        scene_id = str(scene["id"])
        counts["scenes"] += 1
        lines.extend([f"## SCENE {scene_number:02d}: `{scene_id}`", ""])
        metadata = {key: value for key, value in scene.items() if key != "script"}
        lines.extend(["Metadata:", "", *fenced_json(metadata), ""])
        message_number = 0
        for item in scene.get("script") or []:
            kind = str(item.get("type", ""))
            if kind == "message":
                message_number += 1
                counts["messages"] += 1
                ref = f"{scene_id}-M{message_number:02d}"
                text = str(item.get("text", ""))
                if not text:
                    raise ValueError(f"{ref}: visible text is empty")
                if ref in review_ids:
                    raise ValueError(f"duplicate review ID: {ref}")
                review_ids.add(ref)
                lines.extend([f"[{ref}] {names.get(str(item.get('speaker', '')), str(item.get('speaker', '')))}: {text}", ""])
            elif kind == "genderMessages":
                for variant, messages in (item.get("variants") or {}).items():
                    for index, message in enumerate(messages or [], 1):
                        counts["messages"] += 1
                        counts["variants"] += 1
                        ref = f"{scene_id}-G{variant}-M{index:02d}"
                        text = str(message.get("text", ""))
                        if not text or ref in review_ids:
                            raise ValueError(f"invalid review unit: {ref}")
                        review_ids.add(ref)
                        lines.extend([f"[{ref}] {names.get(str(message.get('speaker', '')), str(message.get('speaker', '')))}: {text}", ""])
            elif kind == "choice":
                counts["choices"] += 1
                choice_id = str(item.get("id", f"{scene_id}-choice"))
                lines.extend([f"### CHOICE `{choice_id}`", ""])
                for index, option in enumerate(item.get("options") or [], 1):
                    counts["options"] += 1
                    ref = f"{choice_id}-O{index}"
                    if ref in review_ids:
                        raise ValueError(f"duplicate review ID: {ref}")
                    review_ids.add(ref)
                    lines.append(f"- [{ref}] {option.get('text', '')} -> `{option.get('target', '')}`; state={json.dumps(option.get('state') or {}, ensure_ascii=False, separators=(',', ':'))}")
                lines.append("")
            elif kind == "jump":
                lines.extend([f"**JUMP** -> `{item.get('target', '')}`", ""])
            elif kind == "awaitInput":
                lines.extend(["**AWAIT INPUT**", ""])
            elif kind == "routeEnding":
                lines.extend(["**ROUTE ENDING**", ""])
            elif kind == "returnLogo":
                lines.extend(["**RETURN LOGO / RESET**", ""])
            else:
                lines.extend([f"**COMMAND `{kind or 'unknown'}`**", "", *fenced_json(item), ""])
        lines.extend(["---", ""])
    counts["reviewIds"] = len(review_ids)
    return lines, counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Export stable-ID Markdown for independent Japanese dialogue review.")
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--bible", type=Path, required=True)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    brief, bible, scenario = load(args.brief), load(args.bible), load(args.scenario)
    validate_graph(scenario)
    source = args.scenario.read_bytes()
    sha = hashlib.sha256(source).hexdigest()
    args.out.mkdir(parents=True, exist_ok=True)
    dump(args.out / "01_concept.md", concept_markdown(brief, sha))
    dump(args.out / "02_character_settings.md", characters_markdown(bible, sha))
    script, counts = script_markdown(scenario, bible, sha)
    dump(args.out / "03_scenario_script.md", script)
    manifest = {"formatVersion": 1, "scenarioSha256": sha, "counts": counts, "files": ["01_concept.md", "02_character_settings.md", "03_scenario_script.md"]}
    (args.out / "review-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "scenarioSha256": sha, **counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
