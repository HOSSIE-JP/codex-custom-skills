from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

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
