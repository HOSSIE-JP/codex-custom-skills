#!/usr/bin/env python3
"""Read-only structural and resource-reference validator for Godot projects."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys


SKIP_DIRS = {".git", ".hg", ".svn", ".godot", ".idea", ".vs", "build", "builds", "node_modules"}
DEV_DIRS = {"test", "tests", "tool", "tools"}
REFERENCE_EXTENSIONS = {
    ".gd", ".tscn", ".tres", ".godot", ".cfg", ".gdshader", ".json", ".csv",
    ".translation", ".import",
}
ASSET_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".tga", ".dds",
    ".wav", ".ogg", ".mp3", ".ogv", ".mp4", ".webm",
    ".gltf", ".glb", ".obj", ".dae", ".fbx",
    ".ttf", ".otf", ".woff", ".woff2",
    ".gdshader", ".tres", ".res", ".translation",
}
RES_REFERENCE_RE = re.compile(r"res://[^\"'\r\n\)\],}]+")
UID_REFERENCE_RE = re.compile(r"uid://[A-Za-z0-9]+")
WINDOWS_ABSOLUTE_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\"'\r\n]+")
UNIX_ABSOLUTE_RE = re.compile(r"(?<![:A-Za-z0-9_])/(?:home|Users|opt|var|tmp)/[^\"'\r\n]+")
SECTION_RE = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*$")
ASSIGNMENT_RE = re.compile(r"^(?P<key>[A-Za-z0-9_./-]+)\s*=")
MAIN_SCENE_RE = re.compile(r'^run/main_scene\s*=\s*"(?P<path>res://[^"]+)"', re.MULTILINE)
DYNAMIC_MARKERS = ("%s", "%d", "{", "}", "*", "${", '" +', "+ ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Godot project without modifying it."
    )
    parser.add_argument("root", type=Path, help="Godot project root")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a summary")
    parser.add_argument("--output", type=Path, help="Explicit report output path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 when validation errors are found",
    )
    parser.add_argument(
        "--max-examples", type=int, default=50, help="Maximum examples retained per finding"
    )
    parser.add_argument(
        "--include-dev",
        action="store_true",
        help="Also scan test and tool directories (excluded by default)",
    )
    return parser.parse_args()


def walk_files(root: Path, include_dev: bool):
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                name = entry.name.casefold()
                if name not in SKIP_DIRS and (include_dev or name not in DEV_DIRS):
                    pending.append(entry)
            elif entry.is_file():
                yield entry


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    for encoding in ("utf-8-sig", "utf-8", "cp932", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def clean_resource_reference(raw: str) -> str:
    value = raw.strip().rstrip(" ;")
    if "::" in value:
        value = value.split("::", 1)[0]
    return value


def contains_dynamic_marker(reference: str) -> bool:
    return any(marker in reference for marker in DYNAMIC_MARKERS)


def resolve_case(root: Path, relative_path: str) -> tuple[bool, str | None]:
    current = root
    corrected_parts: list[str] = []
    for part in Path(relative_path).parts:
        if part in {"", "."}:
            continue
        exact = current / part
        if exact.exists():
            corrected_parts.append(part)
            current = exact
            continue
        if not current.is_dir():
            return False, None
        try:
            matches = [child.name for child in current.iterdir() if child.name.casefold() == part.casefold()]
        except OSError:
            return False, None
        if not matches:
            return False, None
        chosen = sorted(matches)[0]
        corrected_parts.append(chosen)
        current = current / chosen
    corrected = Path(*corrected_parts).as_posix()
    return current.exists(), corrected


def parse_project_sections(project_text: str) -> tuple[list[str], list[str]]:
    section = ""
    autoloads: list[str] = []
    input_actions: list[str] = []
    for raw_line in project_text.splitlines():
        section_match = SECTION_RE.match(raw_line)
        if section_match:
            section = section_match.group("name")
            continue
        assignment = ASSIGNMENT_RE.match(raw_line.strip())
        if not assignment:
            continue
        key = assignment.group("key")
        if section == "autoload":
            autoloads.append(key)
        elif section == "input":
            input_actions.append(key)
    return sorted(autoloads), sorted(input_actions)


def validate(root: Path, max_examples: int, include_dev: bool) -> dict:
    project_file = root / "project.godot"
    errors: list[dict] = []
    warnings: list[dict] = []
    references: dict[str, list[dict]] = {}
    dynamic_references: list[dict] = []
    uid_references: Counter = Counter()
    absolute_paths: list[dict] = []
    zero_byte_assets: list[str] = []
    extension_counts: Counter = Counter()
    scanned_text_files = 0

    project_text = read_text(project_file) if project_file.is_file() else None
    main_scene = None
    autoloads: list[str] = []
    input_actions: list[str] = []
    if project_text is None:
        errors.append({"kind": "missing_project_file", "path": "project.godot"})
    else:
        main_match = MAIN_SCENE_RE.search(project_text)
        main_scene = main_match.group("path") if main_match else None
        autoloads, input_actions = parse_project_sections(project_text)
        if main_scene is None:
            errors.append({"kind": "missing_main_scene_setting", "path": "project.godot"})
        if not input_actions:
            warnings.append({"kind": "no_input_actions", "path": "project.godot"})

    for path in walk_files(root, include_dev):
        rel = relative(path, root)
        suffix = path.suffix.casefold()
        extension_counts[suffix or "<none>"] += 1
        if suffix in ASSET_EXTENSIONS:
            try:
                if path.stat().st_size == 0:
                    zero_byte_assets.append(rel)
            except OSError:
                pass
        if suffix not in REFERENCE_EXTENSIONS:
            continue
        text = read_text(path)
        if text is None:
            warnings.append({"kind": "unreadable_text_file", "path": rel})
            continue
        scanned_text_files += 1
        for match in RES_REFERENCE_RE.finditer(text):
            reference = clean_resource_reference(match.group(0))
            finding = {"source": rel, "line": line_number(text, match.start())}
            if contains_dynamic_marker(reference):
                dynamic_references.append({"reference": reference, **finding})
                continue
            references.setdefault(reference, []).append(finding)
        for match in UID_REFERENCE_RE.finditer(text):
            uid_references[match.group(0)] += 1
        for regex in (WINDOWS_ABSOLUTE_RE, UNIX_ABSOLUTE_RE):
            for match in regex.finditer(text):
                if len(absolute_paths) < max_examples:
                    absolute_paths.append(
                        {
                            "source": rel,
                            "line": line_number(text, match.start()),
                            "path": match.group(0).strip(),
                        }
                    )

    missing_references: list[dict] = []
    case_mismatches: list[dict] = []
    for reference, sources in sorted(references.items()):
        rel = reference[len("res://") :]
        exists, corrected = resolve_case(root, rel)
        if not exists:
            missing_references.append(
                {"reference": reference, "sources": sources[:max_examples]}
            )
        elif corrected is not None and corrected != Path(rel).as_posix():
            case_mismatches.append(
                {
                    "reference": reference,
                    "actual": "res://" + corrected,
                    "sources": sources[:max_examples],
                }
            )

    if missing_references:
        errors.append(
            {
                "kind": "missing_resource_references",
                "count": len(missing_references),
                "examples": missing_references[:max_examples],
            }
        )
    if case_mismatches:
        errors.append(
            {
                "kind": "resource_case_mismatches",
                "count": len(case_mismatches),
                "examples": case_mismatches[:max_examples],
            }
        )
    if absolute_paths:
        warnings.append(
            {
                "kind": "absolute_paths_in_project_text",
                "count": len(absolute_paths),
                "examples": absolute_paths,
            }
        )
    if dynamic_references:
        warnings.append(
            {
                "kind": "dynamic_resource_references_require_runtime_or_manifest_validation",
                "count": len(dynamic_references),
                "examples": dynamic_references[:max_examples],
            }
        )
    if zero_byte_assets:
        errors.append(
            {
                "kind": "zero_byte_assets",
                "count": len(zero_byte_assets),
                "examples": zero_byte_assets[:max_examples],
            }
        )

    return {
        "tool": "validate_godot_project.py",
        "analysis_mode": "read-only",
        "include_dev_directories": include_dev,
        "root": str(root),
        "result": "pass" if not errors else "fail",
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "scanned_text_files": scanned_text_files,
            "unique_resource_references": len(references),
            "missing_resource_references": len(missing_references),
            "case_mismatches": len(case_mismatches),
            "dynamic_resource_references": len(dynamic_references),
            "uid_references": sum(uid_references.values()),
            "zero_byte_assets": len(zero_byte_assets),
        },
        "project": {
            "main_scene": main_scene,
            "autoloads": autoloads,
            "input_actions": input_actions,
        },
        "extension_counts": dict(sorted(extension_counts.items())),
        "errors": errors,
        "warnings": warnings,
    }


def human_summary(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "Godot project validation (read-only)",
        f"Root: {report['root']}",
        f"Result: {report['result']}",
        f"Main scene: {report['project']['main_scene'] or '<missing>'}",
        f"Autoloads: {len(report['project']['autoloads'])}",
        f"Input actions: {len(report['project']['input_actions'])}",
        f"Resource references: {summary['unique_resource_references']}",
        f"Missing references: {summary['missing_resource_references']}",
        f"Case mismatches: {summary['case_mismatches']}",
        f"Dynamic references: {summary['dynamic_resource_references']}",
        f"Zero-byte assets: {summary['zero_byte_assets']}",
        f"Errors: {summary['errors']}; warnings: {summary['warnings']}",
    ]
    for finding in report["errors"]:
        lines.append(f"ERROR: {finding['kind']}")
    for finding in report["warnings"]:
        lines.append(f"WARNING: {finding['kind']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    report = validate(root, max(1, args.max_examples), args.include_dev)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else human_summary(report)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"wrote report: {output}")
    else:
        sys.stdout.write(rendered)
    if args.strict and report["result"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
