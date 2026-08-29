from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from apply_pce_menu_shell import apply_menu_shell  # noqa: E402
from apply_pce_staff_interview import (  # noqa: E402
    INTERVIEW_PAGE_MESSAGE_BUDGET,
    SCENE_PACK_BYTE_LIMIT,
    SCENE_PACK_COMMAND_SIZE,
    SCENE_PACK_HEADER_SIZE,
    SCENE_PACK_MESSAGE_SIZE,
    STAFF_INTERVIEW_QUESTIONS,
    apply_staff_interview,
    find_ending_scenes,
    pack_text_into_messages,
    paginate_messages,
    parse_staff_interview_markdown,
)


def real_scene_pack_bytes(commands: list[dict]) -> int:
    """Reimplements pce-vn-scene-pack.js's byte formula independently of the
    script under test, for end-to-end verification that a generated scene
    actually stays within the engine's real 8192-byte scene-pack limit."""
    message_count = sum(1 for c in commands if c.get("type") == "message")
    total = SCENE_PACK_HEADER_SIZE + len(commands) * SCENE_PACK_COMMAND_SIZE + message_count * SCENE_PACK_MESSAGE_SIZE
    for c in commands:
        if c.get("type") == "message":
            total += 2 * (len(c.get("text", "")) + 1)
    return total
from build_integration_manifest import build_manifest  # noqa: E402
from emit_pce_scenes import cue_mapping, emit  # noqa: E402
from migrate_pce_v2 import migrate  # noqa: E402
from pack_sprite_sheet import pack  # noqa: E402
from pce_vn_common import ValidationError, canonical_json_bytes, load_shared_pack, sha256_file, shared_modules  # noqa: E402


def shared_script(status: str = "APPROVED") -> dict:
    return {
        "formatVersion": 2, "projectId": "project.test", "revision": 1, "status": status, "startSceneId": "scene.opening",
        "stateVariables": [{"id": "state.route", "type": "integer", "initial": 0}],
        "cues": [{"id": "cue.opening.bg", "kind": "visual", "emotion": "期待", "narrativePurpose": "場所を示す", "characters": ["aki"], "visibleContent": "夕暮れの屋上", "musicFunction": "導入", "playbackIntent": "start"}],
        "scenes": [
            {"id": "scene.opening", "summary": "分岐", "entries": [
                {"id": "cueentry.opening.bg", "type": "cue", "cueId": "cue.opening.bg"},
                {"id": "line.opening.ask", "type": "line", "speaker": "aki", "text": "どちらへ行く？"},
                {"id": "stateentry.opening.route", "type": "state", "variableId": "state.route", "operation": "set", "value": 0},
                {"id": "choice.opening.route", "type": "choice", "options": [
                    {"id": "option.opening.good", "text": "進む", "targetSceneId": "scene.good", "setState": {"state.route": 1}},
                    {"id": "option.opening.bad", "text": "戻る", "targetSceneId": "scene.bad", "setState": {"state.route": 2}},
                ]},
            ]},
            {"id": "scene.good", "summary": "進む", "entries": [{"id": "line.good.go", "type": "line", "speaker": "aki", "text": "進もう。"}, {"id": "jump.good.final", "type": "jump", "targetSceneId": "scene.final"}]},
            {"id": "scene.bad", "summary": "悪い結末", "entries": [{"id": "line.bad.back", "type": "line", "speaker": "aki", "text": "戻ろう。"}]},
            {"id": "scene.final", "summary": "良い結末", "entries": [{"id": "line.final.arrive", "type": "line", "speaker": "aki", "text": "着いた。"}]},
        ],
        "endings": [{"id": "ending.good", "title": "到着", "sceneId": "scene.final"}, {"id": "ending.bad", "title": "帰還", "sceneId": "scene.bad"}],
    }


