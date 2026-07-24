"""Unit tests for the shootout ranker.

The ranker never measures anything — it combines raw agentic + factual results —
so these tests pin the ordering contract: criterion priority, the quantization
that stops noise from deciding a rank, and the refusal to rank a model whose
suite coverage is incomplete.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlx_benchmarks.shootout import (
    RATE_RESOLUTION,
    Scored,
    collect,
    multiturn_survival,
    quantize,
    rank_key,
    render_markdown,
    score_agentic,
    score_factual,
)

GATE = "conc4_think-on_ctx-large"


def _row(model: str, **overrides: float | str | None) -> Scored:
    defaults: dict = {
        "gate_valid_rate": 1.0,
        "multiturn_survival": 1.0,
        "grounded_accuracy": 1.0,
        "fabricated_number_rate": 0.0,
        "latency_p50_ms": 1000.0,
        "first_token_p50_ms": 200.0,
        "factual_thinking": "on",
    }
    defaults.update(overrides)
    return Scored(model=model, **defaults)


# --- quantization -------------------------------------------------------------


def test_quantize_snaps_to_the_policy_resolution() -> None:
    assert quantize(0.94) == pytest.approx(0.9)
    assert quantize(0.96) == pytest.approx(1.0)
    assert RATE_RESOLUTION == 0.10


# --- multi-turn survival ------------------------------------------------------


def test_clean_track_survives_fully() -> None:
    assert multiturn_survival([{"rounds": [{}] * 20, "first_degraded_round": None}]) == 1.0


def test_degraded_track_scores_rounds_completed() -> None:
    assert multiturn_survival([{"rounds": [{}] * 20, "first_degraded_round": 5}]) == pytest.approx(0.2)


def test_worst_thinking_mode_wins() -> None:
    # A brain that only holds up in one thinking mode is a brain with a footgun.
    tracks = [
        {"rounds": [{}] * 20, "first_degraded_round": None},
        {"rounds": [{}] * 20, "first_degraded_round": 3},
    ]
    assert multiturn_survival(tracks) == pytest.approx(0.1)


def test_no_tracks_is_unknown_not_zero() -> None:
    assert multiturn_survival([]) is None


# --- criterion priority -------------------------------------------------------


def test_tool_fidelity_outranks_everything() -> None:
    strong_tools = _row("a", gate_valid_rate=1.0, grounded_accuracy=0.5, latency_p50_ms=9000.0)
    weak_tools = _row("b", gate_valid_rate=0.5, grounded_accuracy=1.0, latency_p50_ms=100.0)
    assert sorted([weak_tools, strong_tools], key=rank_key)[0].model == "a"


def test_factual_breaks_a_tool_fidelity_tie() -> None:
    better_facts = _row("a", grounded_accuracy=1.0, latency_p50_ms=9000.0)
    worse_facts = _row("b", grounded_accuracy=0.6, latency_p50_ms=100.0)
    assert sorted([worse_facts, better_facts], key=rank_key)[0].model == "a"


def test_latency_breaks_a_tie_on_both_accuracy_criteria() -> None:
    slow = _row("a", latency_p50_ms=9000.0)
    fast = _row("b", latency_p50_ms=100.0)
    assert sorted([slow, fast], key=rank_key)[0].model == "b"


def test_within_noise_accuracy_difference_falls_through_to_latency() -> None:
    # 0.98 vs 0.96 is inside the verdict policy's divergence threshold, so it
    # must not decide the rank; the much faster model wins instead.
    marginally_better = _row("a", grounded_accuracy=0.98, latency_p50_ms=9000.0)
    much_faster = _row("b", grounded_accuracy=0.96, latency_p50_ms=100.0)
    assert sorted([marginally_better, much_faster], key=rank_key)[0].model == "b"


def test_real_accuracy_gap_still_beats_latency() -> None:
    accurate = _row("a", grounded_accuracy=0.95, latency_p50_ms=9000.0)
    fast_and_loose = _row("b", grounded_accuracy=0.60, latency_p50_ms=100.0)
    assert sorted([fast_and_loose, accurate], key=rank_key)[0].model == "a"


def test_fabrication_rate_is_inverted() -> None:
    honest = _row("a", fabricated_number_rate=0.0, latency_p50_ms=9000.0)
    inventive = _row("b", fabricated_number_rate=0.4, latency_p50_ms=100.0)
    assert sorted([inventive, honest], key=rank_key)[0].model == "a"


# --- completeness -------------------------------------------------------------


def test_row_missing_a_suite_is_incomplete() -> None:
    assert _row("a").complete is True
    assert _row("b", grounded_accuracy=None).complete is False


def test_incomplete_rows_are_listed_but_not_ranked() -> None:
    out = render_markdown([_row("ranked"), _row("partial", grounded_accuracy=None)], GATE)
    assert "| 1 | ranked |" in out
    assert "Not ranked — incomplete suite coverage" in out
    assert "`partial`" in out
    assert "| 2 |" not in out


def test_markdown_states_the_provisional_rule() -> None:
    # Verdict policy: nothing produced here may read as a permanent judgment.
    out = render_markdown([_row("a")], GATE)
    assert "PROVISIONAL" in out
    assert GATE in out


# --- scoring raw runner output ------------------------------------------------


def test_score_agentic_reads_the_gate_cell(agentic_sample: dict) -> None:
    scored = score_agentic(agentic_sample, GATE)
    # The sample's gate cell scores 0.9, not a clean sweep — a fixture that is
    # perfect everywhere cannot show that the gate cell is the one being read.
    assert scored["gate_valid_rate"] == pytest.approx(0.9)
    assert scored["latency_p50_ms"] is not None
    # Sample tracks: one clean, one degrading at round 5 of 5 -> min 0.8.
    assert scored["multiturn_survival"] == pytest.approx(0.8)


def test_score_agentic_rejects_an_unmatched_gate(agentic_sample: dict) -> None:
    with pytest.raises(ValueError, match="no cell matches gate"):
        score_agentic(agentic_sample, "conc99_nonexistent")


def test_score_factual_takes_the_better_thinking_mode(factual_sample: dict) -> None:
    scored = score_factual(factual_sample)
    assert scored["grounded_accuracy"] == pytest.approx(0.92)
    assert scored["fabricated_number_rate"] == pytest.approx(0.04)
    assert scored["factual_thinking"] == "on"


def test_collect_joins_the_two_suites_on_model_id(
    tmp_path: Path, agentic_sample: dict, factual_sample: dict
) -> None:
    # Deliberately mismatched filenames: grouping is on the model field inside
    # the file, so an operator's naming choice cannot split one model in two.
    (tmp_path / "a.json").write_text(json.dumps(agentic_sample))
    (tmp_path / "zzz.json").write_text(json.dumps(factual_sample))

    rows = collect(sorted(tmp_path.glob("*.json")), GATE)
    assert len(rows) == 1
    assert rows[0].complete is True
    assert rows[0].grounded_accuracy == pytest.approx(0.92)
    assert rows[0].gate_valid_rate == pytest.approx(0.9)
