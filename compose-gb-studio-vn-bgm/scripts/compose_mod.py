from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


PERIODS = {
    1: [1712, 1616, 1524, 1440, 1356, 1280, 1208, 1140, 1076, 1016, 960, 906],
    2: [856, 808, 762, 720, 678, 640, 604, 570, 538, 508, 480, 453],
    3: [428, 404, 381, 360, 339, 320, 302, 285, 269, 254, 240, 226],
    4: [214, 202, 190, 180, 170, 160, 151, 143, 135, 127, 120, 113],
    5: [107, 101, 95, 90, 85, 80, 76, 71, 67, 64, 60, 57],
}
NOTES = {name: index for index, name in enumerate(("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"))}
DRUMS = {"kick": 16, "hat": 18, "snare": 18}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def period(note: str) -> int:
    match = __import__("re").fullmatch(r"([A-G](?:#)?)([1-5])", note)
    if not match or match.group(1) not in NOTES:
        raise ValueError(f"Unsupported MOD note: {note}")
    return PERIODS[int(match.group(2))][NOTES[match.group(1)]]


def cell(note: str | None = None, instrument: int = 0, effect: int = 0, param: int = 0) -> bytes:
    value = period(note) if note else 0
    return bytes([(instrument & 0xF0) | ((value >> 8) & 0x0F), value & 0xFF, ((instrument & 0x0F) << 4) | (effect & 0x0F), param & 0xFF])


def with_effect(value: bytes, effect: int, param: int) -> bytes:
    return bytes([value[0], value[1], (value[2] & 0xF0) | (effect & 0x0F), param & 0xFF])


def pick(values: list[Any], index: int, divisor: int = 1) -> Any:
    if not values:
        return None
    return values[(index // divisor) % len(values)]


def compose(spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    bpm = int(spec.get("bpm", 0))
    if not 32 <= bpm <= 255:
        raise ValueError("bpm must be between 32 and 255 for ProTracker Fxx tempo")
    patterns = spec.get("patterns") or []
    if not 1 <= len(patterns) <= 128:
        raise ValueError("patterns must contain 1..128 pattern definitions")

    pattern_bytes = bytearray()
    used_instruments: set[int] = set()
    for pattern_index, pattern_spec in enumerate(patterns):
        rows = [[cell() for _ in range(4)] for _ in range(64)]
        melody = list(pattern_spec.get("melody") or [])
        harmony = list(pattern_spec.get("harmony") or [])
        bass = list(pattern_spec.get("bass") or [])
        drums = list(pattern_spec.get("drums") or [])
        if len(melody) > 16 or len(drums) > 16:
            raise ValueError(f"pattern {pattern_index}: melody/drums support at most 16 steps")
        for step in range(16):
            row = step * 4
            melody_note = pick(melody, step)
            if melody_note:
                rows[row][0] = cell(str(melody_note), 1)
                used_instruments.add(1)
            harmony_note = pick(harmony, step, 4)
            if harmony_note:
                rows[row][1] = cell(str(harmony_note), 2)
                used_instruments.add(2)
            bass_note = pick(bass, step, 4)
            if bass_note:
                rows[row][2] = cell(str(bass_note), 3)
                used_instruments.add(3)
            drum = pick(drums, step)
            if drum:
                if str(drum) not in DRUMS:
                    raise ValueError(f"pattern {pattern_index}: unsupported drum {drum}")
                instrument = DRUMS[str(drum)]
                rows[row][3] = cell("C3", instrument)
                used_instruments.add(instrument)
        rows[0][0] = with_effect(rows[0][0], 0xF, bpm)
        if pattern_index == len(patterns) - 1 and bool(spec.get("loopRequired", True)):
            rows[-1][0] = with_effect(rows[-1][0], 0xB, 0)
        for row in rows:
            for value in row:
                pattern_bytes += value

    title = str(spec.get("title", spec.get("id", "Untitled"))).encode("ascii", "replace")[:20].ljust(20, b"\0")
    data = bytearray(title)
    for instrument in range(1, 32):
        data += f"GB INST {instrument:02d}".encode("ascii").ljust(22, b"\0")
        data += struct.pack(">HBBHH", 0, 0, 64, 0, 0)
    data += bytes([len(patterns), 0])
    data += bytes(list(range(len(patterns))) + [0] * (128 - len(patterns)))
    data += b"M.K."
    data += pattern_bytes
    expected = 1084 + len(patterns) * 1024
    if len(data) != expected:
        raise RuntimeError(f"invalid MOD length: expected {expected}, found {len(data)}")
    digest = hashlib.sha256(data).hexdigest()
    report = {"status": "pass", "id": spec.get("id"), "bytes": len(data), "sha256": digest, "bpm": bpm, "patterns": len(patterns), "channels": 4, "signature": "M.K.", "loopEffect": "B00" if spec.get("loopRequired", True) else None, "instruments": sorted(used_instruments)}
    return bytes(data), report


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose a deterministic original four-channel ProTracker MOD from JSON.")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--gbsres-out", type=Path)
    args = parser.parse_args()
    spec = load_json(args.spec)
    resource: dict[str, Any] | None = None
    if args.gbsres_out:
        resource = dict(spec.get("gbStudioResource") or {})
        required = ("id", "name", "symbol", "filename", "type")
        if any(not resource.get(key) for key in required) or str(resource.get("id", "")).startswith("replace-"):
            raise SystemExit("A real project-stable gbStudioResource id/name/symbol/filename/type is required")
        if resource.get("type") != "mod":
            raise SystemExit("gbStudioResource.type must be mod")
    data, report = compose(spec)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    write_json(args.report, report)
    if args.gbsres_out and resource is not None:
        write_json(args.gbsres_out, {"_resourceType": "music", **resource, "settings": resource.get("settings", {})})
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
