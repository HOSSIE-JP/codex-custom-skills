#!/usr/bin/env python3
"""Validate rectangular GB Studio metasprite frames against source PNGs.

GB Studio stores tile X separately from the X shown by MetaspriteGrid. The
official 4.3.1 editor translates children by max(0, canvasWidth / 2 - 8).
Validation therefore tracks stored, editor-visible, and compiler-relative X.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageChops
except ImportError as exc:
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc

TILE_WIDTH = 8
TILE_HEIGHT = 16


def populated_frames(resource: dict[str, Any]):
    for state_index, state in enumerate(resource.get("states") or []):
        for animation_index, animation in enumerate(state.get("animations") or []):
            for frame_index, frame in enumerate(animation.get("frames") or []):
                tiles = frame.get("tiles") or []
                if tiles:
                    yield state_index, animation_index, frame_index, tiles


def fail(failures: list[str], path: Path, label: str, message: str) -> None:
    failures.append(f"{path}: {label}: {message}")


def editor_grid_offset_x(mode: str, canvas_width: int) -> int:
    normalized = mode.strip().lower()
    if normalized == "none":
        return 0
    if normalized != "auto":
        try:
            return int(normalized, 10)
        except ValueError as exc:
            raise ValueError("expected auto, none, or an integer") from exc

    offset = max(0.0, canvas_width / 2 - 8)
    if not offset.is_integer():
        raise ValueError(
            f"automatic editor offset is fractional ({offset}); pass an explicit integer"
        )
    return int(offset)


def parse_expected_x(value: str | None) -> tuple[int, ...] | None:
    if value is None:
        return None
    try:
        parsed = tuple(sorted({int(part.strip(), 10) for part in value.split(",")}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--expect-compiler-relative-x must be a comma-separated integer list"
        ) from exc
    if not parsed:
        raise argparse.ArgumentTypeError(
            "--expect-compiler-relative-x must contain at least one integer"
        )
    return parsed


def validate_resource(
    path: Path,
    coordinates_only: bool,
    required_frames: int | None,
    grid_offset_mode: str,
    expected_compiler_x: tuple[int, ...] | None,
) -> tuple[int, int, list[str], dict[str, Any]]:
    failures: list[str] = []
    try:
        resource = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return 0, 0, [f"{path}: cannot read resource: {exc}"], {}

    image_path = path.with_suffix("")
    if not image_path.is_file():
        return 0, 0, [f"{path}: source PNG not found at {image_path}"], {}

    canvas_width = int(resource.get("canvasWidth") or 0)
    canvas_height = int(resource.get("canvasHeight") or 0)
    canvas_origin_x = int(resource.get("canvasOriginX") or 0)
    if canvas_width <= 0 or canvas_height <= 0:
        return (
            0,
            0,
            [f"{path}: invalid Canvas size {canvas_width}x{canvas_height}"],
            {},
        )
    try:
        grid_offset_x = editor_grid_offset_x(grid_offset_mode, canvas_width)
    except ValueError as exc:
        return 0, 0, [f"{path}: invalid editor grid offset: {exc}"], {}

    image = Image.open(image_path).convert("RGBA")
    frames = list(populated_frames(resource))
    if required_frames is not None and len(frames) != required_frames:
        failures.append(
            f"{path}: expected {required_frames} populated frames, found {len(frames)}"
        )

    resource_stored_x: set[int] = set()
    resource_editor_x: set[int] = set()
    resource_compiler_x: set[int] = set()
    tile_total = 0
    for ordinal, (state_index, animation_index, frame_index, tiles) in enumerate(frames):
        label = (
            f"frame {ordinal} "
            f"(state {state_index}, animation {animation_index}, frame {frame_index})"
        )
        tile_total += len(tiles)
        x_offsets: set[int] = set()
        y_constants: set[int] = set()
        frame_compiler_x: set[int] = set()
        frame_failed = False

        for tile_index, tile in enumerate(tiles):
            try:
                stored_x = int(tile["x"])
                canvas_y = int(tile["y"])
                slice_x = int(tile["sliceX"])
                slice_y = int(tile["sliceY"])
            except (KeyError, TypeError, ValueError) as exc:
                fail(failures, path, label, f"tile {tile_index} has invalid coordinates: {exc}")
                frame_failed = True
                continue

            editor_x = stored_x + grid_offset_x
            compiler_x = stored_x - canvas_origin_x
            resource_stored_x.add(stored_x)
            resource_editor_x.add(editor_x)
            resource_compiler_x.add(compiler_x)
            frame_compiler_x.add(compiler_x)
            x_offsets.add(slice_x - editor_x)
            y_constants.add(slice_y + canvas_y)

            if editor_x < 0 or editor_x + TILE_WIDTH > canvas_width:
                fail(
                    failures,
                    path,
                    label,
                    f"tile {tile_index} editor Canvas x is out of bounds "
                    f"(stored={stored_x}, editor={editor_x}, offset={grid_offset_x})",
                )
                frame_failed = True
            top = canvas_height - TILE_HEIGHT - canvas_y
            if top < 0 or top + TILE_HEIGHT > canvas_height:
                fail(failures, path, label, f"tile {tile_index} Canvas y is out of bounds")
                frame_failed = True
            if (
                slice_x < 0
                or slice_y < 0
                or slice_x + TILE_WIDTH > image.width
                or slice_y + TILE_HEIGHT > image.height
            ):
                fail(failures, path, label, f"tile {tile_index} source slice is out of bounds")
                frame_failed = True

        if len(x_offsets) != 1:
            fail(
                failures,
                path,
                label,
                f"sliceX - editor Canvas x is not constant: {sorted(x_offsets)}",
            )
            frame_failed = True
        if len(y_constants) != 1:
            fail(
                failures,
                path,
                label,
                f"sliceY + Canvas y is not constant: {sorted(y_constants)}",
            )
            frame_failed = True
        if expected_compiler_x is not None and tuple(sorted(frame_compiler_x)) != expected_compiler_x:
            fail(
                failures,
                path,
                label,
                "compiler-relative x mismatch: "
                f"expected {list(expected_compiler_x)}, found {sorted(frame_compiler_x)}",
            )
            frame_failed = True

        if coordinates_only or frame_failed:
            continue

        source_left = next(iter(x_offsets))
        source_top = next(iter(y_constants)) - (canvas_height - TILE_HEIGHT)
        if (
            source_left < 0
            or source_top < 0
            or source_left + canvas_width > image.width
            or source_top + canvas_height > image.height
        ):
            fail(
                failures,
                path,
                label,
                f"derived source frame {source_left},{source_top},"
                f"{canvas_width},{canvas_height} is out of bounds",
            )
            continue

        reconstructed = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        for tile in tiles:
            editor_x = int(tile["x"]) + grid_offset_x
            canvas_y = int(tile["y"])
            slice_x = int(tile["sliceX"])
            slice_y = int(tile["sliceY"])
            tile_image = image.crop(
                (slice_x, slice_y, slice_x + TILE_WIDTH, slice_y + TILE_HEIGHT)
            )
            if tile.get("flipX"):
                tile_image = tile_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if tile.get("flipY"):
                tile_image = tile_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            reconstructed.alpha_composite(
                tile_image,
                (editor_x, canvas_height - TILE_HEIGHT - canvas_y),
            )

        expected = image.crop(
            (
                source_left,
                source_top,
                source_left + canvas_width,
                source_top + canvas_height,
            )
        )
        if ImageChops.difference(reconstructed, expected).getbbox() is not None:
            fail(failures, path, label, "reconstructed editor Canvas does not match source frame")

    details = {
        "canvas": [canvas_width, canvas_height],
        "canvas_origin_x": canvas_origin_x,
        "editor_grid_offset_x": grid_offset_x,
        "stored_x": sorted(resource_stored_x),
        "editor_x": sorted(resource_editor_x),
        "compiler_relative_x": sorted(resource_compiler_x),
    }
    return len(frames), tile_total, failures, details


def find_resources(root: Path, patterns: list[str]) -> list[Path]:
    if root.is_file():
        return [root]
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path for path in root.glob(pattern) if path.is_file())
    return sorted(found)


def unique_lists(values: set[tuple[int, ...]]) -> list[list[int]]:
    return [list(value) for value in sorted(values)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate GB Studio rectangular metasprite Canvas layout."
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root or one .gbsres file")
    parser.add_argument(
        "--pattern",
        action="append",
        help="Glob relative to root; repeatable (default: **/*.png.gbsres)",
    )
    parser.add_argument(
        "--require-populated-frames",
        type=int,
        help="Require this many populated frames in every resource",
    )
    parser.add_argument(
        "--coordinates-only",
        action="store_true",
        help="Check tile coordinate invariants without exact RGBA frame comparison",
    )
    parser.add_argument(
        "--editor-grid-offset-x",
        default="auto",
        metavar="auto|none|N",
        help=(
            "Horizontal editor child offset. auto uses max(0, canvasWidth/2-8); "
            "none preserves legacy stored-coordinate validation (default: auto)"
        ),
    )
    parser.add_argument(
        "--expect-compiler-relative-x",
        metavar="CSV",
        help="Require sorted unique storedX-canvasOriginX values in every populated frame",
    )
    args = parser.parse_args()

    try:
        expected_compiler_x = parse_expected_x(args.expect_compiler_relative_x)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    root = Path(args.root).resolve()
    patterns = args.pattern or ["**/*.png.gbsres"]
    resources = find_resources(root, patterns)
    if not resources:
        print(
            json.dumps(
                {"status": "fail", "failures": ["no matching .png.gbsres resources"]},
                ensure_ascii=False,
            )
        )
        return 1

    failures: list[str] = []
    frame_total = 0
    tile_total = 0
    offsets: set[int] = set()
    stored_sets: set[tuple[int, ...]] = set()
    editor_sets: set[tuple[int, ...]] = set()
    compiler_sets: set[tuple[int, ...]] = set()
    for resource in resources:
        frames, tiles, resource_failures, details = validate_resource(
            resource,
            args.coordinates_only,
            args.require_populated_frames,
            args.editor_grid_offset_x,
            expected_compiler_x,
        )
        frame_total += frames
        tile_total += tiles
        failures.extend(resource_failures)
        if details:
            offsets.add(int(details["editor_grid_offset_x"]))
            stored_sets.add(tuple(details["stored_x"]))
            editor_sets.add(tuple(details["editor_x"]))
            compiler_sets.add(tuple(details["compiler_relative_x"]))

    result = {
        "status": "pass" if not failures else "fail",
        "resources": len(resources),
        "populated_frames": frame_total,
        "tiles": tile_total,
        "coordinates_only": args.coordinates_only,
        "coordinate_spaces": {
            "editor_grid_offset_x": sorted(offsets),
            "stored_x": unique_lists(stored_sets),
            "editor_x": unique_lists(editor_sets),
            "compiler_relative_x": unique_lists(compiler_sets),
        },
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
