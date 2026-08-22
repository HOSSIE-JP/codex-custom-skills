from __future__ import annotations

import unittest

import test_vn_tools as shared
import vn_tools_cases as cases


class MigrationCharacterNormalizationTests(shared.ToolTests):
    def test_legacy_name_and_age_category_are_preserved_deterministically(self) -> None:
        old = self.root / "legacy-characters"
        cases.write_json(old / "project-brief.json", {"formatVersion": 1, "projectId": "legacy-cast", "title": "旧作"})
        cases.write_json(old / "character-bible.json", {
            "formatVersion": 1,
            "characters": [
                {"id": "hero", "name": "ユキ", "ageGroup": "adult", "role": "主人公", "desire": "帰る", "obstacle": "道がない"},
                {"id": "guide", "name": "ミナト", "age_category": "young-adult", "role": "案内役", "desire": "守る", "obstacle": "秘密がある"}
            ]
        })
        cases.write_json(old / "language-rules.json", {"formatVersion": 1, "allowedSpeakers": ["hero", "guide"]})
        cases.write_json(old / "scenario.json", {"formatVersion": 1, "initialScene": "start", "scenes": [{"id": "start", "script": [{"type": "message", "speaker": "hero", "text": "帰ろう。"}, {"type": "routeEnding"}]}]})
        outputs = [self.root / "normalized-1", self.root / "normalized-2"]
        for output in outputs:
            self.run_tool("migrate_gb_authoring_pack.py", "--project-root", self.root, "--source", old, "--out", output)
        first = cases.read_json(outputs[0] / "character-bible.json")
        second = cases.read_json(outputs[1] / "character-bible.json")
        self.assertEqual(first, second)
        by_id = {item["id"]: item for item in first["characters"]}
        self.assertEqual("ユキ", by_id["hero"]["displayName"])
        self.assertEqual("adult", by_id["hero"]["ageCategory"])
        self.assertEqual("ミナト", by_id["guide"]["displayName"])
        self.assertEqual("young-adult", by_id["guide"]["ageCategory"])
        self.assertNotIn("name", by_id["hero"])
        self.assertNotIn("ageGroup", by_id["hero"])
        self.assertNotIn("age_category", by_id["guide"])
        for name in ("project-brief.json", "character-bible.json", "scenario-design.json", "script.json", "language-rules.json", "self-review.json"):
            self.assertEqual(cases.read_json(outputs[0] / name), cases.read_json(outputs[1] / name), name)


if __name__ == "__main__":
    unittest.main()
