from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_STYLE = (
    "GBC-friendly flat cel illustration with thick consistent dark outlines, broad solid color regions, "
    "two or three discrete value steps per material, a limited palette, simplified readable background shapes, "
    "separated silhouettes, and low-frequency detail that survives reduction to 160 pixels wide."
)
DEFAULT_AVOID = (
    "smooth gradients, airbrush shading, bloom, translucent glow, photorealistic texture, micro-detail, "
    "readable text, logos, watermarks, caption panels, dialogue windows, duplicated anatomy, detached limbs"
)
PURPOSES = {
    "messageSafeWide": {
        "generationSize": [1536, 1024],
        "layout": "Keep all important content inside a centered 5:3 safe composition for a 160x96 art area above a 48-pixel dialogue region.",
    },
    "fullscreenStill": {
        "generationSize": [1024, 1024],
        "layout": "Keep all important content inside a centered 10:9 safe crop for a fullscreen 160x144 still. Do not reserve a message band.",
    },
    "identityAnchor": {"generationSize": [1024, 1024], "layout": "Centered neutral face/identity anchor with clear stable features."},
    "outfitAnchor": {"generationSize": [1024, 1536], "layout": "Centered full-body neutral outfit anchor with an unobstructed silhouette."},
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def character_block(character: dict[str, Any], outfit_id: str) -> tuple[str, list[dict[str, str]]]:
    outfits = {str(item.get("id")): item for item in character.get("outfits", [])}
    if outfit_id not in outfits:
        raise ValueError(f"{character.get('id')}: unknown outfitId {outfit_id}")
    anchors = list(map(str, character.get("identityAnchors") or []))
    outfit = outfits[outfit_id]
    if not anchors or not outfit.get("anchor"):
        raise ValueError(f"{character.get('id')}: identity and outfit anchors are required")
    appearance = character.get("appearance") or {}
    lock = "; ".join(f"{key}={value}" for key, value in appearance.items() if key != "prohibitedDrift")
    drift = ", ".join(map(str, appearance.get("prohibitedDrift") or []))
    text = (
        f"Character {character['id']} ({character.get('displayName', character['id'])}): age {character.get('age')}; "
        f"adult={character.get('adult')}; identity lock: {lock}; outfit {outfit_id}: {outfit.get('description')}; "
        f"prohibited drift: {drift or 'none declared'}."
    )
    refs = [{"path": path, "role": f"identity reference for {character['id']}"} for path in anchors]
    refs.append({"path": str(outfit["anchor"]), "role": f"outfit reference {outfit_id} for {character['id']}"})
    return text, refs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build grounded one-cut-per-image ImageGen jobs for a GB Studio VN.")
    parser.add_argument("--bible", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    bible = load_json(args.bible)
    manifest = load_json(args.manifest)
    style = manifest.get("style") or {}
    if style.get("id", "gbc-flat-cel-v1") != "gbc-flat-cel-v1" and not style.get("explicitUserOverride"):
        raise SystemExit("A non-default visual style requires explicitUserOverride=true")

    characters = {str(item.get("id")): item for item in bible.get("characters", [])}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for cut in manifest.get("cuts", []):
        cut_id = str(cut.get("id", ""))
        if not cut_id or cut_id in seen:
            raise SystemExit(f"Cut IDs must be non-empty and unique: {cut_id!r}")
        seen.add(cut_id)
        purpose = str(cut.get("purpose", ""))
        if purpose == "deterministicUi":
            jobs.append({"id": cut_id, "route": "deterministic-code", "reason": "exact text or UI"})
            continue
        if purpose not in PURPOSES:
            raise SystemExit(f"{cut_id}: unsupported purpose {purpose}")

        character_lines: list[str] = []
        references: list[dict[str, str]] = []
        for entry in cut.get("characters") or []:
            character_id = str(entry.get("id", ""))
            if character_id not in characters:
                raise SystemExit(f"{cut_id}: unknown character {character_id}")
            line, refs = character_block(characters[character_id], str(entry.get("outfitId", "")))
            character_lines.append(line)
            references.extend(refs)

        anatomy = cut.get("anatomy") or {}
        hand_lines = []
        for hand in anatomy.get("visibleHands") or []:
            roles = ", ".join(map(str, hand.get("roles") or []))
            hand_lines.append(f"{hand.get('owner')}: exactly {hand.get('count')} visible hand(s), roles: {roles}")
        forbidden = [
            f"no {item.get('object')} at x={item.get('xPercent')}%, y={item.get('yPercent')}%"
            for item in anatomy.get("forbiddenRegions") or []
        ]
        hidden = "; ".join(map(str, anatomy.get("hiddenLimbs") or []))
        purpose_data = PURPOSES[purpose]
        prompt = "\n".join([
            "Use case: stylized-concept",
            f"Asset type: GB Studio visual-novel {purpose}",
            f"Primary request: {cut.get('action', '')}",
            f"Scene/backdrop: {cut.get('scene', '')}",
            f"Composition/framing: {cut.get('camera', '')}. {purpose_data['layout']}",
            f"Style/medium: {DEFAULT_STYLE}",
            "Character identity and wardrobe locks:",
            *[f"- {line}" for line in character_lines],
            f"Props: {', '.join(map(str, cut.get('props') or [])) or 'none'}",
            f"Anatomy: exactly {anatomy.get('visiblePeople', len(character_lines))} visible person(s). " + "; ".join(hand_lines),
            f"Hidden limbs: {hidden or 'none declared'}",
            f"Forbidden regions: {'; '.join(forbidden) or 'none'}",
            "Defect handling: remove each forbidden object and its broken connected anatomy; reconstruct the existing underlying surface; do not reinterpret it or replace it with another hand, limb, or gesture.",
            "Constraints: one production cut only; every visible hand must connect through wrist, elbow, and shoulder to its owner; no embedded message band; no text.",
            f"Avoid: {DEFAULT_AVOID}",
        ]) + "\n"
        prompt_path = args.out_dir / f"{cut_id}.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        jobs.append({
            "id": cut_id,
            "route": "imagegen",
            "purpose": purpose,
            "generationSize": purpose_data["generationSize"],
            "promptPath": prompt_path.name,
            "inputImages": references,
            "outputPath": cut.get("sourcePath", ""),
            "status": "pending",
        })

    write_json(args.out_dir / "imagegen-jobs.json", {"formatVersion": 1, "style": style, "jobs": jobs})
    print(f"Generated {len(jobs)} visual job(s) in {args.out_dir}")


if __name__ == "__main__":
    main()
