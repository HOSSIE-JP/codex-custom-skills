from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


SOURCE_FILES = (
    "project-brief.json",
    "character-bible.json",
    "scenario-design.json",
    "script.json",
    "language-rules.json",
    "self-review.json",
)
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


class ValidationError(ValueError):
    pass


def contained(root: Path, candidate: Path, *, must_exist: bool = False) -> Path:
    root = root.resolve(strict=True)
    path = candidate.resolve(strict=must_exist)
    if path != root and root not in path.parents:
        raise ValidationError(f"path escapes project root: {candidate}")
    return path


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return value


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def source_paths(project_root: Path, authoring_dir: Path) -> dict[str, Path]:
    base = contained(project_root, authoring_dir, must_exist=True)
    result = {name: contained(project_root, base / name, must_exist=True) for name in SOURCE_FILES}
    return result


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(paths: dict[str, Path]) -> tuple[dict[str, str], str]:
    hashes = {name: sha256_file(paths[name]) for name in sorted(paths)}
    canonical = json.dumps(hashes, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashes, hashlib.sha256(canonical).hexdigest()


def require_id(value: Any, label: str) -> str:
    text = str(value or "")
    if not ID_RE.fullmatch(text):
        raise ValidationError(f"{label} must be a stable lowercase ASCII ID: {text!r}")
    return text


def unique_ids(values: Iterable[tuple[str, str]], label: str) -> set[str]:
    seen: set[str] = set()
    for identifier, location in values:
        require_id(identifier, location)
        if identifier in seen:
            raise ValidationError(f"duplicate {label} ID: {identifier}")
        seen.add(identifier)
    return seen


def canonical_payload(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_id(prefix: str, value: Any, used: set[str]) -> str:
    digest = hashlib.sha256(canonical_payload(value)).hexdigest()
    for width in range(12, 65, 4):
        candidate = f"{prefix}.migrated.{digest[:width]}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    raise ValidationError(f"cannot assign unique content ID for {prefix}")


def all_shared_ids(script: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}

    def add(identifier: Any, kind: str) -> None:
        stable = require_id(identifier, kind)
        if stable in result:
            raise ValidationError(f"duplicate shared ID across categories: {stable}")
        result[stable] = kind

    for scene in script.get("scenes") or []:
        add(scene.get("id"), "scene")
        for entry in scene.get("entries") or []:
            add(entry.get("id"), str(entry.get("type") or "entry"))
            if entry.get("type") == "choice":
                for option in entry.get("options") or []:
                    add(option.get("id"), "choiceOption")
    for cue in script.get("cues") or []:
        add(cue.get("id"), "cueDefinition")
    for ending in script.get("endings") or []:
        add(ending.get("id"), "ending")
    return result
