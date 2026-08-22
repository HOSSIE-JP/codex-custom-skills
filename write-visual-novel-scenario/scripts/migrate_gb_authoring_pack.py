from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from migrate_gb_authoring_pack_core import main as migrate_core
from vn_common import contained, dump_json, load_json


def normalize_legacy_character(character: Any) -> Any:
    if not isinstance(character, dict):
        return character
    normalized = dict(character)
    legacy_name = normalized.get("name")
    if not str(normalized.get("displayName", "")).strip() and str(legacy_name or "").strip():
        normalized["displayName"] = legacy_name
        normalized.pop("name", None)
    if not str(normalized.get("ageCategory", "")).strip():
        for legacy_key in ("ageGroup", "age_category"):
            legacy_age = normalized.get(legacy_key)
            if str(legacy_age or "").strip():
                normalized["ageCategory"] = legacy_age
                normalized.pop(legacy_key, None)
                break
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args, _ = parser.parse_known_args()
    migrate_core()
    root = args.project_root.resolve(strict=True)
    bible_path = contained(root, contained(root, args.out, must_exist=True) / "character-bible.json", must_exist=True)
    bible = load_json(bible_path)
    characters = bible.get("characters") if isinstance(bible.get("characters"), list) else []
    bible["characters"] = [normalize_legacy_character(character) for character in characters]
    dump_json(bible_path, bible)


if __name__ == "__main__":
    main()
