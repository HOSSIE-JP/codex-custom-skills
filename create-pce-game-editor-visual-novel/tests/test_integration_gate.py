from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parent / "scripts"
sys.path.insert(0, str(TEST_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from pce_vn_common import ValidationError, load_shared_pack  # noqa: E402
from test_scripts import full_pack, write_pack  # noqa: E402


class SharedIntegrationReadyGateTests(unittest.TestCase):
    def test_pending_external_review_consultation_blocks_pce_integration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            data = full_pack()
            data["project-brief.json"]["externalReview"]["status"] = "pending-user-decision"
            write_pack(root, data)
            with self.assertRaises(ValidationError):
                load_shared_pack(root, require_approved=True)


if __name__ == "__main__":
    unittest.main()
