"""Add an in-game "staff interview" bonus scene on top of an already
menu-shelled PCE scene document (see apply_pce_menu_shell.py).

Every ending scene produced by apply_pce_menu_shell.py's ending_trailer()
ends in a fixed 4-command tail: wait -> effect(fadeOut) -> audio(stop) ->
jump(sceneId == doc["startScene"]). This script finds ending scenes by that
shape alone, so it does not depend on menu-shell-config.json (most
already-built projects in this series do not keep that file around). For
each ending scene found it:

1. moves the ending's trailer into a new `<ending_id>_finish` scene;
2. appends a `choice` command to the ending scene offering "view the staff
   interview" (-> the shared interview scene) or "return to title" (->
   `<ending_id>_finish`, which just replays the original trailer);
3. builds one or more chained `scene_staff_interview`[`_N`] scenes parsed
   from `source/staff-interview.md` (see references/staff-interview.md for
   the fixed 8-question format this expects), reusing the selector scene's
   own title background so no new image asset is required, and ending on
   the same trailer shape. The interview is paginated across scenes to stay
   within the PCE VN engine's 8192-byte-per-scene-pack limit -- a single
   scene routinely can't hold all eight answers' worth of message commands.

Standing rule: see SKILL.md. Run only after apply_pce_menu_shell.py, and
only when the project has `source/staff-interview.md`. Because this adds
new dialogue content, re-run scripts/scan_text_budget.js and the real CD
preflight/build afterward -- free-form interview prose can contain JIS
Level-2 kanji the System Card jp-v3 font does not cover; fix flagged
characters in staff-interview.md itself and re-run this script.

Usage:
  python apply_pce_staff_interview.py --scenes <pce-vn-scenes.json> \
      --markdown <source/staff-interview.md> --out <pce-vn-scenes.json> \
      [--force]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from pce_vn_common import ValidationError, load_json, write_json


# Message window is 208px wide / 16px tall x 4 lines; SpriteText/message glyphs
# are VN_GLYPH_W=12px wide, so 208/12 ~= 17 characters per line. The real
# per-message cap enforced at build time is 68 display entries (characters
# plus one entry per literal '\n'), not a flat 17*4 -- see
# references/text-and-font-limits.md.
LINE_WIDTH = 17
MAX_LINES = 4
DISPLAY_BUDGET = 68

CHOICE_VIEW_LABEL = "スタッフインタビューを見る"
CHOICE_BACK_LABEL = "タイトルに戻る"
STAFF_INTERVIEW_SCENE_ID = "scene_staff_interview"

# PCE VN scene packs (pce-vn-scene-pack.js's createVnScenePackCodec) have a
# hard 8192-byte cache limit per scene -- exceeding it is a build-blocking
# error ('PCE VN scene pack "..." is N bytes; split the scene to stay within
# 8192 bytes'). A single-scene staff interview with ~8 questions' worth of
# message commands routinely exceeds this (confirmed against real projects
# in this series), so the interview must be paginated across multiple
# chained scenes. The byte formula below is an exact match to the real
# encoder, verified against real generated scenes byte-for-byte:
#   pack_bytes = headerSize(20)
#              + command_count * commandSize(19)
#              + message_count * messageSize(13)
#              + sum(2 * (len(text) + 1) for each message)   # null-terminated
#                                                             # 2-byte glyph words
SCENE_PACK_HEADER_SIZE = 20
SCENE_PACK_COMMAND_SIZE = 19
SCENE_PACK_MESSAGE_SIZE = 13
SCENE_PACK_BYTE_LIMIT = 8192
# Reserve room for the largest possible non-message overhead a single page
# could carry (header + a background command + the 4-command return-to-title
# trailer, i.e. the degenerate single-page case) plus a safety margin, so the
# per-page message budget below is correct regardless of which page (first,
# middle, last) ends up holding how many messages.
_INTERVIEW_PAGE_RESERVED_BYTES = (
    SCENE_PACK_HEADER_SIZE
    + SCENE_PACK_COMMAND_SIZE  # background (first page only)
    + 4 * SCENE_PACK_COMMAND_SIZE  # return-to-title trailer (last page only)
    + 150  # safety margin
)
INTERVIEW_PAGE_MESSAGE_BUDGET = SCENE_PACK_BYTE_LIMIT - _INTERVIEW_PAGE_RESERVED_BYTES


def _message_pack_bytes(text: str) -> int:
    return SCENE_PACK_COMMAND_SIZE + SCENE_PACK_MESSAGE_SIZE + 2 * (len(text) + 1)


def paginate_messages(message_texts: list[str], budget: int = INTERVIEW_PAGE_MESSAGE_BUDGET) -> list[list[str]]:
    """Group message bodies into pages whose total scene-pack byte cost each
    stays within `budget`, without splitting any single message across
    pages. Every individual message is far smaller than one page's budget
    (capped at 68 display entries by pack_text_into_messages), so this never
    has to hard-split a single message."""
    pages: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0
    for text in message_texts:
        cost = _message_pack_bytes(text)
        if current and current_bytes + cost > budget:
            pages.append(current)
            current = []
            current_bytes = 0
        current.append(text)
        current_bytes += cost
    if current:
        pages.append(current)
    return pages


def _interview_page_scene_id(index: int) -> str:
    return STAFF_INTERVIEW_SCENE_ID if index == 0 else f"{STAFF_INTERVIEW_SCENE_ID}_{index + 1}"

_TRAILER_TYPES = ("wait", "effect", "audio", "jump")


def _is_trailer(commands: list[Any], selector_id: str) -> bool:
    if len(commands) < 4:
        return False
    tail = commands[-4:]
    if [c.get("type") for c in tail] != list(_TRAILER_TYPES):
        return False
    return (
        tail[1].get("effect") == "fadeOut"
        and tail[2].get("action") == "stop"
        and tail[3].get("sceneId") == selector_id
    )


def find_ending_scenes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    selector_id = doc.get("startScene")
    if not selector_id:
        raise ValidationError("scenes document has no startScene")
    scenes = doc.get("scenes")
    if not isinstance(scenes, list):
        raise ValidationError("scenes document must have a scenes array")
    endings = [
        scene
        for scene in scenes
        if isinstance(scene, dict)
        and isinstance(scene.get("commands"), list)
        and _is_trailer(scene["commands"], selector_id)
    ]
    if not endings:
        raise ValidationError(
            "no ending scene found with the apply_pce_menu_shell.py trailer shape "
            "(wait / effect:fadeOut / audio:stop / jump-to-selector); run apply_pce_menu_shell.py first"
        )
    return endings


# The fixed eight-question set from references/staff-interview.md. Anchoring
# on this exact, verbatim text (rather than a markdown-decoration pattern) is
# deliberate: across the series' already-written staff-interview.md files,
# the same eight questions have been decorated three different ways --
# '**N. question**' (bold), '## N. question', and '## question' (heading,
# no leading number) -- but the question text itself is always identical.
STAFF_INTERVIEW_QUESTIONS = [
    "今回のゲームでは、どんな仕事を担当しましたか？",
    "自分の担当で、一番見てほしいところはどこですか？",
    "制作中、一番苦労したことは何でしたか？",
    "人間のディレクターについて、率直にどんな印象を持ちましたか？",
    "この機会だから言っておきたい愚痴はありますか？",
    "完成したゲームを見て、今どう感じていますか？",
    "もし次回作があるなら、何をやってみたいですか？",
    "最後に、ここまで遊んでくれたプレイヤーへ一言お願いします。",
]


def _heading_pattern(question: str) -> re.Pattern[str]:
    return re.compile(
        r"^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*[ \t]*)?(?:\d+[.．][ \t]*)?"
        + re.escape(question)
        + r"[ \t]*(?:\*\*)?[ \t]*$",
        re.MULTILINE,
    )


def parse_staff_interview_markdown(text: str) -> list[tuple[str, str]]:
    """Locate the fixed eight-question set verbatim in `text`, tolerant of
    how each heading happens to be decorated (see `_heading_pattern`), and
    split the text between consecutive headings into (question, answer)
    pairs."""
    anchors: list[tuple[int, str, re.Match[str]]] = []
    for number, question in enumerate(STAFF_INTERVIEW_QUESTIONS, start=1):
        match = _heading_pattern(question).search(text)
        if not match:
            raise ValidationError(
                f"question {number} heading not found verbatim in staff-interview markdown: {question!r}"
            )
        anchors.append((number, question, match))
    pairs: list[tuple[str, str]] = []
    for index, (number, question, match) in enumerate(anchors):
        start = match.end()
        end = anchors[index + 1][2].start() if index + 1 < len(anchors) else len(text)
        answer = re.sub(r"\n{2,}", "\n", text[start:end].strip())
        if not answer:
            raise ValidationError(f"question {number} has no answer text")
        pairs.append((f"Q{number} {question}", answer))
    return pairs


_CLAUSE_RE = re.compile(r"[^。、]*[。、]|[^。、]+$")


def _clauses(text: str) -> list[str]:
    return [c for c in _CLAUSE_RE.findall(text) if c]


def _wrap_clause(clause: str, width: int) -> list[str]:
    return [clause[i:i + width] for i in range(0, len(clause), width)]


def _entries(lines: list[str]) -> int:
    """Display-budget cost of `lines` joined by '\\n': characters + one entry
    per line break, matching encodeSystemCardText's counting rule."""
    if not lines:
        return 0
    return sum(len(line) for line in lines) + (len(lines) - 1)