def full_pack(script: dict | None = None, approved: bool = True) -> dict:
    script = script or shared_script("APPROVED" if approved else "REVIEW_REQUIRED")
    status = "APPROVED" if approved else "REVIEW_REQUIRED"
    characters = [{"id": "aki", "displayName": "アキ", "ageCategory": "成人", "role": "主人公", "desire": "進む", "obstacle": "迷い"}]
    return {
        "project-brief.json": {"formatVersion": 2, "projectId": script["projectId"], "title": "test", "language": "ja", "branching": {"choiceCount": 1, "endingCount": 2, "choiceHistoryCount": 2, "stateVariables": [{"id": "state.route"}]}, "externalReview": {"status": "complete", "externalTransmissionApproved": False}},
        "character-bible.json": {"formatVersion": 2, "projectId": script["projectId"], "characters": characters},
        "scenario-design.json": {"formatVersion": 2, "projectId": script["projectId"], "revision": 1, "status": status, "approvedRevision": 1 if approved else None},
        "script.json": script,
        "language-rules.json": {"formatVersion": 2, "allowedSpeakers": ["aki", "narrator"]},
        "self-review.json": {"formatVersion": 2, "status": "complete", "passes": {name: {"status": "complete", "evidence": "checked", "revisions": ["no change"], "remainingConcerns": []} for name in ("mechanical", "readAloud", "characterVoice", "expositionAndBranchJoins")}},
    }


def write_pack(root: Path, data: dict) -> Path:
    authoring = root / "source" / "vn-authoring"; authoring.mkdir(parents=True)
    for name, value in data.items(): (authoring / name).write_bytes(canonical_json_bytes(value))
    return authoring


def valid_cue_map() -> dict:
    return {"formatVersion": 1, "cues": [{"cueId": "cue.opening.bg", "commands": [{"type": "background", "assetId": "roof_bg", "transition": "fade", "x": 2, "y": 1}]}]}


