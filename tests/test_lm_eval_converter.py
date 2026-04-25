"""End-to-end: lm-eval sample -> envelope -> passes schema validation."""

from __future__ import annotations

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def test_lm_eval_round_trip(lm_eval_sample: dict) -> None:
    converter = get_converter("lm-eval")
    ctx = ConverterContext(
        suite="reasoning",
        model="mlx-community/Qwen3.5-9B-MLX-4bit",
        git_sha="deadbeef",
        system=detect_system(),
    )
    envelope = converter.build_envelope(lm_eval_sample, ctx)

    # Must validate against schema
    validate_envelope(envelope)

    # Results were built from the sample
    assert envelope["suite"] == "reasoning"
    assert envelope["model"] == "mlx-community/Qwen3.5-9B-MLX-4bit"
    results = envelope["results"]
    assert len(results) == 2, "expected one entry per non-stderr metric"
    metric_names = {r["metric"] for r in results}
    assert metric_names == {"exact_match_flexible", "exact_match_strict"}

    # Gen kwargs propagated
    assert envelope.get("gen_kwargs", {}).get("max_gen_toks") == 4096

    # Tags preserved original lm-eval key
    lm_keys = {r["tags"]["lm_eval_key"] for r in results}
    assert lm_keys == {"exact_match,flexible-extract", "exact_match,strict-match"}


def test_unknown_converter_kind_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown converter kind"):
        get_converter("no-such-tool")
