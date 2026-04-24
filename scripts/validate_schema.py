#!/usr/bin/env python3
"""Validate schema.json + all TOML configs.

Replaces the inline heredoc previously embedded in validate-schema.yml.
Runnable locally as ``scripts/validate_schema.py`` — no extra arguments.

Exit codes:
    0   schema is a valid Draft-07 JSON Schema and every TOML parses.
    1   schema is invalid.
    2   one or more TOML configs failed to parse.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema.json"
CONFIGS_ROOT = REPO_ROOT / "configs"


def _validate_schema() -> int:
    import json

    schema = json.loads(SCHEMA_PATH.read_text())
    try:
        Draft7Validator.check_schema(schema)
    except Exception as exc:
        print(f"FAIL: schema.json is not a valid Draft-07 JSON Schema: {exc}", file=sys.stderr)
        return 1

    print("ok: schema.json is a valid Draft-07 JSON Schema")
    print(f"    title: {schema.get('title')}")
    print(f"    $id: {schema.get('$id')}")
    print(f"    properties: {sorted(schema.get('properties', {}).keys())}")
    return 0


def _validate_tomls() -> int:
    errors: list[str] = []
    count = 0
    for path in sorted(CONFIGS_ROOT.rglob("*.toml")):
        count += 1
        try:
            tomllib.loads(path.read_text())
            print(f"ok: {path.relative_to(REPO_ROOT)}")
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: {exc}")

    if errors:
        print("\nTOML errors:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 2

    print(f"\nok: {count} TOML config(s) parsed cleanly")
    return 0


def main() -> int:
    schema_rc = _validate_schema()
    if schema_rc != 0:
        return schema_rc
    return _validate_tomls()


if __name__ == "__main__":
    sys.exit(main())
