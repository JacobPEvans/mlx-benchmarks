"""End-to-end: lm-eval sample -> envelope -> passes schema validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.converters.lm_eval import LmEvalConverter
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


@dataclass(slots=True)
class _FakeEncoding:
    ids: list[int]


class _WhitespaceTokenizer:
    """Stand-in for an HF tokenizer in tests — splits on whitespace.

    Avoids any HF network access or filesystem cache dependency. One "token"
    per whitespace-separated word is sufficient to verify the converter's
    accounting math.
    """

    def encode(self, text: str) -> _FakeEncoding:
        return _FakeEncoding(ids=text.split())  # type: ignore[arg-type]


_FIXTURES = Path(__file__).parent / "fixtures"


def test_lm_eval_populates_tokens_per_second(tmp_path: Path) -> None:
    """When source_path points at a results_*.json with a sibling samples_*.jsonl
    and a working tokenizer, the converter writes aggregate tok/s fields to the
    result. Numbers are computed against the fake whitespace tokenizer:

      Per sample (3 total):
        prompt  "What is 2 + 2?"  -> 5 tokens (split on whitespace)
        resp    "The answer is 4." -> 4 tokens
      Totals: prompt=15, response=12, duration=100s
      Expected: prompt_tok_s=0.15, decode_tok_s=0.12, total_tok_s=0.27
    """
    source = _FIXTURES / "lm_eval_with_samples" / "results_2026-05-13T00-00-00.000000.json"
    raw = json.loads(source.read_text())

    converter = LmEvalConverter(tokenizer_loader=lambda _model: _WhitespaceTokenizer())
    ctx = ConverterContext(
        suite="reasoning",
        model="mlx-community/Qwen3.5-9B-MLX-4bit",
        git_sha="deadbeef",
        system=detect_system(),
        source_path=source,
    )

    envelope = converter.build_envelope(raw, ctx)
    validate_envelope(envelope)
    [result] = envelope["results"]
    assert result["duration_seconds"] == 100.0
    assert result["prompt_tokens_per_second"] == 15 / 100.0
    assert result["decode_tokens_per_second"] == 12 / 100.0
    assert result["total_tokens_per_second"] == 27 / 100.0


def test_lm_eval_skips_throughput_without_source_path() -> None:
    """Library callers that don't supply ``source_path`` still get a valid
    envelope — tok/s fields are simply absent."""
    source = _FIXTURES / "lm_eval_with_samples" / "results_2026-05-13T00-00-00.000000.json"
    raw = json.loads(source.read_text())

    converter = LmEvalConverter(tokenizer_loader=lambda _model: _WhitespaceTokenizer())
    ctx = ConverterContext(
        suite="reasoning",
        model="mlx-community/Qwen3.5-9B-MLX-4bit",
        git_sha="deadbeef",
        system=detect_system(),
        # source_path intentionally omitted
    )
    envelope = converter.build_envelope(raw, ctx)
    validate_envelope(envelope)
    [result] = envelope["results"]
    assert "duration_seconds" in result
    assert "decode_tokens_per_second" not in result


def test_lm_eval_skips_throughput_when_tokenizer_unavailable() -> None:
    """When the tokenizer loader returns None (HF offline, missing repo, etc.)
    the converter degrades gracefully — duration still set, tok/s fields not."""
    source = _FIXTURES / "lm_eval_with_samples" / "results_2026-05-13T00-00-00.000000.json"
    raw = json.loads(source.read_text())

    converter = LmEvalConverter(tokenizer_loader=lambda _model: None)
    ctx = ConverterContext(
        suite="reasoning",
        model="mlx-community/Qwen3.5-9B-MLX-4bit",
        git_sha="deadbeef",
        system=detect_system(),
        source_path=source,
    )
    envelope = converter.build_envelope(raw, ctx)
    [result] = envelope["results"]
    assert result["duration_seconds"] == 100.0
    assert "decode_tokens_per_second" not in result
