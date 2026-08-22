from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_vn_core import validate_pack as validate_core_pack
from vn_common import ValidationError, contained, dump_json, load_json, source_hashes, source_paths


PASS_NAMES = ("mechanical", "readAloud", "characterVoice", "expositionAndBranchJoins")
INTEGRATION_READY_STATUSES = {"proceeding-provisionally", "waived-by-user", "complete"}


def validate_pack(data: dict[str, dict[str, Any]], *, require_approved: bool = False, require_integration_ready: bool = False) -> dict[str, Any]:
    report = validate_core_pack(data, require_approved=require_approved or require_integration_ready)
    if not require_integration_ready:
        return report
    readiness: list[dict[str, str]] = []

    def reject(location: str, rule: str, detail: str) -> None:
        readiness.append({"severity": "error", "location": location, "rule": rule, "detail": detail})

    review = data["self-review.json"]
    if review.get("status") != "complete":
        reject("self-review.json", "self-review-status", "aggregate self-review status must be complete")
    passes = review.get("passes") if isinstance(review.get("passes"), dict) else {}
    for name in PASS_NAMES:
        value = passes.get(name) if isinstance(passes.get(name), dict) else {}
        location = f"self-review.json:passes.{name}"
        if value.get("status") != "complete":
            reject(location, "self-review-pass", "pass status must be complete")
        if not str(value.get("evidence", "")).strip():
            reject(location, "self-review-evidence", "non-empty evidence is required")
        revisions = value.get("revisions")
        if not isinstance(revisions, list) or not revisions or not any(str(item).strip() for item in revisions):
            reject(location, "self-review-revisions", "record a concrete revision or explicit no-change result")
    external = data["project-brief.json"].get("externalReview") if isinstance(data["project-brief.json"].get("externalReview"), dict) else {}
    status = str(external.get("status", ""))
    if status not in INTEGRATION_READY_STATUSES:
        reject("project-brief.json:externalReview.status", "external-review-integration-gate", f"{status!r} blocks downstream integration; expected one of {sorted(INTEGRATION_READY_STATUSES)}")
    report["issues"].extend(readiness)
    report["integrationReadiness"] = {"status": "fail" if readiness else "pass", "allowedExternalReviewStatuses": sorted(INTEGRATION_READY_STATUSES), "selfReviewPasses": list(PASS_NAMES)}
    if readiness:
        report["status"] = "fail"
        report["statistics"]["errors"] += len(readiness)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate shared Japanese VN schema, graph, stable IDs, approvals, and optional integration readiness.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--authoring-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--require-integration-ready", action="store_true")
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True)
        paths = source_paths(root, args.authoring_dir)
        report_path = contained(root, args.report)
        data = {name: load_json(path) for name, path in paths.items()}
        report = validate_pack(data, require_approved=args.require_approved, require_integration_ready=args.require_integration_ready)
        hashes, aggregate = source_hashes(paths)
        report["sourceSha256"] = hashes
        report["sourceAggregateSha256"] = aggregate
        dump_json(report_path, report)
        summary = {"status": report["status"], "sourceAggregateSha256": aggregate, **report["statistics"]}
        if "integrationReadiness" in report:
            summary["integrationReadiness"] = report["integrationReadiness"]["status"]
        print(json.dumps(summary, ensure_ascii=False))
        if report["status"] != "pass":
            raise SystemExit(1)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