class IntegrationTests(unittest.TestCase):
    def test_full_pack_gate_and_exact_emission(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_pack(root, full_pack())
            data, report, aggregate, _ = load_shared_pack(root, require_approved=True)
            scenes, source_map, consumption = emit(data["script.json"], cue_mapping(valid_cue_map()), {"aki": "アキ"}, aggregate)
            self.assertEqual(report["status"], "pass"); self.assertEqual(consumption["expected"], consumption["consumed"])
            self.assertEqual(source_map["sharedSourceAggregateSha256"], aggregate)
            self.assertEqual(next(c for c in scenes["scenes"][0]["commands"] if c["type"] == "message")["speaker"], "アキ")

    def test_scene_name_breadcrumb_is_opt_in_and_strips_scene_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_pack(root, full_pack())
            data, _, aggregate, _ = load_shared_pack(root, require_approved=True)
            scenes_default, _, _ = emit(data["script.json"], cue_mapping(valid_cue_map()), {"aki": "アキ"}, aggregate)
            self.assertNotIn("name", scenes_default["scenes"][0])
            scenes_named, _, _ = emit(data["script.json"], cue_mapping(valid_cue_map()), {"aki": "アキ"}, aggregate, "01_test")
            opening = next(s for s in scenes_named["scenes"] if s["id"] == "scene_opening")
            self.assertEqual(opening["name"], "01_test/opening")
            self.assertEqual(opening["id"], "scene_opening")

    def test_unknown_command_and_conditional_choice_rejected(self) -> None:
        bad = valid_cue_map(); bad["cues"][0]["commands"] = [{"type": "future"}]
        with self.assertRaises(ValidationError): cue_mapping(bad)
        script = shared_script(); script["scenes"][0]["entries"][-1]["options"][0]["when"] = {"variableId": "state.route", "equals": 0}
        with self.assertRaises(ValidationError): emit(script, cue_mapping(valid_cue_map()))

    def test_migration_output_is_canonical_schema_valid_with_review_fixture(self) -> None:
        source = {"version": 2, "startScene": "Opening Scene", "scenes": [
            {"id": "Opening Scene", "commands": [{"type": "background", "assetId": "roof_bg"}, {"type": "message", "speaker": "アキ", "text": "行こう。"}, {"type": "jump", "sceneId": "Ending Scene"}]},
            {"id": "Ending Scene", "commands": [{"type": "message", "speaker": "", "text": "終"}]},
        ]}
        script, mapping, report = migrate(source, "a" * 64, "project.migrated")
        self.assertEqual(script["formatVersion"], 2); self.assertIsInstance(script["revision"], int)
        self.assertEqual(mapping["cues"][0]["commands"][0]["assetId"], "roof_bg"); self.assertNotIn("assetId", script["cues"][0])
        characters = report["suggestedCharacters"]
        data = {"project-brief.json": {"formatVersion": 2, "projectId": "project.migrated", "title": "m", "language": "ja", "branching": {"choiceCount": 0, "endingCount": 1, "choiceHistoryCount": 1, "stateVariables": []}, "externalReview": {"status": "pending-user-decision", "externalTransmissionApproved": False}}, "character-bible.json": {"formatVersion": 2, "projectId": "project.migrated", "characters": characters}, "scenario-design.json": {"formatVersion": 2, "projectId": "project.migrated", "revision": 1, "status": "REVIEW_REQUIRED", "approvedRevision": None}, "script.json": script, "language-rules.json": {"formatVersion": 2, "allowedSpeakers": sorted(["narrator", *[item["id"] for item in characters]])}, "self-review.json": {"formatVersion": 2}}
        _, validator, _ = shared_modules(); validation = validator.validate_pack(data, require_approved=False)
        self.assertEqual(validation["status"], "pass", validation["issues"])

    def test_manifest_proves_aggregate_and_all_shared_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); write_pack(root, full_pack())
            data, report, aggregate, _ = load_shared_pack(root, require_approved=True)
            validation_path = root / "validation.json"; validation_path.write_bytes(canonical_json_bytes({"status": "pass", "approved": True, "sourceAggregateSha256": aggregate}))
            scenes, source_map, consumption = emit(data["script.json"], cue_mapping(valid_cue_map()), {"aki": "アキ"}, aggregate)
            scene_path = root / "scenes.json"; scene_path.write_bytes(canonical_json_bytes(scenes))
            source_map_path = root / "source-map.json"; source_map_path.write_bytes(canonical_json_bytes(source_map))
            cue_path = root / "cue-map.json"; cue_path.write_bytes(canonical_json_bytes(valid_cue_map()))
            asset_path = root / "asset-map.json"; asset_path.write_bytes(canonical_json_bytes({"formatVersion": 1, "assets": [{"sharedCueId": "cue.opening.bg", "pceAssetId": "roof_bg"}]}))
            consumption_path = root / "consumption.json"; consumption_path.write_bytes(canonical_json_bytes(consumption))
            generated = root / "game.cue"; generated.write_bytes(b"cue")
            manifest = build_manifest(root, validation_path, scene_path, source_map_path, cue_path, asset_path, consumption_path, [generated], "cd", root, None)
            self.assertEqual(manifest["sharedSourceAggregateSha256"], aggregate); self.assertEqual(manifest["sharedIntegrationValidation"]["status"], "pass")
            stale = copy.deepcopy(consumption); stale["sharedSourceAggregateSha256"] = "0" * 64; consumption_path.write_bytes(canonical_json_bytes(stale))
            with self.assertRaisesRegex(ValidationError, "stale"): build_manifest(root, validation_path, scene_path, source_map_path, cue_path, asset_path, consumption_path, [], "cd", root, None)


