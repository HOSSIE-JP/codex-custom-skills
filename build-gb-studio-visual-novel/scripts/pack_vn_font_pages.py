#!/usr/bin/env python3
"""Pack atomic VN text units into code-aligned 8x8 GB Studio font pages."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import unicodedata
from typing import Any

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc


FIRST_FONT_CODE = 32
PHYSICAL_SLOTS = 224
RESERVED_CODES = {0x25: "runtime formatted-text prefix", 0x5C: "assembler escape prefix"}
SAFE_CODES = tuple(
    code for code in range(FIRST_FONT_CODE, 256) if code not in RESERVED_CODES
)
PAGE_WIDTH = 128
PAGE_HEIGHT = 112
TILE_SIZE = 8
FONT_PALETTE = (
    (0x07, 0x18, 0x21),
    (0x30, 0x68, 0x50),
    (0x86, 0xC0, 0x6C),
    (0xE0, 0xF8, 0xCF),
)


@dataclass(frozen=True)
class BdfGlyph:
    width: int
    height: int
    x_offset: int
    y_offset: int
    rows: tuple[int, ...]


@dataclass(frozen=True)
class TextUnit:
    unit_id: str
    texts: tuple[str, ...]
    characters: frozenset[str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def visible_characters(texts: tuple[str, ...], unit_id: str) -> frozenset[str]:
    characters: set[str] = set()
    for text in texts:
        for char in text:
            if char in "\r\n":
                continue
            if ord(char) < FIRST_FONT_CODE:
                raise ValueError(
                    f"unit {unit_id!r} contains unsupported control U+{ord(char):04X}"
                )
            characters.add(char)
    return frozenset(characters)


def parse_units_data(raw: Any) -> list[TextUnit]:
    if not isinstance(raw, dict) or not isinstance(raw.get("units"), list):
        raise ValueError('strings JSON must be an object containing a "units" array')

    units: list[TextUnit] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(raw["units"]):
        if not isinstance(record, dict):
            raise ValueError(f"units[{index}] must be an object")
        unit_id = record.get("id")
        texts = record.get("texts")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError(f"units[{index}].id must be a non-empty string")
        if unit_id in seen_ids:
            raise ValueError(f"duplicate unit id {unit_id!r}")
        if not isinstance(texts, list) or not texts or not all(
            isinstance(text, str) for text in texts
        ):
            raise ValueError(f"unit {unit_id!r} must contain a non-empty texts array")
        normalized = tuple(unicodedata.normalize("NFC", text) for text in texts)
        characters = visible_characters(normalized, unit_id)
        if len(characters) > len(SAFE_CODES):
            raise ValueError(
                f"unit {unit_id!r} needs {len(characters)} glyphs; "
                f"one page provides {len(SAFE_CODES)} safe codes"
            )
        seen_ids.add(unit_id)
        units.append(TextUnit(unit_id, normalized, characters))
    if not units:
        raise ValueError("strings JSON contains no units")
    return units


def load_units(path: Path) -> list[TextUnit]:
    return parse_units_data(json.loads(path.read_text(encoding="utf-8")))


def parse_bdf(path: Path) -> tuple[dict[int, BdfGlyph], int]:
    glyphs: dict[int, BdfGlyph] = {}
    ascent: int | None = None
    current: dict[str, Any] | None = None
    reading_bitmap = False

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8", errors="strict").splitlines(), start=1
    ):
        line = raw_line.strip()
        if current is None:
            if line.startswith("FONT_ASCENT "):
                ascent = int(line.split()[1])
            if line.startswith("STARTCHAR "):
                current = {"encoding": None, "bbx": None, "rows": []}
            continue

        if line.startswith("ENCODING "):
            current["encoding"] = int(line.split()[1])
        elif line.startswith("BBX "):
            parts = line.split()
            if len(parts) != 5:
                raise ValueError(f"invalid BBX at line {line_number}")
            current["bbx"] = tuple(int(value) for value in parts[1:])
        elif line == "BITMAP":
            reading_bitmap = True
        elif line == "ENDCHAR":
            encoding = current["encoding"]
            bbx = current["bbx"]
            rows = tuple(current["rows"])
            if isinstance(encoding, int) and encoding >= 0:
                if bbx is None:
                    raise ValueError(f"glyph {encoding} has no BBX")
                width, height, x_offset, y_offset = bbx
                if len(rows) != height:
                    raise ValueError(
                        f"glyph {encoding} declares height {height} but has {len(rows)} rows"
                    )
                if encoding in glyphs:
                    raise ValueError(f"duplicate BDF encoding {encoding}")
                glyphs[encoding] = BdfGlyph(
                    width, height, x_offset, y_offset, rows
                )
            current = None
            reading_bitmap = False
        elif reading_bitmap:
            try:
                current["rows"].append(int(line or "0", 16))
            except ValueError as exc:
                raise ValueError(f"invalid bitmap row at line {line_number}: {line!r}") from exc

    if current is not None:
        raise ValueError("unterminated BDF glyph")
    if not glyphs:
        raise ValueError("BDF contains no encoded glyphs")
    return glyphs, ascent if ascent is not None else TILE_SIZE


def pack_units(units: list[TextUnit]) -> tuple[list[set[str]], dict[str, int]]:
    pages: list[set[str]] = []
    assignments: dict[str, int] = {}
    ordered = sorted(units, key=lambda unit: (-len(unit.characters), unit.unit_id))

    for unit in ordered:
        candidates: list[tuple[int, int]] = []
        for page_index, page in enumerate(pages):
            if len(page | set(unit.characters)) <= len(SAFE_CODES):
                overlap = len(page & set(unit.characters))
                candidates.append((-overlap, page_index))
        if candidates:
            _, page_index = min(candidates)
        else:
            page_index = len(pages)
            pages.append(set())
        pages[page_index].update(unit.characters)
        assignments[unit.unit_id] = page_index

    return pages, assignments


def new_font_image() -> Image.Image:
    image = Image.new("P", (PAGE_WIDTH, PAGE_HEIGHT), 3)
    palette: list[int] = []
    for red, green, blue in FONT_PALETTE:
        palette.extend((red, green, blue))
    palette.extend([0] * (768 - len(palette)))
    image.putpalette(palette)
    return image


def draw_glyph(
    image: Image.Image,
    tile_index: int,
    glyph: BdfGlyph,
    ascent: int,
    character: str,
) -> None:
    if glyph.width > TILE_SIZE or glyph.height > TILE_SIZE:
        raise ValueError(
            f"glyph {character!r} U+{ord(character):04X} is "
            f"{glyph.width}x{glyph.height}, larger than 8x8"
        )
    tile_x = (tile_index % 16) * TILE_SIZE
    tile_y = (tile_index // 16) * TILE_SIZE
    top = ascent - glyph.height - glyph.y_offset
    row_bits = max(8, ((glyph.width + 7) // 8) * 8)

    for row_index, row_value in enumerate(glyph.rows):
        for column in range(glyph.width):
            if not row_value & (1 << (row_bits - 1 - column)):
                continue
            x = glyph.x_offset + column
            y = top + row_index
            if not (0 <= x < TILE_SIZE and 0 <= y < TILE_SIZE):
                raise ValueError(
                    f"glyph {character!r} U+{ord(character):04X} draws outside 8x8 "
                    f"at {x},{y}"
                )
            image.putpixel((tile_x + x, tile_y + y), 0)


def render_pages(
    pages: list[set[str]], glyphs: dict[int, BdfGlyph], ascent: int
) -> list[tuple[Image.Image, dict[str, int], str]]:
    missing = sorted(
        {char for page in pages for char in page if ord(char) not in glyphs},
        key=ord,
    )
    if missing:
        formatted = ", ".join(f"{char} U+{ord(char):04X}" for char in missing)
        raise ValueError(f"BDF is missing required glyphs: {formatted}")

    rendered: list[tuple[Image.Image, dict[str, int], str]] = []
    for page in pages:
        ordered_chars = "".join(sorted(page, key=ord))
        if len(ordered_chars) > len(SAFE_CODES):
            raise AssertionError("packed page exceeds safe code count")
        image = new_font_image()
        mapping: dict[str, int] = {}
        for character, code in zip(ordered_chars, SAFE_CODES):
            mapping[character] = code
            draw_glyph(
                image,
                code - FIRST_FONT_CODE,
                glyphs[ord(character)],
                ascent,
                character,
            )
        rendered.append((image, mapping, ordered_chars))
    return rendered


def prepare_output(output: Path, force: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    owned = sorted(output.glob("page_*.png")) + sorted(output.glob("page_*.json"))
    manifest = output / "font-pages-manifest.json"
    if manifest.exists():
        owned.append(manifest)
    if owned and not force:
        raise FileExistsError(
            f"output contains generated files; pass --force to replace them: {output}"
        )
    for path in owned:
        path.unlink()


def build(args: argparse.Namespace) -> dict[str, Any]:
    bdf = args.bdf.resolve()
    strings = args.strings.resolve()
    if not bdf.is_file():
        raise FileNotFoundError(f"BDF not found: {bdf}")
    if not strings.is_file():
        raise FileNotFoundError(f"strings JSON not found: {strings}")

    units = load_units(strings)
    bdf_glyphs, ascent = parse_bdf(bdf)
    pages, assignment_map = pack_units(units)
    rendered = render_pages(pages, bdf_glyphs, ascent)
    prepare_output(args.output.resolve(), args.force)

    page_records: list[dict[str, Any]] = []
    for page_index, (image, mapping, ordered_chars) in enumerate(rendered):
        png_path = args.output.resolve() / f"page_{page_index}.png"
        mapping_path = args.output.resolve() / f"page_{page_index}.json"
        image.save(png_path, optimize=True)
        write_json(
            mapping_path,
            {"name": f"{args.font_name} Page {page_index + 1}", "mapping": mapping},
        )
        page_records.append(
            {
                "page": page_index,
                "glyphs": ordered_chars,
                "glyphCount": len(ordered_chars),
                "codes": [mapping[char] for char in ordered_chars],
                "reservedCodes": sorted(RESERVED_CODES),
                "physicalSlots": PHYSICAL_SLOTS,
                "codeAlignedPhysicalTiles": True,
                "paletteIndexConvention": "glyph=0 background=3",
                "png": png_path.name,
                "pngSha256": sha256_file(png_path),
                "mapping": mapping_path.name,
                "mappingSha256": sha256_file(mapping_path),
            }
        )

    assignments = []
    for unit in sorted(units, key=lambda item: item.unit_id):
        normalized_blob = json.dumps(
            list(unit.texts), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        assignments.append(
            {
                "id": unit.unit_id,
                "page": assignment_map[unit.unit_id],
                "glyphCount": len(unit.characters),
                "textSha256": hashlib.sha256(normalized_blob).hexdigest(),
            }
        )

    manifest = {
        "formatVersion": 1,
        "fontName": args.font_name,
        "bdfFile": bdf.name,
        "bdfSha256": sha256_file(bdf),
        "stringsFile": strings.name,
        "stringsSha256": sha256_file(strings),
        "normalization": "NFC",
        "safeCodeCountPerPage": len(SAFE_CODES),
        "reservedCodes": {f"0x{code:02X}": reason for code, reason in RESERVED_CODES.items()},
        "physicalSlotsPerPage": PHYSICAL_SLOTS,
        "pages": page_records,
        "assignments": assignments,
    }
    write_json(args.output.resolve() / "font-pages-manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pack atomic VN text units into code-aligned GB Studio font pages."
    )
    parser.add_argument("--bdf", type=Path, required=True, help="8x8 Unicode BDF font")
    parser.add_argument(
        "--strings",
        type=Path,
        required=True,
        help='UTF-8 JSON object containing units [{"id":..., "texts":[...]}]',
    )
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--font-name", default="VN Font", help="Display-name prefix")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace only page_*.png, page_*.json, and font-pages-manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    try:
        manifest = build(parse_args())
    except Exception as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "pass",
                "pages": len(manifest["pages"]),
                "units": len(manifest["assignments"]),
                "safeCodesPerPage": manifest["safeCodeCountPerPage"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
