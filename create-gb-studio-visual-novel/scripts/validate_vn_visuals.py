from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError as exc:
    raise SystemExit("Pillow is required: install it in the active environment before running visual QA") from exc


PURPOSE_SIZES = {
    "messageSafeWide": (1536, 1024),
    "fullscreenStill": (1024, 1024),
    "identityAnchor": (1024, 1024),
    "outfitAnchor": (1024, 1536),
}
QA_NAMES = ("fullResolution", "anatomy", "identity", "nativeGbc", "runtime")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_tiles(image: Image.Image) -> list[tuple[tuple[int, int, int], ...]]:
    rgb = image.convert("RGB")
    if rgb.width % 8 or rgb.height % 8:
        return []
    return [
        tuple(rgb.crop((x, y, x + 8, y + 8)).getdata())
        for y in range(0, rgb.height, 8)
        for x in range(0, rgb.width, 8)
    ]


def merged_palette_count(tiles: list[tuple[tuple[int, int, int], ...]]) -> int:
    palettes = [set(tile) for tile in tiles]
    changed = True
    while changed:
        changed = False
        for left in range(len(palettes)):
            for right in range(left + 1, len(palettes)):
                if len(palettes[left] | palettes[right]) <= 4:
                    palettes[left] |= palettes[right]
                    palettes.pop(right)
                    changed = True
                    break
            if changed:
                break
    return len(palettes)


def add_issue(items: list[dict[str, str]], cut_id: str, rule: str, detail: str) -> None:
    items.append({"cut": cut_id, "rule": rule, "detail": detail})


def resolve(root: Path, value: Any) -> Path:
    return root / Path(str(value).replace("/", "\\"))


