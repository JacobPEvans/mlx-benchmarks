"""Unit tests for the throughput probe's pure functions.

``harness/throughput/run.py`` is a standalone PEP 723 script (not part of the
package), so it is loaded here via importlib. Its network dependency (httpx)
is imported lazily inside ``main()``, keeping the module — and these
pure-function tests — importable in the plain dev environment.

The cumulative-throughput fixtures below are real captured numbers (see PR
description / journal entry): decode-only throughput hides prefill gains, so
``cumulative_tok_s`` — (prompt + completion) tokens over wall-clock seconds —
is the headline metric, not ``decode_tok_s``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_runner() -> ModuleType:
    path = REPO_ROOT / "harness" / "throughput" / "run.py"
    spec = importlib.util.spec_from_file_location("throughput_run", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def test_prompt_for_context_defaults_to_the_canonical_short_prompt() -> None:
    assert runner.prompt_for_context(0) == runner.PROMPT


def test_prompt_for_context_is_deterministic_and_contains_requested_repetitions() -> None:
    prompt = runner.prompt_for_context(3)
    assert prompt.count("benchmark context variant-0 evidence ") == 3
    assert prompt.endswith("What is the shared theme?")


def test_context_variants_change_every_repeated_unit_to_defeat_prefix_caching() -> None:
    first = runner.prompt_for_context(3, variant=1)
    second = runner.prompt_for_context(3, variant=2)
    assert first != second
    assert first.count("variant-1") == 3
    assert second.count("variant-2") == 3


# --- cumulative_tok_s arithmetic (known-good captured data) -------------------


def test_cumulative_tok_s_gpt_oss_120b_mxfp4_q8() -> None:
    """gpt-oss-120b-MXFP4-Q8: 146 prompt + 512 completion tokens over 12.879s.

    Cumulative = 658 / 12.879 = 51.09 tok/s (~51.1 at one decimal, as reported
    in the rationale) versus the decode-only figure of 40.3 tok/s reported
    today — cumulative surfaces this model's much stronger prefill.
    """
    result = runner.cumulative_tok_s(146, 512, 12.879)
    assert result == pytest.approx(51.09, abs=0.01)
    assert round(result, 1) == 51.1


def test_cumulative_tok_s_qwen3_next_80b_a3b_thinking_4bit() -> None:
    """Qwen3-Next-80B-A3B-Thinking-4bit: 89 prompt + 512 completion over 46.813s.

    Cumulative = 601 / 46.813 = 12.84 tok/s (~12.8 at one decimal) versus the
    decode-only figure of 11.05 tok/s reported today.
    """
    result = runner.cumulative_tok_s(89, 512, 46.813)
    assert result == pytest.approx(12.84, abs=0.01)
    assert round(result, 1) == 12.8


def test_cumulative_tok_s_widens_the_model_gap() -> None:
    """The gap between the two models above widens from ~4x to ~4.5x under
    the cumulative metric, because gpt-oss's prefill is 4-6x better — this is
    the whole reason cumulative must be the headline: a decode-only number
    hides a real, consumer-visible difference."""
    gpt_oss = runner.cumulative_tok_s(146, 512, 12.879)
    qwen = runner.cumulative_tok_s(89, 512, 46.813)
    decode_only_ratio = 40.3 / 11.05
    cumulative_ratio = gpt_oss / qwen
    assert cumulative_ratio > decode_only_ratio


def test_cumulative_tok_s_handles_missing_tokens() -> None:
    assert runner.cumulative_tok_s(None, None, 12.879) is None
    assert runner.cumulative_tok_s(0, 0, 12.879) is None


def test_cumulative_tok_s_handles_non_positive_duration() -> None:
    assert runner.cumulative_tok_s(100, 100, 0) is None
    assert runner.cumulative_tok_s(100, 100, -1) is None


# --- summarize() reports cumulative_tok_s first, with median/min/max ---------


def test_summarize_reports_cumulative_tok_s_median_min_max() -> None:
    runs = [
        {
            "cumulative_tok_s": 51.09,
            "decode_tok_s": 40.3,
            "prefill_tok_s": 113.3,
            "ttft_s": 1.29,
            "total_s": 12.879,
        },
        {
            "cumulative_tok_s": 55.0,
            "decode_tok_s": 42.0,
            "prefill_tok_s": 120.0,
            "ttft_s": 1.20,
            "total_s": 12.0,
        },
        {
            "cumulative_tok_s": 48.0,
            "decode_tok_s": 38.0,
            "prefill_tok_s": 100.0,
            "ttft_s": 1.40,
            "total_s": 13.5,
        },
    ]
    summary = summarize_and_check(runner, runs)
    assert summary["cumulative_tok_s"] == {"median": 51.09, "min": 48.0, "max": 55.0}
    # decode/prefill remain as supporting detail, unaffected by the new field.
    assert summary["decode_tok_s"] == {"median": 40.3, "min": 38.0, "max": 42.0}


def test_summarize_key_order_is_headline_first() -> None:
    """``_SUMMARY_KEYS`` drives report order; cumulative_tok_s must lead."""
    assert runner._SUMMARY_KEYS[0] == "cumulative_tok_s"


def summarize_and_check(runner_mod: ModuleType, runs: list[dict]) -> dict:
    summary = runner_mod.summarize(runs)
    assert summary["n_ok"] == len(runs)
    return summary
