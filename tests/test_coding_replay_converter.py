"""End-to-end: coding-replay runner rows -> envelope -> passes schema validation."""

from __future__ import annotations

import pytest

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def _ctx(**overrides: object) -> ConverterContext:
    defaults: dict = {
        "suite": "coding",
        "model": "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        "git_sha": "deadbeef",
        "system": detect_system(),
    }
    defaults.update(overrides)
    return ConverterContext(**defaults)


def test_coding_replay_round_trip(coding_replay_sample: list[dict]) -> None:
    converter = get_converter("coding-replay")
    envelope = converter.build_envelope(coding_replay_sample, _ctx())
    validate_envelope(envelope)

    assert envelope["suite"] == "coding"
    assert envelope["timestamp"] == "2026-09-06T00:00:00Z"

    results = envelope["results"]
    assert all(r["name"] == "coding_replay" for r in results)
    metric_names = [r["metric"] for r in results]
    # 2 tasks -> 2 pass_at_1 rows + 1 aggregate pass_rate row.
    assert metric_names.count("pass_at_1") == 2
    assert metric_names.count("pass_rate") == 1


def test_coding_replay_pass_rate_is_the_headline_aggregate(coding_replay_sample: list[dict]) -> None:
    # Fixture: one passing task, one failing task -> pass_rate == 0.5.
    converter = get_converter("coding-replay")
    envelope = converter.build_envelope(coding_replay_sample, _ctx())
    validate_envelope(envelope)

    rate = next(r for r in envelope["results"] if r["metric"] == "pass_rate")
    assert rate["value"] == 0.5
    assert rate["unit"] == "ratio"
    assert rate["tags"]["n_tasks"] == "2"


def test_coding_replay_per_task_tags_and_duration(coding_replay_sample: list[dict]) -> None:
    converter = get_converter("coding-replay")
    envelope = converter.build_envelope(coding_replay_sample, _ctx())
    validate_envelope(envelope)

    passing = next(
        r
        for r in envelope["results"]
        if r["metric"] == "pass_at_1" and r["tags"]["task"] == "tofu-proxmox-1046"
    )
    assert passing["value"] == 1.0
    assert passing["tags"]["repo"] == "dryvist/tofu-proxmox"
    assert passing["tags"]["check"] == "none"
    assert passing["duration_seconds"] == 99.9

    failing = next(
        r
        for r in envelope["results"]
        if r["metric"] == "pass_at_1" and r["tags"]["task"] == "tofu-proxmox-1049"
    )
    assert failing["value"] == 0.0
    assert failing["tags"]["overlap"] == "0"


def test_coding_replay_extra_tags(coding_replay_sample: list[dict]) -> None:
    converter = get_converter("coding-replay")
    envelope = converter.build_envelope(coding_replay_sample, _ctx(extra_tags={"host": "mac-studio"}))
    validate_envelope(envelope)
    assert all(r["tags"]["host"] == "mac-studio" for r in envelope["results"])


def test_coding_replay_passes_through_run_context(coding_replay_sample: list[dict]) -> None:
    converter = get_converter("coding-replay")
    envelope = converter.build_envelope(
        coding_replay_sample, _ctx(env_class="isolated", serving={"stack": "mlx_lm.server"})
    )
    validate_envelope(envelope)
    assert envelope["env_class"] == "isolated"
    assert envelope["serving"] == {"stack": "mlx_lm.server"}


def test_coding_replay_empty_rows_is_an_error() -> None:
    converter = get_converter("coding-replay")
    with pytest.raises(ValueError, match="nothing to publish"):
        converter.build_envelope([], _ctx())


def test_coding_replay_accepts_a_single_dict_row() -> None:
    # cli.py only splits .jsonl input on newlines into a list; a lone dict
    # (e.g. a hand-built raw result) must still convert.
    converter = get_converter("coding-replay")
    row = {"task": "x-1", "repo": "o/x", "check": "none", "check_rc": 0, "overlap": 1, "pass": True}
    envelope = converter.build_envelope(row, _ctx())
    validate_envelope(envelope)
    assert len(envelope["results"]) == 2
