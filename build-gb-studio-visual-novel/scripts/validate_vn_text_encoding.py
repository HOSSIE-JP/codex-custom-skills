#!/usr/bin/env python3
"""Validate VN font pages, inline tags, and compiled GB Studio text bytes."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc


FIRST_FONT_CODE = 32
RESERVED_CODES = {0x25, 0x5C}
INLINE_TAG = re.compile(r"^!F:([0-9a-fA-F-]{36})!")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def speaker_label_format(
    manifest: dict[str, Any], failures: list[str]
) -> str | None:
    runtime = manifest.get("dialogueRuntime") or {}
    presentation = manifest.get("dialoguePresentation") or {}
    value = runtime.get("speakerLabelFormat", presentation.get("speakerLabelFormat"))
    if value is None:
        return None
    if not isinstance(value, str):
        failures.append("speakerLabelFormat must be a string")
        return None
    if "\n" in value or value.count("{speaker}") != 1:
        failures.append(
            "speakerLabelFormat must be one line with exactly one {speaker} token"
        )
        return None
    try:
        value.format(speaker="話者")
    except (KeyError, ValueError) as exc:
        failures.append(f"invalid speakerLabelFormat: {exc}")
        return None
    return value


def walk_events(events: list[dict[str, Any]]):
    for event in events:
        yield event
        children = event.get("children") or {}
        if isinstance(children, dict):
            for branch in children.values():
                if isinstance(branch, list):
                    yield from walk_events(branch)


def parse_asm_string(value: str) -> bytes:
    output = bytearray()
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            code = ord(char)
            if code > 255:
                raise ValueError(f"non-byte assembler character U+{code:04X}")
            output.append(code)
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise ValueError("trailing backslash")
        char = value[index]
        if char in "01234567":
            end = index
            while end < len(value) and end < index + 3 and value[end] in "01234567":
                end += 1
            output.append(int(value[index:end], 8))
            index = end
            continue
        escapes = {"n": 10, "r": 13, "t": 9, "\\": 92, '"': 34}
        if char not in escapes:
            raise ValueError(f"unsupported escape \\{char}")
        output.append(escapes[char])
        index += 1
    return bytes(output)


def asm_blobs(build_dir: Path) -> list[bytes]:
    data_dir = build_dir / "src" / "data"
    paths = sorted(data_dir.glob("scene_*.s"))
    if not paths:
        raise FileNotFoundError(f"no compiled scene_*.s files under {data_dir}")
    blobs: list[bytes] = []
    pattern = re.compile(r'^\s*\.asciz "(.*)"\s*$')
    for path in paths:
        for line in path.read_text(
            encoding="utf-8", errors="surrogateescape"
        ).splitlines():
            match = pattern.match(line)
            if not match:
                continue
            try:
                blobs.append(parse_asm_string(match.group(1)))
            except (ValueError, UnicodeEncodeError):
                continue
    return blobs


def encode_text(text: str, mapping: dict[str, int]) -> bytes:
    output = bytearray()
    for char in text:
        if char == "\n":
            output.append(10)
            continue
        if char not in mapping:
            raise ValueError(f"unmapped character {char!r} U+{ord(char):04X}")
        code = int(mapping[char])
        if code < FIRST_FONT_CODE or code > 255:
            raise ValueError(f"mapped character uses non-printable code {code}: {char!r}")
        if code in RESERVED_CODES:
            raise ValueError(f"mapped character uses reserved code 0x{code:02X}: {char!r}")
        output.append(code)
    return bytes(output)


def reserved_tile_is_blank(image: Image.Image, code: int) -> bool:
    tile_index = code - FIRST_FONT_CODE
    left = (tile_index % 16) * 8
    top = (tile_index // 16) * 8
    return all(
        image.getpixel((x, y)) == 3
        for y in range(top, top + 8)
        for x in range(left, left + 8)
    )


def load_font_pages(
    manifest: dict[str, Any], font_root: Path, failures: list[str]
) -> tuple[dict[int, dict[str, Any]], dict[str, int], bool]:
    records = manifest.get("fontPages")
    if not isinstance(records, list) or not records:
        failures.append("manifest fontPages must be a non-empty array")
        return {}, {}, False

    pages: dict[int, dict[str, Any]] = {}
    font_id_to_page: dict[str, int] = {}
    used_fallback_index = False
    for record in records:
        try:
            page = int(record["page"])
            font_id = str(record["fontId"])
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"invalid font page record: {exc}")
            continue
        if page in pages:
            failures.append(f"duplicate font page {page}")
            continue
        if font_id in font_id_to_page:
            failures.append(f"duplicate font resource id {font_id}")
            continue

        mapping_path = font_root / f"page_{page}.json"
        resource_path = font_root / f"page_{page}.png.gbsres"
        png_path = font_root / f"page_{page}.png"
        try:
            mapping_raw = load_json(mapping_path).get("mapping")
            resource = load_json(resource_path)
        except Exception as exc:
            failures.append(f"font page {page} cannot be loaded: {exc}")
            continue
        if not isinstance(mapping_raw, dict):
            failures.append(f"font page {page} mapping is not an object")
            continue

        mapping: dict[str, int] = {}
        codes: list[int] = []
        for character, raw_code in mapping_raw.items():
            try:
                code = int(raw_code)
            except (TypeError, ValueError):
                failures.append(f"font page {page} has invalid code for {character!r}")
                continue
            if not isinstance(character, str) or len(character) != 1:
                failures.append(f"font page {page} has non-character key {character!r}")
                continue
            if code < FIRST_FONT_CODE or code > 255 or code in RESERVED_CODES:
                failures.append(
                    f"font page {page} maps {character!r} to unsafe code 0x{code:02X}"
                )
            mapping[character] = code
            codes.append(code)
        if len(codes) != len(set(codes)):
            failures.append(f"font page {page} reuses a byte code")
        if len(mapping) > 222:
            failures.append(f"font page {page} maps {len(mapping)} glyphs; maximum is 222")
        if resource.get("id") != font_id:
            failures.append(
                f"font page {page} resource id mismatch: manifest={font_id}, "
                f"resource={resource.get('id')}"
            )

        try:
            image = Image.open(png_path)
            if image.mode != "P" or image.size != (128, 112):
                failures.append(
                    f"font page {page} PNG must be indexed 128x112, "
                    f"found mode={image.mode} size={image.size}"
                )
            else:
                for code in sorted(RESERVED_CODES):
                    if not reserved_tile_is_blank(image, code):
                        failures.append(
                            f"font page {page} reserved physical tile 0x{code:02X} is not blank"
                        )
        except Exception as exc:
            failures.append(f"font page {page} PNG cannot be checked: {exc}")

        compiled_index_raw = record.get("compiledFontIndex")
        if compiled_index_raw is None:
            compiled_index = page + 1
            used_fallback_index = True
        else:
            try:
                compiled_index = int(compiled_index_raw)
            except (TypeError, ValueError):
                failures.append(f"font page {page} has invalid compiledFontIndex")
                continue
        if not 0 <= compiled_index <= 255:
            failures.append(f"font page {page} compiledFontIndex is outside byte range")

        pages[page] = {
            "font_id": font_id,
            "mapping": mapping,
            "compiled_index": compiled_index,
        }
        font_id_to_page[font_id] = page
    return pages, font_id_to_page, used_fallback_index


def load_project_events(
    project_root: Path, failures: list[str]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scene_paths = sorted((project_root / "project" / "scenes").rglob("scene.gbsres"))
    if not scene_paths:
        failures.append("no project/scenes/**/scene.gbsres files found")
        return {}, [], []

    events: dict[str, dict[str, Any]] = {}
    choices: list[dict[str, Any]] = []
    draws: list[dict[str, Any]] = []
    for path in scene_paths:
        try:
            scene = load_json(path)
        except Exception as exc:
            failures.append(f"cannot load scene {path}: {exc}")
            continue
        for event in walk_events(scene.get("script") or []):
            event_id = event.get("id")
            if isinstance(event_id, str) and event_id:
                if event_id in events:
                    failures.append(f"duplicate event id {event_id}")
                events[event_id] = event
            if event.get("command") == "EVENT_CHOICE":
                choices.append(event)
            elif event.get("command") == "EVENT_TEXT_DRAW":
                draws.append(event)
    return events, choices, draws


def validate(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.resolve()
    manifest_path = resolve(project_root, args.manifest)
    font_root = resolve(project_root, args.font_root)
    build_dir = resolve(project_root, args.build_dir)
    manifest = load_json(manifest_path)
    failures: list[str] = []
    label_format = speaker_label_format(manifest, failures)

    pages, font_id_to_page, used_fallback_index = load_font_pages(
        manifest, font_root, failures
    )
    events, choices, draws = load_project_events(project_root, failures)

    expected_blobs: Counter[bytes] = Counter()
    tagged_messages = 0
    speaker_labels_validated = 0
    narration_messages_validated = 0
    message_records = manifest.get("messages") or []
    if not isinstance(message_records, list):
        failures.append("manifest messages must be an array")
        message_records = []

    for record in message_records:
        try:
            event_id = str(record["eventId"])
            visible_expected = str(record["generatedText"])
            page = int(record["fontPage"])
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"invalid message manifest record: {exc}")
            continue
        if label_format is not None:
            if "speaker" not in record or "sourceText" not in record:
                failures.append(
                    f"message {event_id} lacks speaker/sourceText for label validation"
                )
            else:
                speaker = str(record.get("speaker", ""))
                source_text = str(record.get("sourceText", ""))
                policy_text = (
                    f"{label_format.format(speaker=speaker)}\n{source_text}"
                    if speaker
                    else source_text
                )
                if visible_expected != policy_text:
                    failures.append(
                        f"speaker label policy mismatch for event {event_id}"
                    )
                elif speaker:
                    speaker_labels_validated += 1
                else:
                    narration_messages_validated += 1
        if page not in pages:
            failures.append(f"message {event_id} references missing font page {page}")
            continue
        event = events.get(event_id)
        if event is None:
            failures.append(f"missing message event {event_id}")
            continue
        text = (event.get("args") or {}).get("text", "")
        tag = f"!F:{pages[page]['font_id']}!"
        if not isinstance(text, str) or not text.startswith(tag):
            failures.append(f"message {event_id} lacks expected inline font tag")
            continue
        visible = text[len(tag) :]
        if visible != visible_expected:
            failures.append(f"visible message mismatch for event {event_id}")
            continue
        try:
            encoded = encode_text(visible, pages[page]["mapping"])
        except ValueError as exc:
            failures.append(f"message {event_id}: {exc}")
            continue
        expected_blobs[
            bytes((2, pages[page]["compiled_index"])) + encoded
        ] += 1
        tagged_messages += 1

    tagged_choice_labels = 0
    for event in choices:
        event_args = event.get("args") or {}
        choice_pages: set[int] = set()
        for key in ("trueText", "falseText"):
            text = event_args.get(key, "")
            match = INLINE_TAG.match(text) if isinstance(text, str) else None
            if not match or match.group(1) not in font_id_to_page:
                failures.append(f"choice {event.get('id')} {key} lacks a valid font tag")
                continue
            page = font_id_to_page[match.group(1)]
            choice_pages.add(page)
            try:
                encode_text(text[match.end() :], pages[page]["mapping"])
            except ValueError as exc:
                failures.append(f"choice {event.get('id')} {key}: {exc}")
                continue
            tagged_choice_labels += 1
        if len(choice_pages) > 1:
            failures.append(
                f"choice {event.get('id')} labels use different font pages: "
                f"{sorted(choice_pages)}"
            )

    tagged_draws = 0
    for event in draws:
        text = (event.get("args") or {}).get("text", "")
        if not isinstance(text, str) or not text.strip():
            continue
        match = INLINE_TAG.match(text)
        if not match or match.group(1) not in font_id_to_page:
            failures.append(f"SpriteText {event.get('id')} lacks a valid font tag")
            continue
        page = font_id_to_page[match.group(1)]
        try:
            encode_text(text[match.end() :], pages[page]["mapping"])
        except ValueError as exc:
            failures.append(f"SpriteText {event.get('id')}: {exc}")
            continue
        tagged_draws += 1

    statistics = manifest.get("statistics") or {}
    if "messages" in statistics and int(statistics["messages"]) != tagged_messages:
        failures.append(
            f"message count mismatch: expected {statistics['messages']}, found {tagged_messages}"
        )
    if "choices" in statistics and int(statistics["choices"]) != len(choices):
        failures.append(
            f"choice count mismatch: expected {statistics['choices']}, found {len(choices)}"
        )

    try:
        actual_blobs = Counter(asm_blobs(build_dir))
    except Exception as exc:
        failures.append(str(exc))
        actual_blobs = Counter()
    missing_compiled = expected_blobs - actual_blobs
    if missing_compiled:
        failures.append(
            f"{sum(missing_compiled.values())} compiled dialogue byte sequences "
            "do not match their selected font page"
        )

    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "taggedMessages": tagged_messages,
        "speakerLabelFormat": label_format,
        "speakerLabelsValidated": speaker_labels_validated,
        "narrationMessagesValidated": narration_messages_validated,
        "choiceEvents": len(choices),
        "taggedChoiceLabels": tagged_choice_labels,
        "taggedSpriteTexts": tagged_draws,
        "compiledDialogueSequences": sum(expected_blobs.values()),
        "compiledDialogueMatches": sum((expected_blobs & actual_blobs).values()),
        "fontPages": len(pages),
        "compiledFontIndexFallback": "page+1" if used_fallback_index else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate VN font pages, inline tags, and compiled GB Studio text."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--font-root", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    try:
        result = validate(parse_args())
    except Exception as exc:
        result = {"status": "fail", "failures": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
