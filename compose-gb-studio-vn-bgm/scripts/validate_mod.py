from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a four-channel ProTracker MOD and its loop/tempo contract.")
    parser.add_argument("--mod", type=Path, required=True)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    data = args.mod.read_bytes()
    errors: list[str] = []
    if len(data) < 1084:
        errors.append("file shorter than MOD header")
        song_length = 0
        pattern_count = 0
        sample_bytes = 0
        effects: list[tuple[int, int, int, int]] = []
    else:
        if data[1080:1084] != b"M.K.":
            errors.append("missing M.K. four-channel signature")
        song_length = data[950]
        if not 1 <= song_length <= 128:
            errors.append(f"invalid song length {song_length}")
        orders = list(data[952:1080])[:song_length]
        pattern_count = max(orders, default=-1) + 1
        sample_bytes = 0
        for instrument in range(31):
            offset = 20 + instrument * 30 + 22
            sample_bytes += int.from_bytes(data[offset:offset + 2], "big") * 2
        expected = 1084 + pattern_count * 1024 + sample_bytes
        if len(data) != expected:
            errors.append(f"length mismatch: expected {expected}, found {len(data)}")
        effects = []
        pattern_end = min(len(data), 1084 + pattern_count * 1024)
        cell_index = 0
        for offset in range(1084, pattern_end, 4):
            value = data[offset:offset + 4]
            if len(value) < 4:
                break
            effect, param = value[2] & 0x0F, value[3]
            if effect:
                pattern = cell_index // (64 * 4)
                within = cell_index % (64 * 4)
                effects.append((pattern, within // 4, within % 4, (effect << 8) | param))
            cell_index += 1

    spec = load_json(args.spec) if args.spec else {}
    bpm = int(spec.get("bpm", 0)) if spec else None
    bpm_hits = [value & 0xFF for _, _, _, value in effects if (value >> 8) == 0xF and (value & 0xFF) >= 32]
    loop_hits = [(pattern, row, channel) for pattern, row, channel, value in effects if value == 0xB00]
    if bpm is not None and bpm not in bpm_hits:
        errors.append(f"missing expected F{bpm:02X} BPM effect")
    if spec and pattern_count != len(spec.get("patterns") or []):
        errors.append(f"pattern count mismatch: expected {len(spec.get('patterns') or [])}, found {pattern_count}")
    if spec.get("loopRequired", True) and not loop_hits:
        errors.append("missing B00 loop effect")
    if loop_hits and loop_hits[-1][:2] != (pattern_count - 1, 63):
        errors.append(f"final B00 must be at pattern {pattern_count - 1} row 63")

    report = {"status": "fail" if errors else "pass", "path": str(args.mod), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "signature": data[1080:1084].decode("ascii", "replace") if len(data) >= 1084 else "", "channels": 4 if len(data) >= 1084 and data[1080:1084] == b"M.K." else None, "songLength": song_length, "patterns": pattern_count, "sampleBytes": sample_bytes, "bpmEffects": bpm_hits, "loopEffects": loop_hits, "errors": errors}
    write_json(args.report, report)
    print(json.dumps({"status": report["status"], "patterns": pattern_count, "errors": errors}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
