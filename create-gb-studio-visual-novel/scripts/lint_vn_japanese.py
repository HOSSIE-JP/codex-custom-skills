from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class TextRecord:
    unit: str
    scene: str
    phase: str
    speaker: str
    text: str
    kind: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def conclusion_key(text: str) -> str:
    value = unicodedata.normalize("NFC", text).strip()
    value = re.sub(r"^(?:つまり|要するに|結局|だから)[、,:：\s]*", "", value)
    value = re.sub(r"[、。！？!?…・\s]+", "", value)
    return value if len(value) >= 8 else ""


def issue(issues: list[dict[str, str]], severity: str, unit: str, rule: str, detail: str) -> None:
    issues.append({"severity": severity, "unit": unit, "rule": rule, "detail": detail})


def iter_records(scenario: dict[str, Any], issues: list[dict[str, str]], required_variants: set[str]) -> Iterable[TextRecord]:
    for scene_index, scene in enumerate(scenario.get("scenes", [])):
        scene_id = str(scene.get("id", f"scene:{scene_index}"))
        phase = str(scene.get("revealPhase", ""))
        for command_index, command in enumerate(scene.get("script", [])):
            command_type = command.get("type")
            base = f"{scene_id}:{command_index}"
            if command_type == "message":
                yield TextRecord(base, scene_id, phase, str(command.get("speaker", "")), str(command.get("text", "")), "message")
            elif command_type == "genderMessages":
                variants = command.get("variants") or {}
                variant_keys = set(map(str, variants))
                if variant_keys != required_variants:
                    issue(issues, "error", base, "gender-coverage", f"expected {sorted(required_variants)}, found {sorted(variant_keys)}")
                for variant, messages in variants.items():
                    if not messages:
                        issue(issues, "error", f"{base}:variant:{variant}", "gender-empty", "variant must contain at least one message")
                    for message_index, message in enumerate(messages or []):
                        yield TextRecord(
                            f"{base}:variant:{variant}:{message_index}", scene_id, phase,
                            str(message.get("speaker", "")), str(message.get("text", "")), "genderVariant",
                        )
            elif command_type == "choice":
                options = command.get("options") or []
                if len(options) < 2:
                    issue(issues, "error", base, "choice-count", "a choice needs at least two options")
                for option_index, option in enumerate(options):
                    option_unit = f"{base}:option:{option_index}"
                    if not option.get("target"):
                        issue(issues, "error", option_unit, "choice-target", "choice option needs a target")
                    yield TextRecord(option_unit, scene_id, phase, "", str(option.get("text", "")), "choice")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint normalized Japanese VN source without claiming semantic naturalness.")
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--bible", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Fail warnings as well as errors")
    args = parser.parse_args()

    scenario = load_json(args.scenario)
    bible = load_json(args.bible)
    rules = load_json(args.rules)
    issues: list[dict[str, str]] = []

    scenes = scenario.get("scenes") or []
    scene_ids = [str(scene.get("id", "")) for scene in scenes]
    if not scenes or any(not scene_id for scene_id in scene_ids):
        issue(issues, "error", "scenario", "scene-id", "every scenario needs non-empty scene IDs")
    if len(scene_ids) != len(set(scene_ids)):
        issue(issues, "error", "scenario", "duplicate-scene", "scene IDs must be unique")
    if scenario.get("initialScene") not in set(scene_ids):
        issue(issues, "error", "scenario", "initial-scene", "initialScene must reference an existing scene")
    reveal_scene_id = str(rules.get("revealSceneId", ""))
    if reveal_scene_id and reveal_scene_id not in set(scene_ids):
        issue(issues, "error", "language-rules", "reveal-scene", f"unknown revealSceneId: {reveal_scene_id}")
    elif reveal_scene_id:
        reveal_scene = scenes[scene_ids.index(reveal_scene_id)]
        if reveal_scene.get("revealPhase") != "reveal":
            issue(issues, "error", reveal_scene_id, "reveal-phase", "revealSceneId must use revealPhase=reveal")

    required_variants = set(map(str, rules.get("requiredGenderVariants") or []))
    records = list(iter_records(scenario, issues, required_variants))
    allowed_speakers = set(map(str, rules.get("allowedSpeakers") or []))
    characters = {str(item.get("id")): item for item in bible.get("characters", [])}

    for scene_index, scene in enumerate(scenes):
        scene_id = scene_ids[scene_index]
        for command_index, command in enumerate(scene.get("script", [])):
            if command.get("type") == "jump" and command.get("target") not in set(scene_ids):
                issue(issues, "error", f"{scene_id}:{command_index}", "jump-target", str(command.get("target")))
            if command.get("type") == "choice":
                for option_index, option in enumerate(command.get("options") or []):
                    if option.get("target") not in set(scene_ids):
                        issue(issues, "error", f"{scene_id}:{command_index}:option:{option_index}", "choice-target", str(option.get("target")))

    compiled_patterns: list[tuple[re.Pattern[str], str]] = []
    for item in rules.get("aiLikePatterns") or []:
        try:
            compiled_patterns.append((re.compile(str(item["pattern"])), str(item.get("detail", item["pattern"]))))
        except re.error as exc:
            issue(issues, "error", "language-rules", "invalid-regex", f"{item.get('pattern')}: {exc}")

    previous: TextRecord | None = None
    recent_conclusions: dict[str, list[tuple[str, str]]] = {}
    for record in records:
        text = record.text
        if not text:
            issue(issues, "error", record.unit, "empty-text", "visible text must not be empty")
            continue
        if record.speaker not in allowed_speakers:
            issue(issues, "error", record.unit, "speaker", f"unknown or disallowed speaker: {record.speaker}")
        if record.speaker and record.speaker not in characters:
            issue(issues, "error", record.unit, "character-bible", f"speaker missing from bible: {record.speaker}")
        if text != unicodedata.normalize("NFC", text):
            issue(issues, "error", record.unit, "unicode-nfc", "normalize visible text to NFC")
        if text != text.strip() or any(line != line.rstrip() for line in text.splitlines()):
            issue(issues, "error", record.unit, "whitespace", "remove leading/trailing and line-end whitespace")
        if re.search(r"[、。！？!?]{3,}", text):
            issue(issues, "warning", record.unit, "punctuation", "three or more consecutive punctuation marks")

        for item in rules.get("awkwardPhrases") or []:
            phrase = str(item.get("phrase", ""))
            if phrase and phrase in text:
                issue(issues, str(item.get("severity", "warning")), record.unit, "awkward-phrase", f"{phrase} -> {item.get('suggestion', 'review')}")
        for pattern, detail in compiled_patterns:
            if pattern.search(text):
                issue(issues, "warning", record.unit, "ai-like-language", detail)
        key = conclusion_key(text)
        recent = recent_conclusions.setdefault(record.scene, [])
        if key:
            for previous_unit, previous_key in recent[-3:]:
                if key == previous_key:
                    issue(issues, "warning", record.unit, "repeated-conclusion", f"repeats the conclusion of {previous_unit}")
                    break
            recent.append((record.unit, key))
        if record.phase == "preReveal":
            for spoiler in rules.get("preRevealSpoilerTerms") or []:
                if str(spoiler) and str(spoiler) in text:
                    issue(issues, "error", record.unit, "twist-spoiler", str(spoiler))

        character = characters.get(record.speaker)
        if character:
            voice = character.get("voice") or {}
            for phrase in voice.get("discouragedPhrases") or []:
                if str(phrase) in text:
                    issue(issues, "warning", record.unit, "character-voice", f"discouraged for {record.speaker}: {phrase}")
            if record.kind != "genderVariant":
                for pronoun in voice.get("forbiddenFirstPerson") or []:
                    pattern = rf"(?<![一-龠々ぁ-んァ-ン]){re.escape(str(pronoun))}(?=(?:は|が|も|なら|って|を|の|、|。|！|？|$))"
                    if re.search(pattern, text):
                        issue(issues, "warning", record.unit, "first-person", f"{record.speaker} uses forbidden first-person form: {pronoun}")

        if previous and previous.speaker == record.speaker and previous.text == text:
            issue(issues, "warning", record.unit, "duplicate-line", f"duplicates {previous.unit}")
        previous = record

    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    blocking = bool(errors or (args.strict and warnings))
    manual_names = list(map(str, rules.get("manualReviewNames") or ["readAloud", "characterVoice", "exposition", "branchJoins"]))
    report = {
        "status": "fail" if blocking else "pass",
        "strict": args.strict,
        "automatedNaturalnessClaim": False,
        "statistics": {"scenes": len(scenes), "textUnits": len(records), "errors": len(errors), "warnings": len(warnings)},
        "manualReview": {name: {"status": "required", "note": ""} for name in manual_names},
        "issues": issues,
    }
    write_json(args.report, report)
    print(json.dumps({"status": report["status"], **report["statistics"]}, ensure_ascii=False))
    if blocking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
