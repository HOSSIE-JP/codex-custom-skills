from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

from PIL import Image

from pce_vn_common import ValidationError, load_json, path_record, sha256_file, write_json


def align(value: int, cell: int) -> int:
    return ((value + cell - 1) // cell) * cell


def validate_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ValidationError("sprite spec.rows must be a non-empty array")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValidationError(f"row {index} must be an object")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id or row_id in seen:
            raise ValidationError(f"row {index} needs a unique non-empty id")
        seen.add(row_id)
        if row.get("kind", "normal") not in {"normal", "mouth", "other"}:
            raise ValidationError(f"row {row_id} kind must be normal, mouth, or other")
        if not isinstance(row.get("frames"), list) or not row["frames"]:
            raise ValidationError(f"row {row_id} requires frames")
        kind = row.get("kind", "normal")
        pair_id = row.get("pairId")
        if kind == "mouth":
            if not pair_id or index == 0:
                raise ValidationError(f"mouth row {row_id} needs pairId and a preceding normal row")
            previous = rows[index - 1]
            if previous.get("kind", "normal") != "normal" or previous.get("pairId") != pair_id:
                raise ValidationError(f"mouth row {row_id} must immediately follow its paired normal row")
        if kind == "normal" and pair_id:
            if index + 1 >= len(rows):
                raise ValidationError(f"paired normal row {row_id} needs an adjacent mouth row")
            following = rows[index + 1]
            if following.get("kind") != "mouth" or following.get("pairId") != pair_id:
                raise ValidationError(f"paired normal row {row_id} must immediately precede its mouth row")
    return rows


def pack(spec_path: Path, sheet_path: Path, metadata_path: Path, force: bool = False) -> dict[str, Any]:
    if (sheet_path.exists() or metadata_path.exists()) and not force:
        existing = sheet_path if sheet_path.exists() else metadata_path
        raise ValidationError(f"Refusing to overwrite existing file: {existing}; pass --force explicitly")
    spec = load_json(spec_path)
    if not isinstance(spec, dict):
        raise ValidationError("sprite spec root must be an object")
    cell_size = spec.get("cellSize", 16)
    if cell_size != 16:
        raise ValidationError("PCE sprite cellSize must be 16")
    rows = validate_rows(spec.get("rows"))
    base = spec_path.resolve().parent
    loaded: list[list[tuple[Path, Image.Image]]] = []
    frame_width: int | None = None
    frame_height: int | None = None
    for row in rows:
        loaded_row: list[tuple[Path, Image.Image]] = []
        for raw_path in row["frames"]:
            if not isinstance(raw_path, str) or not raw_path:
                raise ValidationError(f"row {row['id']} contains an invalid frame path")
            frame_path = (base / raw_path).resolve()
            if frame_path.suffix.lower() != ".png":
                raise ValidationError(f"sprite frame must be PNG: {frame_path}")
            with Image.open(frame_path) as opened:
                if opened.mode != "RGBA":
                    raise ValidationError(f"sprite frame must be RGBA: {frame_path}")
                image = opened.copy()
            alpha = image.getchannel("A")
            if alpha.getextrema()[0] == 255:
                raise ValidationError(f"sprite frame has no transparent pixels: {frame_path}")
            if frame_width is None:
                frame_width, frame_height = image.size
            if image.size != (frame_width, frame_height):
                raise ValidationError(f"sprite frame size mismatch: {frame_path}")
            loaded_row.append((frame_path, image))
        loaded.append(loaded_row)
    assert frame_width is not None and frame_height is not None
    aligned_width = align(frame_width, cell_size)
    aligned_height = align(frame_height, cell_size)
    max_frames = max(len(row) for row in loaded)
    sheet_width = aligned_width * max_frames
    sheet_height = aligned_height * len(rows)
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    row_metadata = []
    cells_per_sheet_row = sheet_width // cell_size
    for row_index, (row, frames) in enumerate(zip(rows, loaded)):
        y = row_index * aligned_height
        frame_metadata = []
        for frame_index, (frame_path, image) in enumerate(frames):
            x = frame_index * aligned_width
            sheet.alpha_composite(image, (x, y))
            frame_metadata.append({
                **path_record(frame_path, base),
                "x": x,
                "y": y,
            })
        row_metadata.append({
            "id": row["id"],
            "kind": row.get("kind", "normal"),
            "pairId": row.get("pairId", ""),
            "y": y,
            "firstCell": (y // cell_size) * cells_per_sheet_row,
            "frameCount": len(frames),
            "frameStrideCells": aligned_width // cell_size,
            "frames": frame_metadata,
        })
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, format="PNG", optimize=False, compress_level=9)
    metadata = {
        "formatVersion": 1,
        "spec": path_record(spec_path),
        "sheet": {"path": sheet_path.name, "sha256": sha256_file(sheet_path)},
        "cellSize": cell_size,
        "frameWidth": frame_width,
        "frameHeight": frame_height,
        "alignedFrameWidth": aligned_width,
        "alignedFrameHeight": aligned_height,
        "width": sheet_width,
        "height": sheet_height,
        "rows": row_metadata,
        "animations": [
            {
                "id": row["id"],
                "firstCell": row["firstCell"],
                "frameCount": row["frameCount"],
                "frameStrideCells": row["frameStrideCells"],
            }
            for row in row_metadata
        ],
    }
    write_json(metadata_path, metadata, force)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministically assemble transparent PCE sprite frames and metadata.")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metadata-out", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        metadata = pack(args.spec, args.out, args.metadata_out, args.force)
        print(f"OK: {metadata['width']}x{metadata['height']} sprite sheet, {len(metadata['rows'])} rows")
    except (ValidationError, OSError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
