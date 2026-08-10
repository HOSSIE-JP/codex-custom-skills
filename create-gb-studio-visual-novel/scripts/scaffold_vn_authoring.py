from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL_ROOT / "assets" / "templates"


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy the GB Studio VN authoring templates without accidental overwrite.")
    parser.add_argument("--out", type=Path, required=True, help="Destination authoring directory")
    parser.add_argument("--force", action="store_true", help="Explicitly overwrite existing template files")
    args = parser.parse_args()

    sources = sorted(TEMPLATES.glob("*.json"))
    if not sources:
        raise SystemExit(f"No templates found in {TEMPLATES}")

    args.out.mkdir(parents=True, exist_ok=True)
    collisions = [args.out / source.name for source in sources if (args.out / source.name).exists()]
    if collisions and not args.force:
        joined = "\n".join(str(path) for path in collisions)
        raise SystemExit(f"Refusing to overwrite existing authoring files:\n{joined}\nUse --force only with explicit approval.")

    for source in sources:
        shutil.copy2(source, args.out / source.name)
    print(f"Copied {len(sources)} VN authoring templates to {args.out}")


if __name__ == "__main__":
    main()