def pack_text_into_messages(
    text: str,
    line_width: int = LINE_WIDTH,
    max_lines: int = MAX_LINES,
    budget: int = DISPLAY_BUDGET,
) -> list[str]:
    """Greedily pack `text` into one or more message-command bodies. Each
    body is at most `max_lines` lines of at most `line_width` characters,
    manually '\\n'-joined (there is no automatic line-wrapping anywhere in
    the real pipeline -- see references/text-and-font-limits.md), and each
    body's total display-budget cost stays within `budget`. Prefers to break
    at sentence (。) / clause (、) boundaries; only hard-wraps a clause that
    is itself longer than one line."""
    pieces: list[str] = []
    for clause in _clauses(text.replace("\n", "")):
        if len(clause) <= line_width:
            pieces.append(clause)
        else:
            pieces.extend(_wrap_clause(clause, line_width))

    messages: list[str] = []
    lines: list[str] = []
    current = ""

    def close_message(committed_lines: list[str]) -> None:
        if committed_lines:
            messages.append("\n".join(committed_lines))

    for piece in pieces:
        joined = current + piece
        if len(joined) <= line_width:
            current = joined
            continue
        # `current` is a finished line (pieces are never empty, so current is
        # always non-empty by the time we get here). Try to commit it into
        # the message being built; if there's no room left, close that
        # message out with just what was already committed and start a new
        # message with `current` as its first line -- never drop it.
        candidate_lines = lines + [current]
        if len(candidate_lines) <= max_lines and _entries(candidate_lines) <= budget:
            lines = candidate_lines
            current = piece
        else:
            close_message(lines)
            lines = [current]
            current = piece

    final_lines = lines + ([current] if current else [])
    if final_lines and len(final_lines) <= max_lines and _entries(final_lines) <= budget:
        close_message(final_lines)
    else:
        close_message(lines)
        if current:
            close_message([current])

    return [m for m in messages if m]


