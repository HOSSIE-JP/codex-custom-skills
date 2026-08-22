from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]


class MissingCanonicalFilesTests(unittest.TestCase):
    def test_script_only_pack_exits_cleanly_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = root / "source" / "vn-authoring"
            pack.mkdir(parents=True)
            (pack / "script.json").write_text(json.dumps({"formatVersion": 2}, ensure_ascii=False) + "\n", encoding="utf-8")
            result = subprocess.run([
                sys.executable,
                str(SCRIPTS / "validate_vn_scenario.py"),
                "--project-root", str(root),
                "--authoring-dir", str(pack),
                "--report", str(pack / "validation.json"),
            ], cwd=SCRIPTS, text=True, encoding="utf-8", capture_output=True)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn("path does not exist or cannot be resolved", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
