from __future__ import annotations

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def test_throughput_probe_round_trip() -> None:
    raw = {
        "model": "mlx-community/Qwen3.8-27B-4bit",
        "started_utc": "2026-08-24T11:41:57Z",
        "max_tokens": 256,
        "thinking": "off",
        "sequential_runs": 4,
        "sequential": {
            "n_ok": 4,
            "n_err": 0,
            "answered_rate": 1.0,
            "truncated_rate": 1.0,
            "finish_reasons": ["length"],
            "cumulative_tok_s": {"median": 54.11, "min": 51.84, "max": 56.13},
            "decode_tok_s": {"median": 42.97, "min": 41.35, "max": 44.53},
            "prefill_tok_s": {"median": 186.83, "min": 172.78, "max": 206.61},
            "ttft_s": {"median": 0.49, "min": 0.44, "max": 0.53},
            "total_s": {"median": 6.42, "min": 6.18, "max": 6.69},
        },
    }
    ctx = ConverterContext(
        suite="throughput",
        model=raw["model"],
        git_sha="deadbeef",
        concurrency=1,
        env_class="isolated",
        system=detect_system(),
    )

    envelope = get_converter("throughput-probe").build_envelope(raw, ctx)
    validate_envelope(envelope)

    by_metric = {result["metric"]: result for result in envelope["results"]}
    assert by_metric["throughput_total_toks_per_s"]["value"] == 54.11
    assert by_metric["throughput_output_toks_per_s"]["value"] == 42.97
    assert by_metric["ttft_p50_ms"]["value"] == 490.0
    assert by_metric["throughput_total_toks_per_s"]["tags"]["truncated_rate"] == "1.0"
    assert by_metric["throughput_total_toks_per_s"]["raw"] == raw["sequential"]
