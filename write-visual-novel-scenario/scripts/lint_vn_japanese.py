from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from validate_vn_scenario import validate_pack
from vn_common import ValidationError, contained, dump_json, load_json, source_hashes, source_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint Japanese VN text without claiming naturalness.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--authoring-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Treat warnings as blocking")
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True)
        paths = source_paths(root, args.authoring_dir)
        report_path = contained(root, args.report)
        data = {name: load_json(path) for name, path in paths.items()}
        structural = validate_pack(data)
        script, bible, rules = data["script.json"], data["character-bible.json"], data["language-rules.json"]
        issues: list[dict[str, str]] = []

        def issue(severity: str, unit: str, rule: str, detail: str) -> None:
            issues.append({"severity": severity, "unit": unit, "rule": rule, "detail": detail})

        characters = {str(item.get("id")): item for item in bible.get("characters") or [] if isinstance(item, dict)}
        patterns: list[tuple[re.Pattern[str], str]] = []
        for item in rules.get("aiLikePatterns") or []:
            try:
                patterns.append((re.compile(str(item.get("pattern", ""))), str(item.get("detail", "review wording"))))
            except re.error as exc:
                issue("error", "language-rules.json", "invalid-regex", str(exc))
        max_chars = rules.get("maxVisibleCharacters")
        occurrences: dict[str, list[str]] = defaultdict(list)
        visible: list[tuple[str, str, str]] = []
        for scene in script.get("scenes") or []:
            for entry in scene.get("entries") or []:
                if entry.get("type") == "line":
                    visible.append((str(entry.get("id")), str(entry.get("speaker")), str(entry.get("text", ""))))
                elif entry.get("type") == "choice":
                    if str(entry.get("prompt", "")).strip():
                        visible.append((str(entry.get("id")) + ":prompt", "", str(entry.get("prompt"))))
                    for option in entry.get("options") or []:
                        visible.append((str(option.get("id")), "", str(option.get("text", ""))))
        for unit, speaker, text in visible:
            if text != unicodedata.normalize("NFC", text):
                issue("error", unit, "unicode-normalization", "text must be NFC")
            if text != text.strip() or re.search(r"[ \t]+(?=\n|$)", text):
                issue("error", unit, "whitespace", "leading/trailing whitespace is not allowed")
            if "replace-with" in text or re.search(r"(?:TODO|TBD|仮文|ここに.*記述)", text, re.IGNORECASE):
                issue("error", unit, "placeholder", "draft placeholder remains")
            if isinstance(max_chars, int) and max_chars > 0 and len(text) > max_chars:
                issue("warning", unit, "visible-length", f"{len(text)} characters exceeds configured {max_chars}")
            if re.search(r"[、。！？!?]{3,}", text):
                issue("warning", unit, "punctuation", "three or more consecutive punctuation marks")
            for item in rules.get("awkwardPhrases") or []:
                phrase = str(item.get("phrase", ""))
                if phrase and phrase in text:
                    issue(str(item.get("severity", "warning")), unit, "awkward-phrase", f"{phrase}: {item.get('suggestion', 'review')}")
            for pattern, detail in patterns:
                if pattern.search(text):
                    issue("warning", unit, "ai-like-language", detail)
            character = characters.get(speaker)
            if character:
                voice = character.get("voice") if isinstance(character.get("voice"), dict) else {}
                for phrase in voice.get("discouragedPhrases") or []:
                    if str(phrase) and str(phrase) in text:
                        issue("warning", unit, "character-voice", f"discouraged for {speaker}: {phrase}")
                for phrase in voice.get("forbiddenFirstPerson") or []:
                    if re.search(rf"(?<![一-龠々ぁ-んァ-ン]){re.escape(str(phrase))}(?=(?:は|が|も|を|の|、|。|！|？|$))", text):
                        issue("warning", unit, "first-person", f"forbidden for {speaker}: {phrase}")
            for sentence in re.findall(r"[^。！？!?\n]+[。！？!?]?", text):
                normalized = unicodedata.normalize("NFC", sentence).strip()
                if len(normalized) >= int(rules.get("repeatedSentenceMinCharacters", 12)):
                    occurrences[normalized].append(unit)
        threshold = int(rules.get("repeatedSentenceThreshold", 3))
        for sentence, units in occurrences.items():
            if len(units) >= threshold:
                issue("warning", units[0], "repeated-sentence", f"same sentence appears in {len(units)} units: {units}")

        structural_errors = [item for item in structural["issues"] if item["severity"] == "error"]
        for item in structural_errors:
            issue("error", item["location"], "structural-prerequisite", item["detail"])
        errors = [item for item in issues if item["severity"] == "error"]
        warnings = [item for item in issues if item["severity"] == "warning"]
        blocking = bool(errors or (args.strict and warnings))
        hashes, aggregate = source_hashes(paths)
        report = {
            "status": "fail" if blocking else "pass",
            "strict": args.strict,
            "automatedNaturalnessClaim": False,
            "manualNaturalnessReviewRequired": True,
            "sourceSha256": hashes,
            "sourceAggregateSha256": aggregate,
            "statistics": {"textUnits": len(visible), "errors": len(errors), "warnings": len(warnings)},
            "issues": issues,
        }
        dump_json(report_path, report)
        print(json.dumps({"status": report["status"], **report["statistics"]}, ensure_ascii=False))
        if blocking:
            raise SystemExit(1)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
