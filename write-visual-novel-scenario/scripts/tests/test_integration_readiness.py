from __future__ import annotations

import unittest

import test_vn_tools as shared
import vn_tools_cases as cases


class IntegrationReadinessTests(shared.ToolTests):
    def gate(self, expected: int) -> dict:
        report = self.pack / "integration-ready.json"
        self.run_tool("validate_vn_scenario.py", "--project-root", self.root, "--authoring-dir", self.pack, "--report", report, "--require-integration-ready", expected=expected)
        return cases.read_json(report)

    def test_incomplete_self_review_is_rejected(self) -> None:
        self.approve_valid_pack()
        review = cases.read_json(self.pack / "self-review.json")
        review["status"] = "required"
        review["passes"]["readAloud"].update({"status": "required", "evidence": "", "revisions": []})
        cases.write_json(self.pack / "self-review.json", review)
        rules = {item["rule"] for item in self.gate(1)["issues"]}
        self.assertIn("self-review-status", rules); self.assertIn("self-review-pass", rules); self.assertIn("self-review-evidence", rules); self.assertIn("self-review-revisions", rules)

    def test_pending_and_awaiting_external_review_are_rejected(self) -> None:
        for status in ("pending-user-decision", "awaiting-external-review"):
            with self.subTest(status=status):
                self.approve_valid_pack()
                brief = cases.read_json(self.pack / "project-brief.json"); brief["externalReview"]["status"] = status; cases.write_json(self.pack / "project-brief.json", brief)
                self.assertIn("external-review-integration-gate", {item["rule"] for item in self.gate(1)["issues"]})
                self.temp.cleanup(); self.setUp()

    def test_three_consulted_statuses_are_integration_ready(self) -> None:
        for status in ("proceeding-provisionally", "waived-by-user", "complete"):
            with self.subTest(status=status):
                self.approve_valid_pack()
                brief = cases.read_json(self.pack / "project-brief.json"); brief["externalReview"]["status"] = status; cases.write_json(self.pack / "project-brief.json", brief)
                self.assertEqual("pass", self.gate(0)["integrationReadiness"]["status"])
                self.temp.cleanup(); self.setUp()


if __name__ == "__main__": unittest.main()
