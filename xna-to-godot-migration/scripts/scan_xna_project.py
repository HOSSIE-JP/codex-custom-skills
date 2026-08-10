#!/usr/bin/env python3
"""Read-only inventory scanner for XNA and MonoGame source projects."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


SKIP_TREE_DIRS = {".git", ".hg", ".svn", ".vs", ".idea", ".godot", "node_modules"}
GENERATED_DIRS = {"bin", "obj", "build", "builds", "packages"}
TEXT_EXTENSIONS = {
    ".cs", ".csproj", ".contentproj", ".mgcb", ".sln", ".config", ".xml",
    ".fx", ".hlsl", ".spritefont", ".json", ".txt", ".resx", ".targets",
    ".props",
}
PROJECT_EXTENSIONS = {".sln", ".csproj", ".contentproj", ".mgcb"}
ASSET_EXTENSIONS = {
    "images": {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga", ".dds", ".psd"},
    "audio": {".wav", ".ogg", ".mp3", ".wma", ".aiff", ".aif", ".xap", ".xgs", ".xwb", ".xsb"},
    "video": {".wmv", ".mp4", ".avi", ".mov", ".ogv", ".webm"},
    "models": {".x", ".fbx", ".obj", ".dae", ".3ds", ".gltf", ".glb"},
    "fonts": {".spritefont", ".ttf", ".otf"},
    "shaders": {".fx", ".hlsl", ".fxh"},
    "data": {".xml", ".json", ".csv", ".txt", ".resx"},
    "compiled_content": {".xnb"},
}

API_PATTERNS = {
    "framework": {
        "Microsoft.Xna.Framework": r"\bMicrosoft\.Xna\.Framework\b",
        "MonoGame.Framework": r"\bMonoGame\.Framework\b",
        "Game": r"\bGame\b",
        "GameComponent": r"\bGameComponent\b",
        "DrawableGameComponent": r"\bDrawableGameComponent\b",
    },
    "graphics": {
        "GraphicsDeviceManager": r"\bGraphicsDeviceManager\b",
        "GraphicsDevice": r"\bGraphicsDevice\b",
        "SpriteBatch": r"\bSpriteBatch\b",
        "Texture2D": r"\bTexture2D\b",
        "RenderTarget2D": r"\bRenderTarget2D\b",
        "SpriteFont": r"\bSpriteFont\b",
        "Model": r"\bModel(?:Mesh|Bone)?\b",
        "Effect": r"\b(?:BasicEffect|Effect)\b",
        "BlendState": r"\bBlendState\b",
        "SamplerState": r"\bSamplerState\b",
        "DepthStencilState": r"\bDepthStencilState\b",
        "RasterizerState": r"\bRasterizerState\b",
        "VertexBuffer/IndexBuffer": r"\b(?:VertexBuffer|IndexBuffer)\b",
    },
    "content": {
        "ContentManager": r"\bContentManager\b",
        "Content.Load": r"\.Load\s*<[^>]+>\s*\(",
        "Content Pipeline importer": r"\bContentImporter\b|\[ContentImporter",
        "Content Pipeline processor": r"\bContentProcessor\b|\[ContentProcessor",
        "Content Pipeline reader/writer": r"\bContentType(?:Reader|Writer)\b",
    },
    "input": {
        "Keyboard": r"\bKeyboard(?:State)?\b",
        "Mouse": r"\bMouse(?:State)?\b",
        "GamePad": r"\bGamePad(?:State|Capabilities)?\b",
        "Buttons/Keys": r"\b(?:Buttons|Keys)\.",
        "TouchPanel": r"\bTouchPanel\b",
        "Accelerometer": r"\bAccelerometer\b",
    },
    "audio_media": {
        "SoundEffect": r"\bSoundEffect(?:Instance)?\b",
        "Song/MediaPlayer": r"\b(?:Song|MediaPlayer)\b",
        "XACT": r"\b(?:AudioEngine|WaveBank|SoundBank|Cue)\b",
        "Video": r"\bVideo(?:Player)?\b",
    },
    "services_storage": {
        "GamerServices": r"\b(?:GamerServicesComponent|SignedInGamer|Gamer|Guide)\b",
        "Avatar": r"\bAvatar(?:Description|Renderer|Animation)?\b",
        "Marketplace/Trial": r"\b(?:Marketplace|TrialMode|IsTrialMode)\b",
        "StorageDevice": r"\bStorageDevice\b",
        "TitleContainer": r"\bTitleContainer\b",
        "NetworkSession": r"\bNetworkSession\b",
    },
    "timing_math": {
        "GameTime": r"\bGameTime\b",
        "TargetElapsedTime": r"\bTargetElapsedTime\b",
        "IsFixedTimeStep": r"\bIsFixedTimeStep\b",
        "System.Random": r"\bnew\s+Random\s*\(",
        "XNA Matrix/Vector": r"\b(?:Matrix|Vector2|Vector3|Quaternion)\b",
        "Bounding volumes": r"\b(?:BoundingBox|BoundingSphere|Ray)\b",
    },
}

CONTENT_LOAD_RE = re.compile(
    r"(?:\bContent|\bcontent|\bcontentManager|\bmanager)\s*\.\s*Load\s*<(?P<type>[^>]+)>\s*\((?P<arg>[^\r\n;]+?)\)",
    re.MULTILINE,
)
CLASS_RE = re.compile(
    r"\bclass\s+(?P<name>[A-Za-z_]\w*)\s*:\s*(?P<bases>[^\{\r\n]+)", re.MULTILINE
)
LIFECYCLE_RE = re.compile(
    r"\b(?:public|protected|private|internal)?\s*(?:override\s+|virtual\s+)?(?:void|bool)\s+"
    r"(?P<name>Initialize|LoadContent|UnloadContent|Update|Draw)\s*\(",
    re.MULTILINE,
)
STRING_LITERAL_RE = re.compile(r'^\s*@?"(?P<value>(?:""|\\.|[^"])*)"\s*$')
ABSOLUTE_WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\r\n\"']+)")
CONDITIONAL_RE = re.compile(r"^\s*#(?:if|elif)\s+(?P<symbol>.+?)\s*$", re.MULTILINE)
BACKBUFFER_RE = re.compile(r"PreferredBackBuffer(?P<axis>Width|Height)\s*=\s*(?P<value>\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan an XNA/MonoGame project without modifying it."
    )
    parser.add_argument("root", type=Path, help="XNA/MonoGame source root")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a summary")
    parser.add_argument("--output", type=Path, help="Explicit report output path")
    parser.add_argument(
        "--max-examples", type=int, default=25, help="Maximum example paths per category"
    )
    return parser.parse_args()


def read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        data = path.read_bytes()
    except OSError:
        return None, None
    for encoding in ("utf-8-sig", "utf-8", "cp932", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_generated(path: Path, root: Path) -> bool:
    return any(part.casefold() in GENERATED_DIRS for part in path.relative_to(root).parts[:-1])


def walk_files(root: Path):
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name.casefold() not in SKIP_TREE_DIRS:
                    pending.append(entry)
            elif entry.is_file():
                yield entry


def xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_content_project(path: Path, root: Path) -> tuple[list[dict], list[str]]:
    items: list[dict] = []
    errors: list[str] = []
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        return items, [f"{relative(path, root)}: {exc}"]
    for element in tree.iter():
        include = element.attrib.get("Include")
        if not include:
            continue
        kind = xml_local_name(element.tag)
        if kind not in {"Compile", "Content", "None"}:
            continue
        metadata = {
            xml_local_name(child.tag): (child.text or "").strip()
            for child in list(element)
            if (child.text or "").strip()
        }
        if kind == "Compile" or "Importer" in metadata or "Processor" in metadata:
            items.append(
                {
                    "project": relative(path, root),
                    "source": include.replace("\\", "/"),
                    "logical_name": metadata.get("Name", ""),
                    "importer": metadata.get("Importer", ""),
                    "processor": metadata.get("Processor", ""),
                    "processor_parameters": {
                        key: value
                        for key, value in metadata.items()
                        if key not in {"Name", "Importer", "Processor"}
                    },
                }
            )
    return items, errors


def parse_mgcb(path: Path, root: Path) -> list[dict]:
    text, _ = read_text(path)
    if text is None:
        return []
    items: list[dict] = []
    importer = ""
    processor = ""
    name = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#begin "):
            name = line[7:].strip()
        elif line.startswith("/importer:"):
            importer = line.split(":", 1)[1].strip()
        elif line.startswith("/processor:"):
            processor = line.split(":", 1)[1].strip()
        elif line.startswith("/build:") or line.startswith("/copy:"):
            value = line.split(":", 1)[1].strip()
            source, _, destination = value.partition(";")
            items.append(
                {
                    "project": relative(path, root),
                    "source": source.replace("\\", "/"),
                    "logical_name": destination or name,
                    "importer": importer,
                    "processor": processor,
                    "processor_parameters": {},
                }
            )
            importer = ""
            processor = ""
            name = ""
    return items


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def scan(root: Path, max_examples: int) -> dict:
    api_counts: dict[str, Counter] = defaultdict(Counter)
    api_files: dict[tuple[str, str], set[str]] = defaultdict(set)
    encodings: Counter = Counter()
    asset_counts: Counter = Counter()
    asset_bytes: Counter = Counter()
    asset_extensions: dict[str, Counter] = defaultdict(Counter)
    asset_examples: dict[str, list[str]] = defaultdict(list)
    project_files: list[str] = []
    source_files = 0
    content_loads: list[dict] = []
    component_classes: list[dict] = []
    lifecycle_methods: list[dict] = []
    content_items: list[dict] = []
    content_parse_errors: list[str] = []
    absolute_paths: list[dict] = []
    conditionals: dict[str, set[str]] = defaultdict(set)
    resolution_values: dict[str, list[dict]] = defaultdict(list)
    read_errors: list[str] = []

    for path in walk_files(root):
        rel = relative(path, root)
        suffix = path.suffix.casefold()
        if suffix in PROJECT_EXTENSIONS:
            project_files.append(rel)
        for category, extensions in ASSET_EXTENSIONS.items():
            if suffix in extensions:
                asset_counts[category] += 1
                try:
                    asset_bytes[category] += path.stat().st_size
                except OSError:
                    pass
                asset_extensions[category][suffix] += 1
                if len(asset_examples[category]) < max_examples:
                    asset_examples[category].append(rel)

        if suffix == ".contentproj":
            parsed, errors = parse_content_project(path, root)
            content_items.extend(parsed)
            content_parse_errors.extend(errors)
        elif suffix == ".mgcb":
            content_items.extend(parse_mgcb(path, root))

        if suffix not in TEXT_EXTENSIONS or is_generated(path, root):
            continue
        text, encoding = read_text(path)
        if text is None:
            read_errors.append(rel)
            continue
        encodings[encoding or "unknown"] += 1
        if suffix == ".cs":
            source_files += 1

        for category, patterns in API_PATTERNS.items():
            for name, pattern in patterns.items():
                matches = list(re.finditer(pattern, text))
                if matches:
                    api_counts[category][name] += len(matches)
                    api_files[(category, name)].add(rel)

        if suffix == ".cs":
            for match in CONTENT_LOAD_RE.finditer(text):
                argument = match.group("arg").strip()
                literal = STRING_LITERAL_RE.match(argument)
                content_loads.append(
                    {
                        "file": rel,
                        "line": line_number(text, match.start()),
                        "type": match.group("type").strip(),
                        "expression": argument,
                        "logical_name": literal.group("value") if literal else None,
                        "dynamic": literal is None,
                    }
                )
            for match in CLASS_RE.finditer(text):
                bases = [part.strip().split("<", 1)[0] for part in match.group("bases").split(",")]
                if any(
                    base.rsplit(".", 1)[-1] in {"Game", "GameComponent", "DrawableGameComponent"}
                    for base in bases
                ):
                    component_classes.append(
                        {
                            "file": rel,
                            "line": line_number(text, match.start()),
                            "class": match.group("name"),
                            "bases": bases,
                        }
                    )
            for match in LIFECYCLE_RE.finditer(text):
                lifecycle_methods.append(
                    {
                        "file": rel,
                        "line": line_number(text, match.start()),
                        "method": match.group("name"),
                    }
                )

        for match in ABSOLUTE_WINDOWS_PATH_RE.finditer(text):
            if len(absolute_paths) < max_examples * 4:
                absolute_paths.append(
                    {
                        "file": rel,
                        "line": line_number(text, match.start()),
                        "path": match.group(0),
                    }
                )
        for match in CONDITIONAL_RE.finditer(text):
            conditionals[match.group("symbol")].add(rel)
        for match in BACKBUFFER_RE.finditer(text):
            resolution_values[match.group("axis").casefold()].append(
                {
                    "value": int(match.group("value")),
                    "file": rel,
                    "line": line_number(text, match.start()),
                }
            )

    api_report = []
    for category in sorted(api_counts):
        for name, count in api_counts[category].most_common():
            api_report.append(
                {
                    "category": category,
                    "symbol": name,
                    "occurrences": count,
                    "files": len(api_files[(category, name)]),
                    "examples": sorted(api_files[(category, name)])[:max_examples],
                }
            )

    asset_report = {
        category: {
            "count": asset_counts[category],
            "bytes": asset_bytes[category],
            "extensions": dict(sorted(asset_extensions[category].items())),
            "examples": sorted(asset_examples[category]),
        }
        for category in sorted(asset_counts)
    }
    dynamic_loads = sum(1 for item in content_loads if item["dynamic"])
    platform_markers = sum(
        item["occurrences"] for item in api_report if item["category"] == "services_storage"
    )

    return {
        "tool": "scan_xna_project.py",
        "analysis_mode": "read-only",
        "root": str(root),
        "summary": {
            "project_files": len(project_files),
            "csharp_source_files": source_files,
            "content_pipeline_items": len(content_items),
            "content_loads": len(content_loads),
            "dynamic_content_loads": dynamic_loads,
            "component_classes": len(component_classes),
            "lifecycle_methods": len(lifecycle_methods),
            "platform_specific_markers": platform_markers,
            "absolute_path_examples": len(absolute_paths),
        },
        "project_files": sorted(project_files),
        "text_encodings": dict(encodings.most_common()),
        "api_dependencies": api_report,
        "component_classes": sorted(component_classes, key=lambda item: (item["file"], item["line"])),
        "lifecycle_methods": sorted(lifecycle_methods, key=lambda item: (item["file"], item["line"])),
        "content_loads": sorted(content_loads, key=lambda item: (item["file"], item["line"])),
        "content_pipeline_items": content_items,
        "assets": asset_report,
        "graphics": {"backbuffer_assignments": resolution_values},
        "conditional_compilation": {
            key: sorted(files)[:max_examples] for key, files in sorted(conditionals.items())
        },
        "absolute_path_references": absolute_paths,
        "warnings": {
            "dynamic_content_loads_require_manual_expansion": dynamic_loads,
            "content_parse_errors": content_parse_errors,
            "unreadable_text_files": read_errors[:max_examples],
        },
    }


def human_summary(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "XNA / MonoGame project scan (read-only)",
        f"Root: {report['root']}",
        f"Projects: {summary['project_files']}",
        f"C# source files: {summary['csharp_source_files']}",
        f"Component classes: {summary['component_classes']}",
        f"Content pipeline items: {summary['content_pipeline_items']}",
        f"Content.Load calls: {summary['content_loads']} ({summary['dynamic_content_loads']} dynamic)",
        f"Platform-specific markers: {summary['platform_specific_markers']}",
        f"Absolute path examples: {summary['absolute_path_examples']}",
        "",
        "API dependency groups:",
    ]
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in report["api_dependencies"]:
        grouped[item["category"]].append(f"{item['symbol']}={item['occurrences']}")
    for category in sorted(grouped):
        lines.append(f"  {category}: " + ", ".join(grouped[category]))
    lines.append("")
    lines.append("Asset inventory:")
    for category, item in report["assets"].items():
        lines.append(f"  {category}: {item['count']} files, {item['bytes']} bytes")
    if summary["dynamic_content_loads"]:
        lines.append("WARNING: Dynamic Content.Load expressions require manual expansion.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    report = scan(root, max(1, args.max_examples))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else human_summary(report)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"wrote report: {output}")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
