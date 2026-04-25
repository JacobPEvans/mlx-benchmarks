"""Runtime system detection — smoke test that it returns a schema-shaped dict."""

from __future__ import annotations

from mlx_benchmarks.system import detect_system


def test_detect_system_returns_required_fields() -> None:
    system = detect_system()
    for key in ("os", "chip", "memory_gb"):
        assert key in system, f"detect_system() must always set {key!r}"

    assert isinstance(system["os"], str) and system["os"]
    assert isinstance(system["chip"], str) and system["chip"]
    assert isinstance(system["memory_gb"], int)
    assert system["memory_gb"] >= 0


def test_detect_system_includes_python_version() -> None:
    import platform

    system = detect_system()
    assert system.get("python_version") == platform.python_version()