class MenuShellTests(unittest.TestCase):
    def menu_shell_fixture(self) -> tuple[dict, dict]:
        scenes_doc = {
            "version": 2, "settings": {}, "startScene": "scene_opening",
            "scenes": [
                {"id": "scene_opening", "fullScreenBg": False, "commands": [{"type": "message", "speaker": "", "text": "はじまり。"}], "nextSceneId": "scene_ending_good"},
                {"id": "scene_ending_good", "fullScreenBg": False, "commands": [{"type": "message", "speaker": "", "text": "おわり。"}], "nextSceneId": ""},
            ],
        }
        config = {"formatVersion": 1, "scenarios": [{
            "selectorId": "01_test", "slug": "01_test", "displayName": "テスト編",
            "titleBgAssetId": "bg_test_title", "startSceneId": "scene_opening", "endingSceneIds": ["scene_ending_good"],
        }]}
        return scenes_doc, config

    def test_single_scenario_self_loops_and_tail_is_appended_in_order(self) -> None:
        scenes_doc, config = self.menu_shell_fixture()
        result = apply_menu_shell(scenes_doc, config)
        self.assertEqual(len(result["scenes"]), 3)
        self.assertEqual(result["startScene"], "01_test")
        selector = next(s for s in result["scenes"] if s["id"] == "01_test")
        self.assertEqual(selector["name"], "シナリオ選択/01_test_テスト編")
        title_spritetext = next(c for c in selector["commands"] if c.get("type") == "spritetext" and c.get("slot") == 1)
        self.assertEqual(title_spritetext["text"], "テスト編")
        self.assertEqual(title_spritetext["x"], 104)  # (256 - 12*4) // 2, centered for a 4-glyph title
        next_jump = next(c for i, c in enumerate(selector["commands"]) if c.get("type") == "label" and c["name"] == "NEXT_SCR")
        self.assertEqual(selector["commands"][selector["commands"].index(next_jump) + 1], {"type": "jump", "sceneId": "01_test"})
        prev_label_index = next(i for i, c in enumerate(selector["commands"]) if c.get("type") == "label" and c["name"] == "PREV_SCR")
        self.assertEqual(selector["commands"][prev_label_index + 1], {"type": "jump", "sceneId": "01_test"})
        ending = next(s for s in result["scenes"] if s["id"] == "scene_ending_good")
        self.assertEqual(ending["commands"][-4:], [
            {"type": "wait", "frames": 240},
            {"type": "effect", "effect": "fadeOut", "frames": 90, "intensity": 0, "color": "#000000"},
            {"type": "audio", "kind": "psg", "action": "stop", "assetId": "", "channel": 0, "target": "bgm"},
            {"type": "jump", "sceneId": "01_test"},
        ])

    def test_title_spritetext_x_centers_by_display_name_length(self) -> None:
        scenes_doc, config = self.menu_shell_fixture()
        config["scenarios"][0]["displayName"] = "百物語の夜"  # 5 glyphs
        result = apply_menu_shell(scenes_doc, config)
        selector = next(s for s in result["scenes"] if s["id"] == "01_test")
        title_spritetext = next(c for c in selector["commands"] if c.get("type") == "spritetext" and c.get("slot") == 1)
        self.assertEqual(title_spritetext["x"], 98)  # (256 - 12*5) // 2

    def test_rejects_ending_scene_id_not_present_in_scenes_document(self) -> None:
        scenes_doc, config = self.menu_shell_fixture()
        config["scenarios"][0]["endingSceneIds"].append("scene_missing")
        with self.assertRaises(ValidationError):
            apply_menu_shell(scenes_doc, config)

    def test_rejects_selector_id_colliding_with_an_existing_scene(self) -> None:
        scenes_doc, config = self.menu_shell_fixture()
        config["scenarios"][0]["selectorId"] = "scene_opening"
        with self.assertRaises(ValidationError):
            apply_menu_shell(scenes_doc, config)

    def test_rejects_double_apply_against_an_already_shelled_ending(self) -> None:
        scenes_doc, config = self.menu_shell_fixture()
        once = apply_menu_shell(scenes_doc, config)
        with self.assertRaises(ValidationError):
            apply_menu_shell(once, config)


# Mirrors the three decoration styles actually found across the series'
# already-written staff-interview.md files: '**N. question**' (bold, used by
# 001), '## N. question' (heading+number, used by most), and '## question'
# (heading, no leading number, used by a few) -- the parser must tolerate
# all three since it is applied retroactively to existing files.
SAMPLE_MARKDOWN = """# AIスタッフインタビュー

**対象作品**: テスト作品

---

**1. 今回のゲームでは、どんな仕事を担当しましたか？**

短い回答です。

## 2. 自分の担当で、一番見てほしいところはどこですか？

ここも短い回答です。

## 制作中、一番苦労したことは何でしたか？

これは十七文字を超える一文になるように書かれた長めの回答です。読点も、途中に、いくつか含めています。そして二つ目の文もここに続きます。

## 人間のディレクターについて、率直にどんな印象を持ちましたか？

好印象でした。

## この機会だから言っておきたい愚痴はありますか？

特にありません。

## 完成したゲームを見て、今どう感じていますか？

満足しています。

## もし次回作があるなら、何をやってみたいですか？

新しい構成に挑戦したいです。

## 最後に、ここまで遊んでくれたプレイヤーへ一言お願いします。

ありがとうございました。
"""


