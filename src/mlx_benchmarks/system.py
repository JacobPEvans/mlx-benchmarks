"""Runtime detection of ``system`` envelope fields.

Replaces the hardcoded laptop-specific dict that previously shipped in
``scripts/publish_run.py``. The old behavior published wrong metadata for any
contributor not using a specific M4 Max.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from functools import lru_cache
from importlib import metadata
from typing import Any


@lru_cache(maxsize=1)
def detect_system() -> dict[str, Any]:
    """Build a ``system`` dict reflecting the machine actually running the benchmark.

    The schema-required fields ``os`` / ``chip`` / ``memory_gb`` are always
    populated — when a detector fails they fall back to ``"unknown"`` or
    ``0`` rather than being omitted, because the schema rejects envelopes
    missing these keys. Optional fields (``python_version``, ``kernel``,
    and the package versions below) are only added when actually detected.
    Consumers should treat everything except ``os`` / ``chip`` /
    ``memory_gb`` as best-effort metadata.
    """
    data: dict[str, Any] = {
        "os": _detect_os(),
        "chip": _detect_chip(),
        "memory_gb": _detect_memory_gb(),
        "kernel": _detect_kernel(),
        "python_version": platform.python_version(),
    }

    for pkg_name, envelope_key in (
        ("mlx", "mlx_version"),
        ("mlx-lm", "mlx_lm_version"),
        ("lm-eval", "lm_eval_version"),
        ("vllm", "vllm_mlx_version"),
    ):
        version = _package_version(pkg_name)
        if version:
            data[envelope_key] = version

    runner = os.environ.get("RUNNER_NAME") or os.environ.get("GITHUB_RUNNER_LABEL")
    if runner:
        data["runner"] = runner

    return data


def _detect_os() -> str:
    if sys.platform == "darwin":
        mac_ver = platform.mac_ver()[0]
        if mac_ver:
            return f"macOS {mac_ver}"
    return platform.platform()


def _detect_chip() -> str:
    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=3
            ).strip()
            if out:
                return out
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    # Fallback for Linux/Windows: platform.processor() is often empty on macOS but useful elsewhere.
    return platform.processor() or platform.machine() or "unknown"


def _detect_memory_gb() -> int:
    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=3).strip()
            return round(int(out) / (1024**3))
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            pass
    try:
        import psutil

        return round(psutil.virtual_memory().total / (1024**3))
    except ImportError:
        return 0


def _detect_kernel() -> str:
    return platform.release() or "unknown"


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None
