from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL_ROOT / "assets" / "templates"


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy VN BGM cue and track templates without accidental overwrite.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    sources = sorted(TEMPLATES.glob("*.json"))
    args.out.mkdir(parents=True, exist_ok=True)
    collisions = [args.out / source.name for source in sources if (args.out / source.name).exists()]
    if collisions and not args.force:
        raise SystemExit("Refusing to overwrite:\n" + "\n".join(map(str, collisions)) + "\nUse --force only with explicit approval.")
    for source in sources:
        shutil.copy2(source, args.out / source.name)
    print(f"Copied {len(sources)} VN BGM template(s) to {args.out}")


if __name__ == "__main__":
    main()