class StaffInterviewMarkdownTests(unittest.TestCase):
    def test_parses_all_eight_fixed_questions_across_mixed_decoration_styles(self) -> None:
        pairs = parse_staff_interview_markdown(SAMPLE_MARKDOWN)
        self.assertEqual(len(pairs), 8)
        self.assertEqual(pairs[0], ("Q1 今回のゲームでは、どんな仕事を担当しましたか？", "短い回答です。"))
        self.assertEqual(pairs[1][0], "Q2 自分の担当で、一番見てほしいところはどこですか？")
        self.assertIn("読点も", pairs[2][1])
        self.assertEqual(pairs[7][0], "Q8 最後に、ここまで遊んでくれたプレイヤーへ一言お願いします。")
        self.assertEqual(pairs[7][1], "ありがとうございました。")

    def test_rejects_markdown_with_no_question_headings(self) -> None:
        with self.assertRaises(ValidationError):
            parse_staff_interview_markdown("ただの文章で見出しがありません。")

    def test_rejects_when_last_question_has_no_answer_text(self) -> None:
        truncated = SAMPLE_MARKDOWN.rsplit("ありがとうございました。", 1)[0]
        with self.assertRaises(ValidationError):
            parse_staff_interview_markdown(truncated)


class StaffInterviewPackingTests(unittest.TestCase):
    def _assert_within_budget(self, messages: list[str]) -> None:
        for body in messages:
            lines = body.split("\n")
            self.assertLessEqual(len(lines), 4)
            for line in lines:
                self.assertLessEqual(len(line), 17)
            self.assertLessEqual(sum(len(line) for line in lines) + (len(lines) - 1), 68)

    def test_short_text_fits_on_a_single_line_with_no_wrap(self) -> None:
        messages = pack_text_into_messages("短い回答です。")
        self.assertEqual(messages, ["短い回答です。"])

    def test_text_longer_than_one_line_wraps_within_one_message(self) -> None:
        text = "これは十七文字を超える一文になるように書かれた回答です。"
        messages = pack_text_into_messages(text)
        self.assertEqual(len(messages), 1)
        self.assertIn("\n", messages[0])
        self._assert_within_budget(messages)
        self.assertEqual(messages[0].replace("\n", ""), text)

    def test_long_answer_spans_multiple_messages_and_preserves_all_text(self) -> None:
        text = "。".join(f"これは{n}番目の短い文です" for n in range(1, 30)) + "。"
        messages = pack_text_into_messages(text)
        self.assertGreater(len(messages), 1)
        self._assert_within_budget(messages)
        self.assertEqual("".join(m.replace("\n", "") for m in messages), text)

    def test_single_sentence_with_no_punctuation_still_hard_wraps_safely(self) -> None:
        text = "あ" * 130  # no 。/、 anywhere, forces the hard-wrap fallback
        messages = pack_text_into_messages(text)
        self._assert_within_budget(messages)
        self.assertEqual("".join(m.replace("\n", "") for m in messages), text)


class StaffInterviewPaginationTests(unittest.TestCase):
    def test_small_message_set_fits_on_a_single_page(self) -> None:
        pages = paginate_messages(["短い回答です。", "もう一つ短い回答。"])
        self.assertEqual(pages, [["短い回答です。", "もう一つ短い回答。"]])

    def test_no_page_exceeds_the_message_budget_and_no_message_is_lost(self) -> None:
        # Near-max-length (68-entry) messages, enough of them that a single
        # PCE VN scene pack (8192-byte hard limit) cannot hold them all --
        # this is the exact shape of bug that slipped through when the whole
        # interview was written into one scene (confirmed against real
        # projects in this series: a ~70-message interview reached
        # 9800-10900 bytes against the 8192 limit).
        messages = [("これは" + "あ" * 60 + f"{n:03d}。") for n in range(80)]
        pages = paginate_messages(messages)
        self.assertGreater(len(pages), 1, "fixture should be large enough to force a split")
        for page in pages:
            page_bytes = sum(SCENE_PACK_COMMAND_SIZE + SCENE_PACK_MESSAGE_SIZE + 2 * (len(m) + 1) for m in page)
            self.assertLessEqual(page_bytes, INTERVIEW_PAGE_MESSAGE_BUDGET)
        # No message dropped, duplicated, or reordered across the split.
        self.assertEqual([m for page in pages for m in page], messages)


