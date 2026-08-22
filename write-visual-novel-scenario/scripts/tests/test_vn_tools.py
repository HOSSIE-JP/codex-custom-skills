from __future__ import annotations

import vn_tools_cases as cases


class ToolTests(cases.ToolTests):
    def approve_valid_pack(self) -> None:
        super().approve_valid_pack()
        brief = cases.read_json(self.pack / "project-brief.json")
        brief["externalReview"]["status"] = "proceeding-provisionally"
        cases.write_json(self.pack / "project-brief.json", brief)
