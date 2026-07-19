"""End-to-end: vllm-mlx bench-serve sample -> envelope -> passes schema validation."""

from __future__ import annotations

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def _run(prompt_set: str, rep: int, gen_tps: float, ttft_ms: float, validated: bool) -> dict:
    return {
        "model_id": "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        "prompt_set": prompt_set,
        "concurrency": 1,
        "repetition": rep,
        "gen_tps": gen_tps,
        "throughput_tps": gen_tps + 10.0,
        "ttft_ms": ttft_ms,
        "tpot_ms": 7.5,
        "metal_peak_gb": 18.2,
        "validated": validated,
    }


def _sample() -> list[dict]:
    return [
        _run("short", 0, 131.0, 69.0, True),
        _run("short", 1, 130.9, 68.0, True),
        _run("short", 2, 131.5, 68.5, True),
        _run("long", 0, 108.7, 404.0, False),
        _run("long", 1, 108.1, 404.5, False),
        _run("long", 2, 108.0, 403.9, False),
    ]


def test_bench_serve_round_trip() -> None:
    converter = get_converter("bench-serve")
    ctx = ConverterContext(
        suite="throughput",
        model="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
        git_sha="deadbeef",
        concurrency=1,
        env_class="under-load",
        system=detect_system(),
    )
    envelope = converter.build_envelope(_sample(), ctx)

    validate_envelope(envelope)

    results = envelope["results"]
    # 2 groups (short, long) x 4 metrics
    assert len(results) == 8
    assert all(r["name"] == "bench_serve" for r in results)

    by_key = {(r["tags"]["prompt_set"], r["metric"]): r for r in results}
    short_tps = by_key[("short", "throughput_output_toks_per_s")]
    assert short_tps["value"] == 131.0  # median of 131.0 / 130.9 / 131.5
    assert short_tps["tags"]["repetitions"] == "3"
    assert short_tps["tags"]["validated"] == "true"
    assert short_tps["peak_rss_mb"] == 18.2 * 1024.0

    long_ttft = by_key[("long", "ttft_p50_ms")]
    assert long_ttft["value"] == 404.0
    assert long_ttft["tags"]["validated"] == "false"

    assert envelope["concurrency"] == 1
    assert envelope["env_class"] == "under-load"


def test_bench_serve_empty_list_yields_no_results() -> None:
    converter = get_converter("bench-serve")
    ctx = ConverterContext(
        suite="throughput",
        model="m",
        git_sha="deadbeef",
        system=detect_system(),
    )
    envelope = converter.build_envelope([], ctx)
    assert envelope["results"] == []
