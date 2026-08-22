from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict: return json.loads(path.read_text(encoding="utf-8"))


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name); self.pack = self.root / "source" / "vn-authoring"

    def tearDown(self) -> None: self.temp.cleanup()

    def run_tool(self, name: str, *args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPTS / name), *map(str, args)]
        result = subprocess.run(command, cwd=SCRIPTS, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(expected, result.returncode, msg=f"{command}\nstdout={result.stdout}\nstderr={result.stderr}"); return result

    def scaffold(self) -> None: self.run_tool("scaffold_vn_authoring.py", "--project-root", self.root, "--out", self.pack)

    def approve_valid_pack(self) -> None:
        self.scaffold()
        for name in ("project-brief.json", "character-bible.json", "scenario-design.json", "script.json"):
            value = read_json(self.pack / name); value["projectId"] = "test-project"; write_json(self.pack / name, value)
        design = read_json(self.pack / "scenario-design.json"); design.update({"status": "APPROVED", "approvedRevision": 1}); write_json(self.pack / "scenario-design.json", design)
        script = read_json(self.pack / "script.json"); script["status"] = "APPROVED"; script["scenes"][0]["entries"][0]["text"] = "雨の音が、少し近くなった。"; write_json(self.pack / "script.json", script)
        review = read_json(self.pack / "self-review.json"); review["status"] = "complete"
        for name, value in review["passes"].items(): value.update({"status": "complete", "evidence": f"{name}を全行確認した。", "revisions": ["変更不要の箇所も含めて確認記録を固定した。"]})
        write_json(self.pack / "self-review.json", review)

    def validate(self, expected: int = 0, name: str = "validation.json") -> dict:
        report = self.pack / name
        self.run_tool("validate_vn_scenario.py", "--project-root", self.root, "--authoring-dir", self.pack, "--report", report, expected=expected)
        return read_json(report)

    def test_scaffold_collision_and_root_containment(self) -> None:
        self.scaffold(); self.assertEqual(6, len(list(self.pack.glob("*.json"))))
        self.run_tool("scaffold_vn_authoring.py", "--project-root", self.root, "--out", self.pack, expected=2)
        self.run_tool("scaffold_vn_authoring.py", "--project-root", self.root, "--out", self.root.parent / "escape-pack", expected=2)

    def test_export_all_input_hash_and_stale_correction(self) -> None:
        self.approve_valid_pack(); validation = self.validate(); self.assertEqual(1, validation["statistics"]["choiceHistoryCount"])
        review_out = self.root / "source" / "external-review"
        self.run_tool("export_vn_review_pack.py", "--project-root", self.root, "--authoring-dir", self.pack, "--out", review_out)
        manifest = read_json(review_out / "review-manifest.json"); self.assertEqual(6, len(manifest["sourceFiles"])); self.assertEqual({"01_concept.md", "02_character_settings.md", "03_scenario_script.md"}, set(manifest["files"]))
        correction = self.root / "correction.json"; write_json(correction, {"formatVersion": 1, "sourceAggregateSha256": manifest["sourceAggregateSha256"], "edits": [{"id": "line.start.opening", "field": "text", "before": "雨の音が、少し近くなった。", "after": "雨音が、さっきより近い。", "reason": "音読時のリズム"}]})
        self.run_tool("apply_review_corrections.py", "--project-root", self.root, "--authoring-dir", self.pack, "--manifest", review_out / "review-manifest.json", "--corrections", correction)
        self.assertEqual("雨音が、さっきより近い。", read_json(self.pack / "script.json")["scenes"][0]["entries"][0]["text"])
        self.run_tool("apply_review_corrections.py", "--project-root", self.root, "--authoring-dir", self.pack, "--manifest", review_out / "review-manifest.json", "--corrections", correction, expected=2)

    def test_asymmetric_branch_history_count_is_path_sum(self) -> None:
        self.approve_valid_pack(); script = read_json(self.pack / "script.json")
        script["startSceneId"] = "scene.start"
        script["scenes"] = [
            {"id": "scene.start", "summary": "first", "entries": [{"type": "choice", "id": "choice.first", "options": [{"id": "option.first.a", "text": "A", "targetSceneId": "scene.end.a"}, {"id": "option.first.b", "text": "B", "targetSceneId": "scene.branch"}]}]},
            {"id": "scene.branch", "summary": "second", "entries": [{"type": "choice", "id": "choice.second", "options": [{"id": "option.second.a", "text": "C", "targetSceneId": "scene.end.b"}, {"id": "option.second.b", "text": "D", "targetSceneId": "scene.end.c"}]}]},
            {"id": "scene.end.a", "summary": "A end", "entries": [{"type": "line", "id": "line.end.a", "speaker": "narrator", "text": "Aの結末。"}]},
            {"id": "scene.end.b", "summary": "B end", "entries": [{"type": "line", "id": "line.end.b", "speaker": "narrator", "text": "Bの結末。"}]},
            {"id": "scene.end.c", "summary": "C end", "entries": [{"type": "line", "id": "line.end.c", "speaker": "narrator", "text": "Cの結末。"}]},
        ]
        script["endings"] = [{"id": "ending.a", "title": "A", "sceneId": "scene.end.a"}, {"id": "ending.b", "title": "B", "sceneId": "scene.end.b"}, {"id": "ending.c", "title": "C", "sceneId": "scene.end.c"}]
        write_json(self.pack / "script.json", script)
        brief = read_json(self.pack / "project-brief.json"); brief["branching"].update({"choiceCount": 2, "endingCount": 3, "choiceHistoryCount": 3}); write_json(self.pack / "project-brief.json", brief)
        self.assertEqual(3, self.validate()["statistics"]["choiceHistoryCount"])

    def test_cycle_and_recursive_cue_implementation_fields_are_rejected(self) -> None:
        self.approve_valid_pack(); script = read_json(self.pack / "script.json")
        script["endings"] = []; script["scenes"][0]["nextSceneId"] = "scene.loop"; script["scenes"].append({"id": "scene.loop", "summary": "loop", "entries": [{"type": "cue", "id": "cueentry.loop", "cueId": "cue.loop"}], "nextSceneId": "scene.start"})
        script["cues"] = [{"id": "cue.loop", "kind": "visual", "emotion": "不安", "narrativePurpose": "閉塞を示す", "characters": [], "visibleContent": "狭い部屋", "musicFunction": "緊張", "playbackIntent": "start", "implementation": {"render": {"pixelWidth": 224, "assetId": "bg-1"}, "engineCommand": "show"}}]
        write_json(self.pack / "script.json", script)
        brief = read_json(self.pack / "project-brief.json"); brief["branching"].update({"endingCount": 0, "choiceHistoryCount": 0}); write_json(self.pack / "project-brief.json", brief)
        report = self.validate(expected=1); rules = [item["rule"] for item in report["issues"]]
        self.assertIn("cyclic-flow", rules); self.assertGreaterEqual(rules.count("engine-neutral-cue"), 3)

    def test_state_speaker_and_unreachable_failures(self) -> None:
        self.approve_valid_pack(); script = read_json(self.pack / "script.json")
        script["scenes"].append({"id": "scene.orphan", "summary": "孤立", "entries": [{"type": "state", "id": "state.orphan.write", "variableId": "state.missing", "operation": "set", "value": True}]})
        write_json(self.pack / "script.json", script); rules = {item["rule"] for item in self.validate(expected=1)["issues"]}; self.assertIn("unreachable-scene", rules); self.assertIn("state-write", rules)

    def test_integration_manifest_exact_consumption(self) -> None:
        self.approve_valid_pack(); aggregate = self.validate()["sourceAggregateSha256"]; manifest_path = self.root / "integration.json"
        mappings = [{"sharedId": "line.start.opening", "action": "consumed", "targetRefs": ["scene0.command0"]}, {"sharedId": "ending.default", "action": "substituted", "targetRefs": ["scene0.return"], "reason": "common ending primitive"}]
        write_json(manifest_path, {"formatVersion": 1, "target": "fixture", "sharedSourceAggregateSha256": aggregate, "mappings": mappings})
        self.run_tool("validate_integration_manifest.py", "--project-root", self.root, "--authoring-dir", self.pack, "--manifest", manifest_path)
        mappings.append(dict(mappings[0])); write_json(manifest_path, {"formatVersion": 1, "target": "fixture", "sharedSourceAggregateSha256": aggregate, "mappings": mappings})
        self.run_tool("validate_integration_manifest.py", "--project-root", self.root, "--authoring-dir", self.pack, "--manifest", manifest_path, expected=1)

    def test_legacy_migration_is_content_deterministic(self) -> None:
        old = self.root / "old"; write_json(old / "project-brief.json", {"formatVersion": 1, "projectId": "legacy", "title": "旧作"}); write_json(old / "character-bible.json", {"formatVersion": 1, "characters": []}); write_json(old / "language-rules.json", {"formatVersion": 1, "allowedSpeakers": [""]}); write_json(old / "scenario.json", {"formatVersion": 1, "initialScene": "start", "scenes": [{"id": "start", "script": [{"type": "message", "speaker": "", "text": "古い本文。"}, {"type": "routeEnding"}, {"type": "returnLogo"}]}]})
        out1, out2 = self.root / "migrated1", self.root / "migrated2"
        self.run_tool("migrate_gb_authoring_pack.py", "--project-root", self.root, "--source", old, "--out", out1); self.run_tool("migrate_gb_authoring_pack.py", "--project-root", self.root, "--source", old, "--out", out2)
        self.assertEqual(read_json(out1 / "script.json"), read_json(out2 / "script.json")); self.assertEqual("REVIEW_REQUIRED", read_json(out1 / "scenario-design.json")["status"]); self.assertTrue(read_json(out1 / "script.json")["scenes"][0]["entries"][0]["id"].startswith("line.migrated."))


if __name__ == "__main__": unittest.main()
