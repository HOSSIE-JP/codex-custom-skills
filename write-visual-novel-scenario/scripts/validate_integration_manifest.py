from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_integration_manifest_core import required_integration_ids, validate_manifest
from validate_vn_scenario import validate_pack
from vn_common import ValidationError, contained, dump_json, load_json, source_hashes, source_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Require integration-ready source and prove exactly-once consumption of shared stable IDs.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--authoring-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True)
        paths = source_paths(root, args.authoring_dir)
        data = {name: load_json(path) for name, path in paths.items()}
        readiness = validate_pack(data, require_integration_ready=True)
        _, aggregate = source_hashes(paths)
        mapping = validate_manifest(data["script.json"], load_json(contained(root, args.manifest, must_exist=True)), aggregate)
        report = {**mapping, "authoringReadiness": readiness.get("integrationReadiness", {"status": "fail"})}
        if readiness["status"] != "pass":
            report["status"] = "fail"
            report["issues"] = readiness["issues"] + report["issues"]
        if args.report:
            dump_json(contained(root, args.report), report)
        print(json.dumps({key: report[key] for key in ("status", "sharedSourceAggregateSha256", "requiredCount", "mappedCount")}, ensure_ascii=False))
        if report["status"] != "pass":
            raise SystemExit(1)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
