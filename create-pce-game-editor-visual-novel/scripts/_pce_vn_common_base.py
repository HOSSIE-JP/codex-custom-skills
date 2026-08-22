from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_json(path: Path, value: Any, force: bool = False) -> None:
    if path.exists() and not force:
        raise ValidationError(f"Refusing to overwrite existing file: {path}; pass --force explicitly")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_authoring_dir(pack: Path) -> tuple[Path, Path]:
    resolved = pack.resolve(strict=True)
    if resolved.is_file():
        if resolved.name != "script.json":
            raise ValidationError("a file-valued --pack must be source/vn-authoring/script.json")
        authoring = resolved.parent
    elif (resolved / "source" / "vn-authoring" / "script.json").is_file():
        authoring = resolved / "source" / "vn-authoring"
    elif (resolved / "script.json").is_file():
        authoring = resolved
    else:
        raise ValidationError(f"no complete source/vn-authoring pack found under {resolved}")
    if authoring.parent.name == "source":
        project_root = authoring.parent.parent
    else:
        raise ValidationError("authoring pack must be located at <project>/source/vn-authoring")
    return project_root.resolve(strict=True), authoring.resolve(strict=True)


def shared_modules() -> tuple[Any, Any, Any]:
    shared_scripts = Path(__file__).resolve().parents[2] / "write-visual-novel-scenario" / "scripts"
    if not (shared_scripts / "validate_vn_scenario.py").is_file():
        raise ValidationError(f"shared VN validator is unavailable: {shared_scripts}")
    sys.path.insert(0, str(shared_scripts))
    try:
        common = importlib.import_module("vn_common")
        validator = importlib.import_module("validate_vn_scenario")
        integration = importlib.import_module("validate_integration_manifest")
    finally:
        if sys.path and sys.path[0] == str(shared_scripts):
            sys.path.pop(0)
    return common, validator, integration


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
        report = validator.validate_pack(data, require_approved=require_approved)
        _, aggregate = common.source_hashes(paths)
    except common.ValidationError as exc:
        raise ValidationError(str(exc)) from exc
    if report.get("status") != "pass":
        errors = [item.get("detail", "validation error") for item in report.get("issues", []) if item.get("severity") == "error"]
        raise ValidationError("shared authoring validation failed: " + "; ".join(errors))
    review = data["self-review.json"]
    passes = review.get("passes") if isinstance(review.get("passes"), dict) else {}
    required_passes = ("mechanical", "readAloud", "characterVoice", "expositionAndBranchJoins")
    if review.get("status") != "complete" or any(
        not isinstance(passes.get(name), dict)
        or passes[name].get("status") != "complete"
        or not str(passes[name].get("evidence", "")).strip()
        or not isinstance(passes[name].get("revisions"), list)
        or not passes[name]["revisions"]
        for name in required_passes
    ):
        raise ValidationError("all four self-review passes must be complete with evidence and revision/no-change records")
    external = data["project-brief.json"].get("externalReview", {})
    if external.get("status") not in {"proceeding-provisionally", "waived-by-user", "complete"}:
        raise ValidationError("external-review consultation is not resolved for downstream integration")
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


def pce_id(source_id: str, prefix: str = "id") -> str:
    value = re.sub(r"[^a-zA-Z0-9_]", "_", source_id).strip("_").lower()
    if not value or not value[0].isalpha():
        value = f"{prefix}_{value}" if value else prefix
    if len(value) > 48:
        suffix = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:8]
        value = f"{value[:39]}_{suffix}"
    return value


def path_record(path: Path, root: Path | None = None) -> dict[str, str]:
    resolved = path.resolve(strict=True)
    if root is not None:
        try:
            label = resolved.relative_to(root.resolve(strict=True)).as_posix()
        except ValueError:
            label = resolved.as_posix()
    else:
        label = resolved.name
    return {"path": label, "sha256": sha256_file(resolved)}
