from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class DesignOnlyValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name); self.pack = self.root / "source" / "vn-authoring"; self.pack.mkdir(parents=True)
        self.brief = {"formatVersion": 2, "projectId": "new-work", "language": "ja", "expectedMinutes": 10, "branching": {"choiceCount": 1, "endingCount": 2, "choiceHistoryCount": 2, "stateVariables": ["state.trust"]}}
        self.bible = {"formatVersion": 2, "projectId": "new-work", "characters": [{"id": "hero", "displayName": "ユキ", "ageCategory": "adult", "role": "主人公", "desire": "帰る", "obstacle": "道が閉ざされている", "change": "助けを求められるようになる", "voice": {"style": "短く慎重に話す"}}]}
        self.rules = {"formatVersion": 2, "allowedSpeakers": ["narrator", "hero"]}
        self.design = {"formatVersion": 2, "projectId": "new-work", "revision": 1, "status": "REVIEW_REQUIRED", "approvedRevision": None, "structureLensCandidates": [{"id": "lens.character", "selectionReason": "主人公の変化を選択へ結びつける", "selected": True}, {"id": "lens.mystery", "rejectionReason": "情報隠蔽より関係変化を優先する", "selected": False}], "selectedStructureLenses": ["lens.character"], "characterArcs": [], "beats": [{"id": "beat.open"}, {"id": "beat.choice"}, {"id": "beat.payoff"}], "sceneBoxes": [{"id": "scene.start", "estimatedMinutes": 3}, {"id": "scene.choice", "estimatedMinutes": 3}, {"id": "scene.end", "estimatedMinutes": 4}], "branchAndJoinPlan": [{"type": "choice", "id": "choice.path", "sceneId": "scene.choice", "options": [{"id": "option.ask", "targetSceneId": "scene.end", "setState": {"state.trust": True}}, {"id": "option.silent", "targetSceneId": "scene.end", "setState": {"state.trust": False}}], "joinSceneId": "scene.end", "stateWrites": ["state.trust"]}], "endingPlan": [{"id": "ending.trust", "sceneId": "scene.end"}, {"id": "ending.silence", "sceneId": "scene.end"}], "semanticCuePlan": [{"id": "cue.rain", "kind": "visual", "emotion": "不安", "narrativePurpose": "孤立を示す", "characters": ["hero"], "visibleContent": "窓を流れる雨", "musicFunction": "緊張を保つ", "playbackIntent": "start"}]}
        self.flush()

    def tearDown(self) -> None: self.temp.cleanup()

    def flush(self) -> None:
        write(self.pack / "project-brief.json", self.brief); write(self.pack / "character-bible.json", self.bible); write(self.pack / "scenario-design.json", self.design); write(self.pack / "language-rules.json", self.rules)

    def design_run(self, expected: int) -> dict:
        report = self.pack / "design-report.json"
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_vn_design.py"), "--project-root", str(self.root), "--authoring-dir", str(self.pack), "--report", str(report)], cwd=SCRIPTS, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        return json.loads(report.read_text(encoding="utf-8"))

    def test_review_required_design_passes_while_full_pack_cleanly_fails(self) -> None:
        self.assertEqual("pass", self.design_run(0)["status"])
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_vn_scenario.py"), "--project-root", str(self.root), "--authoring-dir", str(self.pack), "--report", str(self.pack / "full.json")], cwd=SCRIPTS, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(2, result.returncode); self.assertNotIn("Traceback", result.stderr)

    def test_bad_duration_id_counts_and_cue_fields_are_rejected(self) -> None:
        mutations = [
            ("duration", lambda: self.brief.update({"expectedMinutes": 11}), "duration-total"),
            ("id", lambda: self.design["sceneBoxes"].append({"id": "scene.start", "estimatedMinutes": 0}), "duplicate-id"),
            ("count", lambda: self.brief["branching"].update({"choiceCount": 2}), "choice-count"),
            ("cue", lambda: self.design["semanticCuePlan"][0].update({"implementation": {"assetId": "bg-1", "pixelWidth": 224}}), "engine-neutral-cue"),
        ]
        original_brief, original_design = copy.deepcopy(self.brief), copy.deepcopy(self.design)
        for name, mutate, expected_rule in mutations:
            with self.subTest(name=name):
                self.brief, self.design = copy.deepcopy(original_brief), copy.deepcopy(original_design); mutate(); self.flush()
                rules = {item["rule"] for item in self.design_run(1)["issues"]}; self.assertIn(expected_rule, rules)


if __name__ == "__main__": unittest.main()
