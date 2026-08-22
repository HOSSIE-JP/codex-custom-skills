from __future__ import annotations

import argparse
from pathlib import Path

from pce_vn_common import ValidationError, load_shared_pack, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the shared VN full-pack approval/review/graph gate for PCE integration.")
    parser.add_argument("--pack", type=Path, required=True, help="Project root or source/vn-authoring directory")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        data, report, aggregate, _ = load_shared_pack(args.pack, require_approved=True)
        output = {
            "formatVersion": 1,
            "status": "pass",
            "approved": bool(report.get("approved")),
            "sourceAggregateSha256": aggregate,
            "revision": data["script.json"]["revision"],
            "statistics": report.get("statistics", {}),
            "reachableScenes": report.get("reachableScenes", []),
            "reachableEndings": report.get("reachableEndings", []),
            "externalReviewStatus": data["project-brief.json"]["externalReview"]["status"],
            "selfReviewStatus": data["self-review.json"]["status"],
        }
        write_json(args.report, output, args.force)
        print(f"OK: aggregate={aggregate}, revision={output['revision']}, endings={len(output['reachableEndings'])}")
    except ValidationError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
