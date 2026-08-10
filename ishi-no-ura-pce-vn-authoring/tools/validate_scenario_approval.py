#!/usr/bin/env python3
"""Validate the approval front matter of a scenario-design.md file.

This intentionally validates only file-embedded approval. An explicit approval
in a current user message must be checked by the authoring agent itself.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_STATIC = {
    "workflow": "ishi-no-ura-pce-vn",
    "document_type": "scenario-design",
    "schema_version": "1",
    "approval_status": "APPROVED",
}


def parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("YAML front matter opening '---' was not found")

    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        raise ValueError("YAML front matter closing '---' was not found")

    data: dict[str, str] = {}
    for raw in lines[1:end]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = parse_scalar(value)
    return data


def validate(data: dict[str, str]) -> list[str]:
    errors: list[str] = []

    for key, expected in REQUIRED_STATIC.items():
        actual = data.get(key)
        if actual != expected:
            errors.append(f"{key}: expected {expected!r}, got {actual!r}")

    revision = data.get("revision", "")
    approved_revision = data.get("approved_revision", "")
    if not re.fullmatch(r"[1-9][0-9]*", revision):
        errors.append(f"revision must be a positive integer, got {revision!r}")
    if approved_revision != revision:
        errors.append(
            "approved_revision must match revision "
            f"({approved_revision!r} != {revision!r})"
        )

    approved_by = data.get("approved_by", "").strip()
    if not approved_by or approved_by.lower() in {"null", "none", "chatgpt", "assistant", "ai"}:
        errors.append("approved_by must identify a human approver")

    approved_at = data.get("approved_at", "").strip()
    if not approved_at or approved_at.lower() in {"null", "none"}:
        errors.append("approved_at must be set")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_design", type=Path)
    args = parser.parse_args()

    try:
        text = args.scenario_design.read_text(encoding="utf-8")
        data = parse_front_matter(text)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if errors:
        print("BLOCKED: HUMAN_APPROVAL_REQUIRED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "PASS: approved scenario design "
        f"episode={data.get('episode', '')} revision={data['revision']} "
        f"approved_by={data['approved_by']} approved_at={data['approved_at']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