def crop_to_aspect(image: Image.Image, width: int, height: int) -> Image.Image:
    target = width / height
    current = image.width / image.height
    if current < target:
        crop_height = int(round(image.width / target))
        top = max(0, (image.height - crop_height) // 2)
        return image.crop((0, top, image.width, top + crop_height))
    crop_width = int(round(image.height * target))
    left = max(0, (image.width - crop_width) // 2)
    return image.crop((left, 0, left + crop_width, image.height))


def review_sheet(root: Path, cuts: list[dict[str, Any]], output: Path) -> None:
    rows: list[tuple[str, list[tuple[str, Image.Image]]]] = []
    for cut in cuts:
        source = resolve(root, cut.get("sourcePath", ""))
        converted = resolve(root, cut.get("convertedPath", ""))
        runtime = resolve(root, cut.get("runtimeCapturePath", ""))
        if not source.exists():
            continue
        with Image.open(source) as image:
            source_image = image.convert("RGB")
        panels: list[tuple[str, Image.Image]] = [("source master", ImageOps.contain(source_image, (320, 240)))]
        purpose = str(cut.get("purpose", ""))
        if purpose == "messageSafeWide":
            safe = crop_to_aspect(source_image, 5, 3).resize((320, 192), Image.Resampling.LANCZOS)
            panels.append(("160x96 safe composition", safe))
        elif purpose == "fullscreenStill":
            safe = crop_to_aspect(source_image, 10, 9).resize((320, 288), Image.Resampling.LANCZOS)
            panels.append(("160x144 safe composition", safe))
        if converted.exists():
            with Image.open(converted) as image:
                panels.append(("native 160x144", image.convert("RGB").resize((320, 288), Image.Resampling.NEAREST)))
        if runtime.exists():
            with Image.open(runtime) as image:
                panels.append(("runtime capture", ImageOps.contain(image.convert("RGB"), (320, 288))))
        regions = list(cut.get("reviewRegions") or []) + list((cut.get("anatomy") or {}).get("forbiddenRegions") or [])
        for index, region in enumerate(regions[:4]):
            cx = source_image.width * float(region.get("xPercent", 50)) / 100
            cy = source_image.height * float(region.get("yPercent", 50)) / 100
            width = source_image.width * float(region.get("widthPercent", 24)) / 100
            height = source_image.height * float(region.get("heightPercent", 24)) / 100
            box = (max(0, int(cx - width / 2)), max(0, int(cy - height / 2)), min(source_image.width, int(cx + width / 2)), min(source_image.height, int(cy + height / 2)))
            label = str(region.get("label") or region.get("object") or f"region {index + 1}")
            panels.append((label, ImageOps.fit(source_image.crop(box), (180, 180))))
        rows.append((str(cut.get("id")), panels))
    if not rows:
        return
    width = max(sum(panel.width + 8 for _, panel in panels) + 8 for _, panels in rows)
    row_heights = [max(panel.height for _, panel in panels) + 52 for _, panels in rows]
    canvas = Image.new("RGB", (width, sum(row_heights)), (24, 28, 36))
    draw = ImageDraw.Draw(canvas)
    y = 0
    for (cut_id, panels), row_height in zip(rows, row_heights):
        draw.text((8, y + 4), cut_id, fill=(240, 240, 232))
        x = 8
        for label, panel in panels:
            draw.text((x, y + 22), label, fill=(190, 220, 210))
            canvas.paste(panel, (x, y + 44))
            x += panel.width + 8
        y += row_height
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate VN visual manifests and GBC conversion metrics; manual visual review remains mandatory.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--bible", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--review-sheet", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--max-palettes", type=int, default=7)
    parser.add_argument("--max-tiles", type=int, default=384)
    args = parser.parse_args()

    root = args.project_root.resolve()
    bible = load_json(args.bible)
    manifest = load_json(args.manifest)
    characters = {str(item.get("id")): item for item in bible.get("characters", [])}
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    metrics: dict[str, Any] = {}
    seen: set[str] = set()

    for cut in manifest.get("cuts", []):
        cut_id = str(cut.get("id", ""))
        if not cut_id or cut_id in seen:
            add_issue(errors, cut_id or "manifest", "cut-id", "cut IDs must be non-empty and unique")
            continue
        seen.add(cut_id)
        purpose = str(cut.get("purpose", ""))
        if purpose not in PURPOSE_SIZES:
            add_issue(errors, cut_id, "purpose", f"unsupported purpose: {purpose}")
            continue

        anatomy = cut.get("anatomy") or {}
        hands = anatomy.get("visibleHands") or []
        if any(int(item.get("count", -1)) < 0 or len(item.get("roles") or []) != int(item.get("count", 0)) for item in hands):
            add_issue(errors, cut_id, "visible-hands", "each visible hand needs exactly one declared role")
        for item in anatomy.get("forbiddenRegions") or []:
            x, y = float(item.get("xPercent", -1)), float(item.get("yPercent", -1))
            if not (0 <= x <= 100 and 0 <= y <= 100) or not item.get("object"):
                add_issue(errors, cut_id, "forbidden-region", "normalized coordinates and object are required")

        source = resolve(root, cut.get("sourcePath", ""))
        converted = resolve(root, cut.get("convertedPath", ""))
        runtime = resolve(root, cut.get("runtimeCapturePath", ""))
        if not source.exists():
            add_issue(errors, cut_id, "source", str(source))
            continue
        with Image.open(source) as image:
            if image.size != PURPOSE_SIZES[purpose]:
                add_issue(errors, cut_id, "source-size", f"expected {PURPOSE_SIZES[purpose]}, found {image.size}")
        actual_hash = sha256(source)
        if cut.get("sha256") and str(cut.get("sha256")).lower() != actual_hash:
            add_issue(errors, cut_id, "source-hash", "manifest SHA-256 does not match source")
        if cut.get("sourceContainsMessageWindow") is not False:
            add_issue(errors, cut_id, "source-window", "sourceContainsMessageWindow must be false")
        if cut.get("messageWindowBandIncluded") is not False:
            add_issue(errors, cut_id, "window-band", "messageWindowBandIncluded must be false")

        cut_metrics: dict[str, Any] = {"sourceSha256": actual_hash, "sourceSize": list(PURPOSE_SIZES[purpose])}
        if not converted.exists():
            add_issue(errors, cut_id, "converted", str(converted))
        else:
            with Image.open(converted) as image:
                rgb = image.convert("RGB")
            if rgb.size != (160, 144):
                add_issue(errors, cut_id, "converted-size", f"expected (160, 144), found {rgb.size}")
            tiles = image_tiles(rgb)
            max_colors = max((len(set(tile)) for tile in tiles), default=999)
            palettes = merged_palette_count(tiles)
            unique_tiles = len(set(tiles))
            cut_metrics.update({"convertedSize": list(rgb.size), "maxColorsPer8x8Tile": max_colors, "backgroundPalettes": palettes, "uniqueTiles": unique_tiles})
            if max_colors > 4:
                add_issue(errors, cut_id, "tile-colors", str(max_colors))
            if palettes > args.max_palettes:
                add_issue(errors, cut_id, "palettes", str(palettes))
            if unique_tiles > args.max_tiles:
                add_issue(errors, cut_id, "unique-tiles", str(unique_tiles))
            if purpose == "fullscreenStill" and len(set(rgb.crop((0, 112, 160, 144)).getdata())) < 6:
                add_issue(warnings, cut_id, "flat-lower-band", "fullscreen still lower edge may contain a legacy message band")

        expected_anchors: list[str] = []
        for entry in cut.get("characters") or []:
            character_id = str(entry.get("id", ""))
            outfit_id = str(entry.get("outfitId", ""))
            if not character_id or not outfit_id:
                add_issue(errors, cut_id, "character-lock", "character id and outfitId are required")
                continue
            character = characters.get(character_id)
            if not character:
                add_issue(errors, cut_id, "character-lock", f"character missing from bible: {character_id}")
                continue
            outfits = {str(item.get("id")): item for item in character.get("outfits", [])}
            outfit = outfits.get(outfit_id)
            if not outfit:
                add_issue(errors, cut_id, "outfit-lock", f"unknown outfit {character_id}:{outfit_id}")
                continue
            anchor_paths = list(map(str, character.get("identityAnchors") or [])) + [str(outfit.get("anchor", ""))]
            expected_anchors.extend(anchor_paths)
            if not all(anchor_paths):
                add_issue(errors, cut_id, "anchor", f"identity and outfit anchors are required for {character_id}")
            for anchor_path in anchor_paths:
                if anchor_path and not resolve(root, anchor_path).exists():
                    add_issue(errors, cut_id, "anchor", f"missing {anchor_path}")
        prompt_value = str(cut.get("promptPath", "")).strip()
        if not prompt_value:
            add_issue(errors, cut_id, "prompt", "promptPath is required")
        elif not resolve(root, prompt_value).exists():
            add_issue(errors, cut_id, "prompt", f"missing {prompt_value}")
        recorded_anchors = list(map(str, cut.get("referenceAnchors") or []))
        if recorded_anchors != expected_anchors:
            add_issue(errors, cut_id, "reference-anchors", f"expected {expected_anchors}, found {recorded_anchors}")
        if cut.get("accepted") and not str(cut.get("adoptionReason", "")).strip():
            add_issue(errors, cut_id, "adoption-reason", "accepted masters require a non-empty adoptionReason")

        qa = cut.get("qa") or {}
        for name in QA_NAMES:
            if qa.get(name) != "pass":
                add_issue(warnings, cut_id, f"qa-{name}", f"manual QA status is {qa.get(name, 'missing')}")
        if not cut.get("accepted"):
            add_issue(warnings, cut_id, "accepted", "selected master is not marked accepted")
        if not runtime.exists():
            add_issue(warnings, cut_id, "runtime-capture", str(runtime))
        metrics[cut_id] = cut_metrics

    blocking = bool(errors or (args.strict and warnings))
    report = {
        "status": "fail" if blocking else "pass",
        "strict": args.strict,
        "automatedAnatomyClaim": False,
        "metrics": metrics,
        "errors": errors,
        "warnings": warnings,
        "manualReviewRequired": ["full-resolution anatomy", "identity/outfit anchors", "native GBC composition", "runtime capture"],
    }
    write_json(args.report, report)
    if args.review_sheet:
        review_sheet(root, list(manifest.get("cuts", [])), args.review_sheet)
    print(json.dumps({"status": report["status"], "cuts": len(metrics), "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    if blocking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
