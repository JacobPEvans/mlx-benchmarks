"""promptfoo eval output -> envelope -> passes schema validation."""

from __future__ import annotations

from typing import Any

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def _ctx(**overrides: Any) -> ConverterContext:
    base: dict[str, Any] = {
        "suite": "capability-comparison",
        "model": "flagship-sweep",
        "git_sha": "deadbeef",
        "system": detect_system(),
    }
    base.update(overrides)
    return ConverterContext(**base)


def _by_model_metric(results: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    return {(r["name"], r["metric"]): r["value"] for r in results}


def test_promptfoo_round_trip(promptfoo_sample: dict) -> None:
    envelope = get_converter("promptfoo").build_envelope(promptfoo_sample, _ctx())
    validate_envelope(envelope)

    assert envelope["suite"] == "capability-comparison"
    results = envelope["results"]
    # 2 providers x (pass_rate + mean_score + 2 named metrics) = 8 rows
    assert len(results) == 8
    assert all(r["unit"] == "ratio" for r in results)


def test_promptfoo_aggregates_per_provider(promptfoo_sample: dict) -> None:
    envelope = get_converter("promptfoo").build_envelope(promptfoo_sample, _ctx())
    scores = _by_model_metric(envelope["results"])

    # baseline: 1 of 2 passed, scores 1.0 and 0.0
    assert scores[("baseline-gpt-oss-120b", "pass_rate")] == 0.5
    assert scores[("baseline-gpt-oss-120b", "mean_score")] == 0.5
    assert scores[("baseline-gpt-oss-120b", "coding_correctness")] == 1.0
    assert scores[("baseline-gpt-oss-120b", "agentic_planning")] == 0.0

    # candidate: both passed, scores 0.8 and 1.0
    assert scores[("candidate-qwen3-235b", "pass_rate")] == 1.0
    assert scores[("candidate-qwen3-235b", "mean_score")] == 0.9


def test_promptfoo_sets_model_tag(promptfoo_sample: dict) -> None:
    """Each row carries a ``model`` tag = the model under test, so downstream
    consumers (e.g. the Splunk model_eval alert) stay per-model even though the
    envelope-level model is the sweep label."""
    envelope = get_converter("promptfoo").build_envelope(promptfoo_sample, _ctx())
    for result in envelope["results"]:
        tags = result.get("tags", {})
        assert tags["model"] == result["name"]
        assert tags["n_tests"] == "2"


def test_promptfoo_extra_tags_propagate(promptfoo_sample: dict) -> None:
    envelope = get_converter("promptfoo").build_envelope(
        promptfoo_sample, _ctx(extra_tags={"sweep": "nightly"})
    )
    assert all(r.get("tags", {}).get("sweep") == "nightly" for r in envelope["results"])


def test_promptfoo_timestamp_from_output(promptfoo_sample: dict) -> None:
    envelope = get_converter("promptfoo").build_envelope(promptfoo_sample, _ctx())
    assert envelope["timestamp"] == "2026-05-01T12:00:00Z"


def test_promptfoo_empty_results_yields_no_rows() -> None:
    envelope = get_converter("promptfoo").build_envelope({"results": {"results": []}}, _ctx())
    validate_envelope(envelope)
    assert envelope["results"] == []


def test_promptfoo_handles_top_level_results_list(promptfoo_sample: dict) -> None:
    """Some callers persist the summary object directly (results at top level)."""
    flattened = {"results": promptfoo_sample["results"]["results"]}
    envelope = get_converter("promptfoo").build_envelope(flattened, _ctx())
    assert len(envelope["results"]) == 8
