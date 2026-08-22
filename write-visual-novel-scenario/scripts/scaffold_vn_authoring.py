from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from vn_common import ValidationError, contained


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL_ROOT / "assets" / "templates"
AUTHORING_NAMES = {"project-brief.json", "character-bible.json", "scenario-design.json", "script.json", "language-rules.json", "self-review.json"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold an engine-neutral Japanese VN authoring pack.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="Overwrite only with explicit user approval")
    args = parser.parse_args()
    try:
        root = args.project_root.resolve(strict=True)
        out = contained(root, args.out)
        sources = sorted(path for path in TEMPLATES.glob("*.json") if path.name in AUTHORING_NAMES)
        if {path.name for path in sources} != AUTHORING_NAMES:
            raise ValidationError("authoring templates are incomplete")
        collisions = [out / source.name for source in sources if (out / source.name).exists()]
        if collisions and not args.force:
            raise ValidationError("refusing to overwrite existing files:\n" + "\n".join(map(str, collisions)))
        out.mkdir(parents=True, exist_ok=True)
        for source in sources:
            shutil.copy2(source, out / source.name)
        print(f"Copied {len(sources)} templates to {out}")
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
