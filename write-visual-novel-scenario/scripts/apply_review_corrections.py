from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from validate_vn_scenario import validate_pack
from vn_common import ValidationError, contained, dump_json, load_json, source_hashes, source_paths


def editable_units(script: dict[str, Any]) -> dict[str, tuple[dict[str, Any], str]]:
    result: dict[str, tuple[dict[str, Any], str]] = {}
    for scene in script.get("scenes") or []:
        for entry in scene.get("entries") or []:
            identifier = str(entry.get("id", ""))
            if entry.get("type") == "line":
                result[identifier] = (entry, "text")
            elif entry.get("type") == "choice":
                if "prompt" in entry:
                    result[identifier] = (entry, "prompt")
                for option in entry.get("options") or []:
                    result[str(option.get("id", ""))] = (option, "text")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply non-structural stable-ID review corrections to a current shared script.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--authoring-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True)
        paths = source_paths(root, args.authoring_dir)
        manifest = load_json(contained(root, args.manifest, must_exist=True))
        corrections = load_json(contained(root, args.corrections, must_exist=True))
        _, current_aggregate = source_hashes(paths)
        manifest_sha = str(manifest.get("sourceAggregateSha256", ""))
        corrections_sha = str(corrections.get("sourceAggregateSha256", ""))
        if not manifest_sha or manifest_sha != current_aggregate or corrections_sha != current_aggregate:
            raise ValidationError(f"stale correction source: current={current_aggregate}, manifest={manifest_sha}, corrections={corrections_sha}")
        original = load_json(paths["script.json"])
        updated = copy.deepcopy(original)
        units = editable_units(updated)
        seen: set[str] = set()
        applied: list[str] = []
        for index, edit in enumerate(corrections.get("edits") or []):
            if not isinstance(edit, dict):
                raise ValidationError(f"edit[{index}] must be an object")
            identifier = str(edit.get("id", ""))
            if identifier in seen:
                raise ValidationError(f"duplicate correction ID: {identifier}")
            seen.add(identifier)
            if identifier not in units:
                raise ValidationError(f"unknown or structurally non-editable stable ID: {identifier}")
            target, allowed_field = units[identifier]
            field = str(edit.get("field", ""))
            if field != allowed_field:
                raise ValidationError(f"{identifier}: field must be {allowed_field}")
            before, after = edit.get("before"), edit.get("after")
            if target.get(field) != before:
                raise ValidationError(f"{identifier}: before text does not match current source")
            if not isinstance(after, str) or not after.strip():
                raise ValidationError(f"{identifier}: after text must be non-empty")
            if not str(edit.get("reason", "")).strip():
                raise ValidationError(f"{identifier}: correction reason is required")
            target[field] = after
            applied.append(identifier)
        if not applied:
            raise ValidationError("corrections contain no edits")
        data = {name: load_json(path) for name, path in paths.items()}
        data["script.json"] = updated
        validation = validate_pack(data, require_approved=True)
        if validation["status"] != "pass":
            details = "; ".join(item["detail"] for item in validation["issues"] if item["severity"] == "error")
            raise ValidationError("corrected script is invalid: " + details)
        dump_json(paths["script.json"], updated)
        print(json.dumps({"status": "pass", "applied": applied, "previousSourceAggregateSha256": current_aggregate, "reviewPackNowStale": True}, ensure_ascii=False))
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
