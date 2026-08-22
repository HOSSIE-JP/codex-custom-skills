from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from vn_common import ValidationError, all_shared_ids, contained, dump_json, load_json, source_hashes, source_paths


def required_integration_ids(script: dict[str, Any]) -> dict[str, str]:
    return {identifier: kind for identifier, kind in all_shared_ids(script).items() if kind != "scene"}


def validate_manifest(script: dict[str, Any], manifest: dict[str, Any], aggregate: str) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def issue(severity: str, identifier: str, detail: str) -> None:
        issues.append({"severity": severity, "sharedId": identifier, "detail": detail})

    if manifest.get("formatVersion") != 1:
        issue("error", "manifest", "formatVersion must be 1")
    if manifest.get("sharedSourceAggregateSha256") != aggregate:
        issue("error", "manifest", f"shared source SHA mismatch; expected {aggregate}")
    required = required_integration_ids(script)
    seen: set[str] = set()
    for index, mapping in enumerate(manifest.get("mappings") or []):
        if not isinstance(mapping, dict):
            issue("error", f"mapping[{index}]", "mapping must be an object")
            continue
        identifier = str(mapping.get("sharedId", ""))
        if identifier in seen:
            issue("error", identifier, "shared ID mapped more than once")
            continue
        seen.add(identifier)
        if identifier not in required:
            issue("error", identifier, "unknown shared ID")
            continue
        action = mapping.get("action")
        if action not in {"consumed", "substituted"}:
            issue("error", identifier, "action must be consumed or substituted")
        refs = mapping.get("targetRefs")
        if not isinstance(refs, list) or not refs or any(not str(value).strip() for value in refs):
            issue("error", identifier, "targetRefs must contain at least one non-empty target reference")
        if action == "substituted" and not str(mapping.get("reason", "")).strip():
            issue("error", identifier, "substitution requires a reason")
    for identifier in sorted(set(required) - seen):
        issue("error", identifier, f"{required[identifier]} was not consumed or substituted")
    errors = [item for item in issues if item["severity"] == "error"]
    return {"status": "fail" if errors else "pass", "sharedSourceAggregateSha256": aggregate, "requiredCount": len(required), "mappedCount": len(seen & set(required)), "issues": issues}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prove that a target integration consumes each shared stable ID exactly once.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--authoring-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True)
        paths = source_paths(root, args.authoring_dir)
        _, aggregate = source_hashes(paths)
        script = load_json(paths["script.json"])
        manifest = load_json(contained(root, args.manifest, must_exist=True))
        report = validate_manifest(script, manifest, aggregate)
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
