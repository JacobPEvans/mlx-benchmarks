from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_generator() -> ModuleType:
    path = REPO_ROOT / "scripts" / "generate-context-inventory.py"
    spec = importlib.util.spec_from_file_location("context_inventory", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def test_manifest_intersects_evaluated_windows_with_live_models() -> None:
    manifest = generator.build_manifest(
        "campaign-a",
        "/tmp/runs",
        "http://127.0.0.1:11434/v1",
        {"enabled": 131072, "disabled": 65536},
        {"enabled", "foreign"},
    )
    assert manifest["profiles"] == [
        {
            "model": "enabled",
            "window_limit_tokens": 131072,
            "catalog_max_tokens": 131072,
        }
    ]
    assert manifest["defaults"]["targets"] == [32000, 64000, 128000, 192000]
