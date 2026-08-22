from __future__ import annotations

from pathlib import Path
from typing import Any

from _pce_vn_common_base import *
from _pce_vn_common_base import ValidationError, find_authoring_dir, load_json, shared_modules


def load_shared_pack(
    pack: Path,
    *,
    require_approved: bool,
    validation_report: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Path]]:
    project_root, authoring = find_authoring_dir(pack)
    common, validator, _ = shared_modules()
    try:
        paths = common.source_paths(project_root, authoring)
        data = {name: common.load_json(path) for name, path in paths.items()}
        report = validator.validate_pack(
            data,
            require_approved=require_approved,
            require_integration_ready=require_approved,
        )
        _, aggregate = common.source_hashes(paths)
    except common.ValidationError as exc:
        raise ValidationError(str(exc)) from exc
    if report.get("status") != "pass":
        errors = [item.get("detail", "validation error") for item in report.get("issues", []) if item.get("severity") == "error"]
        raise ValidationError("shared authoring validation failed: " + "; ".join(errors))
    report = {**report, "sourceAggregateSha256": aggregate}
    if validation_report is not None:
        supplied = load_json(validation_report)
        if not isinstance(supplied, dict) or supplied.get("status") != "pass":
            raise ValidationError("shared validation report must have status=pass")
        if supplied.get("sourceAggregateSha256") != aggregate:
            raise ValidationError("shared validation report aggregate SHA is stale")
        if require_approved and supplied.get("approved") is not True:
            raise ValidationError("shared validation report is not approved")
    return data, report, aggregate, paths
