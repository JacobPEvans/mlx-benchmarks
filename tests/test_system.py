"""Runtime system detection — smoke test that it returns a schema-shaped dict."""

from __future__ import annotations

import json

import pytest

from mlx_benchmarks.system import _detect_topology, detect_system

_TOPOLOGY_VARS = (
    "MLX_BENCH_WORLD_SIZE",
    "MLX_BENCH_PARALLELISM",
    "MLX_BENCH_INTERCONNECT",
    "MLX_BENCH_NODES",
)


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


def test_detect_topology_absent_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _TOPOLOGY_VARS:
        monkeypatch.delenv(var, raising=False)
    assert _detect_topology() is None


def test_detect_topology_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLX_BENCH_WORLD_SIZE", "2")
    monkeypatch.setenv("MLX_BENCH_PARALLELISM", "pipeline")
    monkeypatch.setenv("MLX_BENCH_INTERCONNECT", "tb5-rdma")
    monkeypatch.setenv(
        "MLX_BENCH_NODES",
        json.dumps([{"hostname": "node-0", "chip": "Apple M3 Ultra", "memory_gb": 256}]),
    )
    assert _detect_topology() == {
        "world_size": 2,
        "parallelism": "pipeline",
        "interconnect": "tb5-rdma",
        "nodes": [{"hostname": "node-0", "chip": "Apple M3 Ultra", "memory_gb": 256}],
    }


def test_detect_topology_ignores_malformed_nodes_json(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _TOPOLOGY_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MLX_BENCH_WORLD_SIZE", "2")
    monkeypatch.setenv("MLX_BENCH_NODES", "{not json")
    # Bad nodes JSON is dropped (warning logged), not fatal — world_size survives.
    assert _detect_topology() == {"world_size": 2}


def test_detect_topology_rejects_bad_parallelism(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _TOPOLOGY_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MLX_BENCH_PARALLELISM", "quantum")
    # Not in the schema enum, so it's ignored rather than emitted invalid.
    assert _detect_topology() is None
