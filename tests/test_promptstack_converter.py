"""End-to-end: promptstack runner sample -> envelope -> passes schema validation."""

from __future__ import annotations

import pytest

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def _ctx(**overrides: object) -> ConverterContext:
    defaults: dict = {
        "suite": "promptstack",
        "model": "mlx-community/Qwen3.6-35B-A3B-4bit",
        "git_sha": "deadbeef",
        "system": detect_system(),
    }
    defaults.update(overrides)
    return ConverterContext(**defaults)


def test_promptstack_round_trip(promptstack_sample: dict) -> None:
    converter = get_converter("promptstack")
    envelope = converter.build_envelope(promptstack_sample, _ctx())

    validate_envelope(envelope)

    assert envelope["suite"] == "promptstack"
    assert envelope["timestamp"] == "2026-07-11T09:00:00Z"

    results = envelope["results"]
    assert all(r["name"] == "promptstack" for r in results)

    # 2 cells x 4 probe classes, each emitting task_success_rate + 2 token rows
    # + 2 latency rows, plus the class-specific extras (tool_call: +2,
    # instruction: +1, homelab_qa: +1).
    metric_names = [r["metric"] for r in results]
    assert metric_names.count("task_success_rate") == 8
    assert metric_names.count("valid_tool_call_rate") == 2
    assert metric_names.count("unsupported_claim_rate") == 4  # tool_call + homelab_qa, x2 cells
    assert metric_names.count("instruction_adherence_rate") == 2
    assert metric_names.count("tokens_prompt") == 8
    assert metric_names.count("tokens_completion") == 8
    assert metric_names.count("request_latency_p50_ms") == 8
    assert metric_names.count("request_latency_p95_ms") == 8


def test_promptstack_tags_carry_sweep_dimensions(promptstack_sample: dict) -> None:
    converter = get_converter("promptstack")
    envelope = converter.build_envelope(promptstack_sample, _ctx())
    validate_envelope(envelope)

    tool_call_base = [
        r
        for r in envelope["results"]
        if r["metric"] == "valid_tool_call_rate" and r["tags"]["prompt_variant"] == "base_plus_variant"
    ]
    assert len(tool_call_base) == 1
    result = tool_call_base[0]
    assert result["value"] == 0.75
    assert result["unit"] == "ratio"
    tags = result["tags"]
    assert tags["probe_class"] == "tool_call"
    assert tags["probe_bank_version"] == "1"
    assert tags["thinking"] == "on"
    assert tags["concurrency"] == "1"
    assert tags["n_tasks"] == "4"


def test_promptstack_adoption_comparison(promptstack_sample: dict) -> None:
    """The whole point: base_plus_variant vs current is comparable per probe class."""
    converter = get_converter("promptstack")
    envelope = converter.build_envelope(promptstack_sample, _ctx())

    reasoning_success = {
        r["tags"]["prompt_variant"]: r["value"]
        for r in envelope["results"]
        if r["metric"] == "task_success_rate" and r["tags"]["probe_class"] == "reasoning"
    }
    assert reasoning_success["base_plus_variant"] > reasoning_success["current"]


def test_promptstack_extra_tags(promptstack_sample: dict) -> None:
    converter = get_converter("promptstack")
    envelope = converter.build_envelope(promptstack_sample, _ctx(extra_tags={"host": "mac-studio"}))
    validate_envelope(envelope)
    assert all(r["tags"]["host"] == "mac-studio" for r in envelope["results"])


def test_promptstack_empty_cells_is_an_error() -> None:
    converter = get_converter("promptstack")
    with pytest.raises(ValueError, match="no cells"):
        converter.build_envelope({"cells": []}, _ctx())
