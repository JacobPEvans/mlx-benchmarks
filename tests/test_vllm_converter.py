"""End-to-end: vllm benchmark_serving sample -> envelope -> passes schema validation."""

from __future__ import annotations

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def test_vllm_round_trip(vllm_sample: dict) -> None:
    converter = get_converter("vllm")
    ctx = ConverterContext(
        suite="throughput",
        model="mlx-community/Qwen3.5-9B-MLX-4bit",
        git_sha="deadbeef",
        system=detect_system(),
    )
    envelope = converter.build_envelope(vllm_sample, ctx)

    validate_envelope(envelope)

    assert envelope["suite"] == "throughput"
    assert envelope["model"] == "mlx-community/Qwen3.5-9B-MLX-4bit"

    results = envelope["results"]
    assert len(results) > 0, "expected at least one result"

    metric_names = {r["metric"] for r in results}
    assert "throughput_output_toks_per_s" in metric_names
    assert "ttft_p50_ms" in metric_names
    assert "ttft_p99_ms" in metric_names
    assert "itl_p50_ms" in metric_names

    # All results share the same task name
    assert all(r["name"] == "benchmark_serving" for r in results)

    # Duration propagated from the raw sample (60.12 s)
    assert all(r.get("duration_seconds") == 60.12 for r in results)

    # Metadata tags propagated
    for result in results:
        tags = result.get("tags", {})
        assert tags.get("completed_requests") == "100"
        assert tags.get("total_input_tokens") == "25600"
        assert tags.get("total_output_tokens") == "25600"


def test_vllm_extra_tags(vllm_sample: dict) -> None:
    converter = get_converter("vllm")
    ctx = ConverterContext(
        suite="throughput",
        model="mlx-community/Qwen3.5-9B-MLX-4bit",
        git_sha="deadbeef",
        extra_tags={"input_len": "256", "output_len": "256"},
    )
    envelope = converter.build_envelope(vllm_sample, ctx)
    for result in envelope["results"]:
        tags = result.get("tags", {})
        assert tags.get("input_len") == "256"
        assert tags.get("output_len") == "256"


def test_vllm_missing_optional_metrics(vllm_sample: dict) -> None:
    converter = get_converter("vllm")
    ctx = ConverterContext(
        suite="throughput",
        model="some/model",
        git_sha="deadbeef",
        system=detect_system(),
    )
    sparse = {k: vllm_sample[k] for k in ("output_throughput", "median_ttft_ms", "p99_ttft_ms")}
    envelope = converter.build_envelope(sparse, ctx)
    validate_envelope(envelope)
    metric_names = {r["metric"] for r in envelope["results"]}
    assert "throughput_output_toks_per_s" in metric_names
    assert "tpot_p50_ms" not in metric_names  # not in sparse sample
