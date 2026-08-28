#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def load_windows(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("window inventory must be an object keyed by physical model id")
    windows: dict[str, int] = {}
    for model, window in payload.items():
        if not isinstance(model, str) or not model:
            raise ValueError("window inventory keys must be non-empty model ids")
        if not isinstance(window, int) or isinstance(window, bool) or window < 1:
            raise ValueError(f"window inventory value for {model} must be a positive integer")
        windows[model] = window
    return windows


def fetch_models(base_url: str) -> set[str]:
    url = base_url.rstrip("/") + "/models"
    try:
        with urlopen(url, timeout=10) as response:
            payload: Any = json.loads(response.read())
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read live model inventory from {url}: {exc}") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise RuntimeError(f"live model inventory from {url} has no data array")
    return {row["id"] for row in data if isinstance(row, dict) and isinstance(row.get("id"), str)}


def build_manifest(
    campaign_id: str,
    output_root: str,
    base_url: str,
    windows: dict[str, int],
    live_models: set[str],
) -> dict[str, Any]:
    return {
        "campaign_id": campaign_id,
        "output_root": output_root,
        "base_url": base_url,
        "defaults": {
            "targets": [32000, 64000, 128000, 192000],
            "configured_windows": [32768, 65536, 131072, 196608],
            "output_tokens": 512,
            "repeats": 4,
            "concurrency": 1,
        },
        "profiles": [
            {"model": model, "window_limit_tokens": windows[model]}
            for model in sorted(live_models & windows.keys())
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a context campaign manifest from evaluated window limits and live serving inventory."
    )
    parser.add_argument("--windows-json", required=True, type=Path)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--output-root", default="~/bench-runs")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(
            args.campaign_id,
            args.output_root,
            args.base_url,
            load_windows(args.windows_json),
            fetch_models(args.base_url),
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
