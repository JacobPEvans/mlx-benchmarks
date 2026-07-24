"""End-to-end: factual runner sample -> envelope -> passes schema validation."""

from __future__ import annotations

import pytest

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def _ctx(**overrides: object) -> ConverterContext:
    defaults: dict = {
        "suite": "grounded-summary",
        "model": "mlx-community/Qwen3.6-35B-A3B-4bit",
        "git_sha": "deadbeef",
        "system": detect_system(),
    }
    defaults.update(overrides)
    return ConverterContext(**defaults)


def test_factual_round_trip(factual_sample: dict) -> None:
    envelope = get_converter("factual").build_envelope(factual_sample, _ctx())
    validate_envelope(envelope)

    assert envelope["suite"] == "grounded-summary"
    assert envelope["timestamp"] == "2026-07-24T12:00:00Z"

    results = envelope["results"]
    assert all(r["name"] == "factual" for r in results)

    metrics = [r["metric"] for r in results]
    # 2 cells x (6 rate + 2 latency + 1 token) rows
    assert metrics.count("grounded_accuracy") == 2
    assert metrics.count("fabricated_number_rate") == 2
    assert metrics.count("tool_syntax_leak_rate") == 2
    assert metrics.count("request_latency_p95_ms") == 2
    assert metrics.count("tokens_completion") == 2


def test_thinking_and_bank_version_travel_as_tags(factual_sample: dict) -> None:
    envelope = get_converter("factual").build_envelope(factual_sample, _ctx())
    thinking_on = [
        r for r in envelope["results"] if r["metric"] == "grounded_accuracy" and r["tags"]["thinking"] == "on"
    ]
    assert len(thinking_on) == 1
    row = thinking_on[0]
    assert row["value"] == 0.92
    assert row["unit"] == "ratio"
    assert row["tags"]["fixture_bank_version"] == "1"
    assert row["tags"]["concurrency"] == "1"
    assert row["duration_seconds"] == 210.5


def test_extra_tags_are_carried(factual_sample: dict) -> None:
    envelope = get_converter("factual").build_envelope(
        factual_sample, _ctx(extra_tags={"env_class": "isolated"})
    )
    assert all(r["tags"]["env_class"] == "isolated" for r in envelope["results"])


def test_empty_cells_rejected() -> None:
    with pytest.raises(ValueError, match="no cells"):
        get_converter("factual").build_envelope({"cells": []}, _ctx())


def test_kind_is_registered() -> None:
    assert get_converter("factual").kind == "factual"