def _message(text: str) -> dict[str, Any]:
    return {"type": "message", "speaker": "", "text": text, "textColor": "", "voiceAssetId": "", "mouthSlot": None}


def _messages_for(text: str) -> list[dict[str, Any]]:
    return [_message(body) for body in pack_text_into_messages(text)]


def _selector_background_asset_id(doc: dict[str, Any], selector_id: str) -> str:
    scenes = {s["id"]: s for s in doc["scenes"] if isinstance(s, dict) and "id" in s}
    selector = scenes.get(selector_id)
    if not selector:
        raise ValidationError(f"selector scene not found: {selector_id}")
    for command in selector.get("commands", []):
        if command.get("type") == "background" and command.get("assetId"):
            return command["assetId"]
    raise ValidationError(f"selector scene {selector_id} has no background command to reuse for the staff interview")


def build_interview_scenes(
    qa_pairs: list[tuple[str, str]],
    background_asset_id: str,
    trailer: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the staff-interview scene(s). The eight Q&A pairs are flattened
    into one ordered stream of message bodies and paginated by
    `paginate_messages` to stay within the 8192-byte PCE VN scene-pack limit
    (a single scene routinely doesn't fit ~8 questions' worth of answers --
    see the byte-budget comment above `SCENE_PACK_HEADER_SIZE`). Pages are
    chained with plain `jump` commands; only the first page shows the
    background (it persists across the jump, so repeating it would just
    spend bytes for no visual effect), and only the last page carries the
    return-to-title trailer."""
    all_texts: list[str] = []
    for question, answer in qa_pairs:
        all_texts.extend(pack_text_into_messages(question))
        all_texts.extend(pack_text_into_messages(answer))

    pages = paginate_messages(all_texts)
    scenes: list[dict[str, Any]] = []
    for index, page_texts in enumerate(pages):
        commands: list[dict[str, Any]] = []
        if index == 0:
            commands.append({"type": "background", "assetId": background_asset_id, "transition": "fade", "fadeOutFrames": 30, "fadeInFrames": 30, "x": 2, "y": 1})
        commands.extend(_message(t) for t in page_texts)
        if index + 1 < len(pages):
            commands.append({"type": "jump", "sceneId": _interview_page_scene_id(index + 1)})
        else:
            commands.extend(trailer)
        scenes.append({
            "id": _interview_page_scene_id(index),
            "name": "スタッフインタビュー" if len(pages) == 1 else f"スタッフインタビュー/{index + 1}",
            "fullScreenBg": False,
            "commands": commands,
            "nextSceneId": "",
        })
    return scenes


def apply_staff_interview(scenes_doc: dict[str, Any], markdown_text: str) -> dict[str, Any]:
    scenes = scenes_doc.get("scenes")
    if not isinstance(scenes, list):
        raise ValidationError("scenes document must have a scenes array")
    existing_ids = {scene["id"] for scene in scenes if isinstance(scene, dict) and "id" in scene}
    if STAFF_INTERVIEW_SCENE_ID in existing_ids:
        raise ValidationError("staff interview bonus already applied: scene_staff_interview already exists")

    selector_id = scenes_doc["startScene"]
    ending_scenes = find_ending_scenes(scenes_doc)
    qa_pairs = parse_staff_interview_markdown(markdown_text)
    background_asset_id = _selector_background_asset_id(scenes_doc, selector_id)

    new_scenes: list[dict[str, Any]] = []
    shared_trailer: list[dict[str, Any]] | None = None
    for ending in ending_scenes:
        trailer = ending["commands"][-4:]
        shared_trailer = shared_trailer or trailer
        finish_id = f"{ending['id']}_finish"
        if finish_id in existing_ids:
            raise ValidationError(f"refusing to overwrite existing scene: {finish_id}")
        existing_ids.add(finish_id)
        ending["commands"] = ending["commands"][:-4] + [{
            "type": "choice",
            "choices": [
                {"label": CHOICE_VIEW_LABEL, "value": 0, "targetSceneId": STAFF_INTERVIEW_SCENE_ID},
                {"label": CHOICE_BACK_LABEL, "value": 1, "targetSceneId": finish_id},
            ],
            "defaultIndex": 0,
        }]
        new_scenes.append({
            "id": finish_id,
            "name": f"{ending['id']}/finish",
            "fullScreenBg": False,
            "commands": trailer,
            "nextSceneId": "",
        })

    assert shared_trailer is not None
    interview_scenes = build_interview_scenes(qa_pairs, background_asset_id, shared_trailer)
    for scene in interview_scenes:
        if scene["id"] in existing_ids:
            raise ValidationError(f"refusing to overwrite existing scene: {scene['id']}")
        existing_ids.add(scene["id"])
    new_scenes.extend(interview_scenes)

    scenes_doc = dict(scenes_doc)
    scenes_doc["scenes"] = list(scenes) + new_scenes
    return scenes_doc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add a staff-interview bonus scene (a view/return-to-title choice at every ending) "
        "to an already menu-shelled PCE scene document."
    )
    parser.add_argument("--scenes", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        scenes_doc = load_json(args.scenes)
        try:
            markdown_text = args.markdown.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValidationError(f"cannot read markdown file {args.markdown}: {exc}") from exc
        result = apply_staff_interview(scenes_doc, markdown_text)
        write_json(args.out, result, args.force)
        print(f"OK: {len(result['scenes'])} scenes, staff interview scene id={STAFF_INTERVIEW_SCENE_ID!r}")
    except ValidationError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