class StaffInterviewApplyTests(unittest.TestCase):
    def _menu_shelled_doc(self, ending_count: int = 1) -> dict:
        scenes = [{"id": "scene_opening", "fullScreenBg": False, "commands": [{"type": "message", "speaker": "", "text": "はじまり。"}], "nextSceneId": "scene_ending_1"}]
        ending_ids = [f"scene_ending_{n}" for n in range(1, ending_count + 1)]
        for i, ending_id in enumerate(ending_ids):
            scenes.append({"id": ending_id, "fullScreenBg": False, "commands": [{"type": "message", "speaker": "", "text": f"結末{i + 1}。"}], "nextSceneId": ""})
        scenes_doc = {"version": 2, "settings": {}, "startScene": "scene_opening", "scenes": scenes}
        config = {"formatVersion": 1, "scenarios": [{
            "selectorId": "01_test", "slug": "01_test", "displayName": "テスト編",
            "titleBgAssetId": "bg_test_title", "startSceneId": "scene_opening", "endingSceneIds": ending_ids,
        }]}
        return apply_menu_shell(scenes_doc, config)

    def test_find_ending_scenes_matches_only_the_real_trailer_shape(self) -> None:
        doc = self._menu_shelled_doc(ending_count=1)
        endings = find_ending_scenes(doc)
        self.assertEqual([s["id"] for s in endings], ["scene_ending_1"])
        # A scene that merely ends in a 'jump' (but not the full 4-command
        # trailer) must not be mistaken for an ending.
        doc["scenes"].append({"id": "scene_decoy", "fullScreenBg": False, "commands": [{"type": "jump", "sceneId": "01_test"}], "nextSceneId": ""})
        endings_after = find_ending_scenes(doc)
        self.assertEqual([s["id"] for s in endings_after], ["scene_ending_1"])

    def test_single_ending_gets_choice_and_shared_interview_scene(self) -> None:
        doc = self._menu_shelled_doc(ending_count=1)
        result = apply_staff_interview(doc, SAMPLE_MARKDOWN)
        ending = next(s for s in result["scenes"] if s["id"] == "scene_ending_1")
        self.assertEqual(ending["commands"][-1], {
            "type": "choice",
            "choices": [
                {"label": "スタッフインタビューを見る", "value": 0, "targetSceneId": "scene_staff_interview"},
                {"label": "タイトルに戻る", "value": 1, "targetSceneId": "scene_ending_1_finish"},
            ],
            "defaultIndex": 0,
        })
        finish = next(s for s in result["scenes"] if s["id"] == "scene_ending_1_finish")
        self.assertEqual(finish["commands"], [
            {"type": "wait", "frames": 240},
            {"type": "effect", "effect": "fadeOut", "frames": 90, "intensity": 0, "color": "#000000"},
            {"type": "audio", "kind": "psg", "action": "stop", "assetId": "", "channel": 0, "target": "bgm"},
            {"type": "jump", "sceneId": "01_test"},
        ])
        interview = next(s for s in result["scenes"] if s["id"] == "scene_staff_interview")
        self.assertEqual(interview["commands"][0], {"type": "background", "assetId": "bg_test_title", "transition": "fade", "fadeOutFrames": 30, "fadeInFrames": 30, "x": 2, "y": 1})
        self.assertEqual(interview["commands"][-1], {"type": "jump", "sceneId": "01_test"})
        self.assertTrue(any(c.get("type") == "message" and "短い回答です" in c.get("text", "") for c in interview["commands"]))

    def test_three_endings_all_get_the_choice_and_share_one_interview_scene(self) -> None:
        doc = self._menu_shelled_doc(ending_count=3)
        result = apply_staff_interview(doc, SAMPLE_MARKDOWN)
        for n in (1, 2, 3):
            ending = next(s for s in result["scenes"] if s["id"] == f"scene_ending_{n}")
            self.assertEqual(ending["commands"][-1]["type"], "choice")
            self.assertEqual(ending["commands"][-1]["choices"][0]["targetSceneId"], "scene_staff_interview")
        interview_scenes = [s for s in result["scenes"] if s["id"] == "scene_staff_interview"]
        self.assertEqual(len(interview_scenes), 1)

    def test_long_transcript_is_paginated_across_scene_pack_safe_scenes(self) -> None:
        # Reproduces the real bug: a single staff-interview.md with realistic
        # (not toy-short) answers to all eight questions produced one scene
        # exceeding the engine's 8192-byte scene-pack limit for 10 of the 18
        # real projects in this series (up to ~10900 bytes). Build a
        # comparably long transcript here rather than depending on any real
        # project's file.
        long_answer = "。".join(f"これは長い回答の{n}番目の文です" for n in range(1, 40)) + "。"
        questions = list(STAFF_INTERVIEW_QUESTIONS)
        long_markdown = "# AIスタッフインタビュー\n\n" + "".join(
            f"## {n}. {q}\n\n{long_answer}\n\n" for n, q in enumerate(questions, start=1)
        )
        doc = self._menu_shelled_doc(ending_count=1)
        result = apply_staff_interview(doc, long_markdown)

        interview_pages = [s for s in result["scenes"] if s["id"].startswith("scene_staff_interview")]
        self.assertGreater(len(interview_pages), 1, "fixture should be long enough to force pagination")
        interview_pages.sort(key=lambda s: s["id"])  # scene_staff_interview, _2, _3, ... sorts correctly as text too since <10 pages

        for page in interview_pages:
            self.assertLessEqual(real_scene_pack_bytes(page["commands"]), SCENE_PACK_BYTE_LIMIT)

        # First page carries the background; later pages don't repeat it.
        self.assertEqual(interview_pages[0]["commands"][0]["type"], "background")
        for page in interview_pages[1:]:
            self.assertNotEqual(page["commands"][0]["type"], "background")

        # Every non-final page ends by jumping straight to the next page;
        # the final page ends on the standard return-to-title trailer.
        expected_ids = [s["id"] for s in interview_pages]
        for page, next_id in zip(interview_pages[:-1], expected_ids[1:]):
            self.assertEqual(page["commands"][-1], {"type": "jump", "sceneId": next_id})
        self.assertEqual(interview_pages[-1]["commands"][-1], {"type": "jump", "sceneId": "01_test"})

        # The ending's choice still targets page 1 specifically.
        ending = next(s for s in result["scenes"] if s["id"] == "scene_ending_1")
        self.assertEqual(ending["commands"][-1]["choices"][0]["targetSceneId"], "scene_staff_interview")

    def test_rejects_double_apply(self) -> None:
        doc = self._menu_shelled_doc(ending_count=1)
        once = apply_staff_interview(doc, SAMPLE_MARKDOWN)
        with self.assertRaises(ValidationError):
            apply_staff_interview(once, SAMPLE_MARKDOWN)

    def test_rejects_when_no_ending_scene_is_present(self) -> None:
        scenes_doc = {"version": 2, "settings": {}, "startScene": "01_test", "scenes": [
            {"id": "01_test", "fullScreenBg": False, "commands": [{"type": "background", "assetId": "bg_test_title", "transition": "fade", "x": 2, "y": 1}], "nextSceneId": ""},
        ]}
        with self.assertRaises(ValidationError):
            apply_staff_interview(scenes_doc, SAMPLE_MARKDOWN)


class SpriteTests(unittest.TestCase):
    def test_sprite_pack_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name, color in (("normal.png", (255, 0, 0, 255)), ("mouth.png", (0, 255, 0, 255))):
                image = Image.new("RGBA", (17, 31), (0, 0, 0, 0)); image.putpixel((1, 1), color); image.save(root / name)
            spec = {"cellSize": 16, "rows": [{"id": "default", "kind": "normal", "pairId": "talk", "frames": ["normal.png"]}, {"id": "mouth", "kind": "mouth", "pairId": "talk", "frames": ["mouth.png"]}]}
            spec_path = root / "spec.json"; spec_path.write_bytes(canonical_json_bytes(spec)); sheet = root / "sheet.png"; meta = root / "sheet.json"
            metadata = pack(spec_path, sheet, meta); digest = sha256_file(sheet); pack(spec_path, sheet, meta, force=True)
            self.assertEqual(digest, sha256_file(sheet)); self.assertEqual(metadata["rows"][1]["firstCell"], 4)


if __name__ == "__main__": unittest.main()
