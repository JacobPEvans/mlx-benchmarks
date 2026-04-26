"""End-to-end: framework-eval sample -> envelope -> passes schema validation."""

from __future__ import annotations

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def test_framework_eval_round_trip(framework_eval_sample: dict) -> None:
    converter = get_converter("framework-eval")
    ctx = ConverterContext(
        suite="framework-eval",
        model="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        git_sha="deadbeef",
        system=detect_system(),
    )
    envelope = converter.build_envelope(framework_eval_sample, ctx)

    validate_envelope(envelope)

    assert envelope["suite"] == "framework-eval"
    assert envelope["model"] == "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"

    results = envelope["results"]
    assert len(results) == 4  # score + latency + tokens + steps

    metric_names = {r["metric"] for r in results}
    assert metric_names == {"score", "latency", "tokens", "steps"}

    # All results share the framework name
    framework_names = {r["name"] for r in results}
    assert framework_names == {"OpenAI tool-calling (baseline)"}

    # Score is 1.0 (non-error answer)
    score_result = next(r for r in results if r["metric"] == "score")
    assert score_result["value"] == 1.0
    assert score_result["unit"] == "bool"

    # Latency carried through
    latency_result = next(r for r in results if r["metric"] == "latency")
    assert latency_result["value"] == 8.43
    assert latency_result["unit"] == "seconds"
    assert latency_result.get("duration_seconds") == 8.43


def test_framework_eval_error_answer_scores_zero(framework_eval_sample: dict) -> None:
    converter = get_converter("framework-eval")
    ctx = ConverterContext(
        suite="framework-eval",
        model="some/model",
        git_sha="deadbeef",
        system=detect_system(),
    )
    error_sample = {**framework_eval_sample, "answer": "Error: tool call failed"}
    envelope = converter.build_envelope(error_sample, ctx)
    score_result = next(r for r in envelope["results"] if r["metric"] == "score")
    assert score_result["value"] == 0.0


def test_framework_eval_sparse_sample(framework_eval_sample: dict) -> None:
    converter = get_converter("framework-eval")
    ctx = ConverterContext(
        suite="framework-eval",
        model="some/model",
        git_sha="deadbeef",
        system=detect_system(),
    )
    # smolagents-style output: no tool_calls, tokens, or steps
    sparse = {"framework": "smolagents (ToolCallingAgent)", "answer": "The fox jumps.", "latency": 5.2}
    envelope = converter.build_envelope(sparse, ctx)
    validate_envelope(envelope)

    metric_names = {r["metric"] for r in envelope["results"]}
    assert metric_names == {"score", "latency"}
    assert "tokens" not in metric_names
    assert "steps" not in metric_names
