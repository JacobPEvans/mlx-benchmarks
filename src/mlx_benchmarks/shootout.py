"""Rank models across the three agent-brain criteria from raw suite output.

The shootout asks one question — which model should be the resident brain — and
answers it from two raw result files per model: an ``agentic`` run (tool-call
fidelity and latency) and a ``factual`` run (grounded summarization). Nothing
here re-measures anything; it only combines what the runners already scored, so
the ranking is reproducible from the same JSONs by anyone.

Ordering is **lexicographic by the stated criterion priority**, not a weighted
sum — a weighted sum would smuggle in per-criterion importance numbers nobody
agreed to:

1. tool-call fidelity — gate-cell ``valid_tool_call_rate``, then multi-turn
   survival (``docs/agentic.md``: single-shot validity alone is not a passing
   agentic verdict, the degradation track is the discriminator)
2. factual accuracy — ``grounded_accuracy``, then ``fabricated_number_rate``
3. latency — gate-cell ``request_latency_p50_ms``

Every rate is quantized to :data:`RATE_RESOLUTION` before it is compared. That
constant is the verdict policy's own divergence threshold for a bounded-[0,1]
metric (``docs/verdict-policy.md`` Gate 2): two rates closer than it are inside
run-to-run noise, so treating them as distinct would rank on noise. Quantizing
makes near-ties fall through to the next criterion instead, and leaves latency —
the one criterion where a small difference is real and repeatable — as the final
tiebreak.

Usage::

    mlx-bench-shootout run-output/ --gate conc1_think-on_ctx-large
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

log = logging.getLogger(__name__)

# Verdict-policy Gate 2 divergence threshold for a bounded-[0,1] rate metric.
# Differences smaller than this are indistinguishable from run-to-run drift.
RATE_RESOLUTION = 0.10

# Default gate: single-stream, thinking on, large context. The shootout picks a
# brain that runs ALONE under single-user load, and every 40B+ model on this
# fabric is served single-slot, so conc1 — not the conc4 pass gate in
# docs/agentic.md — is the cell that matches how the winner will actually serve.
DEFAULT_GATE = "conc1_think-on_ctx-large"


class Scored(NamedTuple):
    """One model's combined scores. ``None`` fields mean the suite was not run."""

    model: str
    gate_valid_rate: float | None
    multiturn_survival: float | None
    grounded_accuracy: float | None
    fabricated_number_rate: float | None
    latency_p50_ms: float | None
    first_token_p50_ms: float | None
    factual_thinking: str | None

    @property
    def complete(self) -> bool:
        """True when both suites contributed, so the row is rankable."""
        return None not in (
            self.gate_valid_rate,
            self.multiturn_survival,
            self.grounded_accuracy,
            self.fabricated_number_rate,
            self.latency_p50_ms,
        )


def quantize(value: float, resolution: float = RATE_RESOLUTION) -> float:
    """Snap a rate to the nearest ``resolution`` bucket."""
    return round(value / resolution) * resolution


def rank_key(row: Scored) -> tuple[float, ...]:
    """Sort key implementing the criterion priority. Lower sorts first (better).

    A missing score sorts last on its criterion. Note the explicit ``is None``
    checks: ``value or default`` cannot be used here because 0.0 is falsy, and
    0.0 is the *best* possible fabrication rate — the idiom would rank a model
    that never invented a number as if it invented one every time.
    """
    return (
        -quantize(row.gate_valid_rate if row.gate_valid_rate is not None else 0.0),
        -quantize(row.multiturn_survival if row.multiturn_survival is not None else 0.0),
        -quantize(row.grounded_accuracy if row.grounded_accuracy is not None else 0.0),
        quantize(row.fabricated_number_rate if row.fabricated_number_rate is not None else 1.0),
        row.latency_p50_ms if row.latency_p50_ms is not None else float("inf"),
    )


def multiturn_survival(tracks: Sequence[Mapping[str, Any]]) -> float | None:
    """Worst-case share of multi-turn rounds completed before degradation.

    ``first_degraded_round`` of ``None`` means the track ran clean to the end
    (1.0). Otherwise the model survived ``first_degraded_round - 1`` rounds. The
    minimum across thinking modes is used deliberately: a brain that only holds
    up in one thinking mode is a brain with a footgun.
    """
    scores: list[float] = []
    for track in tracks:
        rounds = track.get("rounds") or []
        if not rounds:
            continue
        first = track.get("first_degraded_round")
        scores.append(1.0 if not isinstance(first, int) else max(0, first - 1) / len(rounds))
    return min(scores) if scores else None


def score_agentic(raw: Mapping[str, Any], gate: str) -> dict[str, Any]:
    """Pull gate-cell fidelity + latency and the multi-turn survival share."""
    gate_cells = [c for c in raw.get("cells") or [] if gate in str(c.get("name", ""))]
    if not gate_cells:
        available = ", ".join(str(c.get("name", "")) for c in raw.get("cells") or []) or "(none)"
        raise ValueError(f"no cell matches gate {gate!r} for {raw.get('model')!r}; cells: {available}")

    def mean_of(key: str) -> float | None:
        values = [c[key] for c in gate_cells if isinstance(c.get(key), int | float)]
        return sum(values) / len(values) if values else None

    return {
        "gate_valid_rate": mean_of("valid_tool_call_rate"),
        "latency_p50_ms": mean_of("latency_p50_ms"),
        "first_token_p50_ms": mean_of("first_token_p50_ms"),
        "multiturn_survival": multiturn_survival(raw.get("multiturn") or []),
    }


def score_factual(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Pull the model's best factual cell, and say which thinking mode produced it.

    Best = highest ``grounded_accuracy``, fewest fabrications on a tie. Taking
    the better thinking mode mirrors the RUNBOOK rule that a model is judged in,
    and shipped with, its winning track's serving config.
    """
    cells = [c for c in raw.get("cells") or [] if isinstance(c.get("grounded_accuracy"), int | float)]
    if not cells:
        raise ValueError(f"factual results for {raw.get('model')!r} contain no scored cell")
    best = max(cells, key=lambda c: (c["grounded_accuracy"], -c.get("fabricated_number_rate", 1.0)))
    return {
        "grounded_accuracy": float(best["grounded_accuracy"]),
        "fabricated_number_rate": float(best.get("fabricated_number_rate", 1.0)),
        "factual_thinking": "on" if best.get("thinking") else "off",
    }


def collect(paths: Sequence[Path], gate: str) -> list[Scored]:
    """Group raw result files by the model id recorded inside them.

    Grouping on the file's own ``model`` field rather than its filename means a
    run keeps its identity however the operator named the output.
    """
    merged: dict[str, dict[str, Any]] = {}
    for path in sorted(paths):
        raw = json.loads(path.read_text())
        model = raw.get("model")
        if not model:
            log.warning("%s has no model field — skipping", path)
            continue
        benchmark = raw.get("benchmark")
        entry = merged.setdefault(model, {})
        if benchmark == "agentic":
            entry |= score_agentic(raw, gate)
        elif benchmark == "factual":
            entry |= score_factual(raw)
        else:
            log.warning("%s: unsupported benchmark %r — skipping", path, benchmark)

    return [
        Scored(
            model=model,
            gate_valid_rate=data.get("gate_valid_rate"),
            multiturn_survival=data.get("multiturn_survival"),
            grounded_accuracy=data.get("grounded_accuracy"),
            fabricated_number_rate=data.get("fabricated_number_rate"),
            latency_p50_ms=data.get("latency_p50_ms"),
            first_token_p50_ms=data.get("first_token_p50_ms"),
            factual_thinking=data.get("factual_thinking"),
        )
        for model, data in merged.items()
    ]


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _ms(value: float | None) -> str:
    return "—" if value is None else f"{value:,.0f}"


def render_markdown(rows: Sequence[Scored], gate: str) -> str:
    """Ranked table plus the incomplete-model list. Wording follows verdict policy."""
    complete = sorted([r for r in rows if r.complete], key=rank_key)
    incomplete = [r for r in rows if not r.complete]

    lines = [
        f"# Agent-brain shootout — provisional standing (gate cell `{gate}`)",
        "",
        "Ordered lexicographically by tool-call fidelity, then factual accuracy, then",
        f"latency; rates quantized to {RATE_RESOLUTION:.2f} so within-noise differences fall",
        "through to the next criterion. Every standing here is PROVISIONAL until the",
        "model clears all three gates of `docs/verdict-policy.md`.",
        "",
        "| # | Model | Gate valid% | Multi-turn survival | Grounded acc% | Fabricated% | Latency p50 ms | TTFT p50 ms | Factual track |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, row in enumerate(complete, start=1):
        lines.append(
            f"| {i} | {row.model} | {_pct(row.gate_valid_rate)} | "
            f"{_pct(row.multiturn_survival)} | {_pct(row.grounded_accuracy)} | "
            f"{_pct(row.fabricated_number_rate)} | {_ms(row.latency_p50_ms)} | "
            f"{_ms(row.first_token_p50_ms)} | thinking {row.factual_thinking or '—'} |"
        )
    if incomplete:
        lines += [
            "",
            "## Not ranked — incomplete suite coverage",
            "",
            "A model is ranked only once both the agentic and factual suites have run.",
            "",
        ]
        lines += [f"- `{row.model}`" for row in incomplete]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank models from raw agentic + factual results")
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Raw result JSON files, or directories scanned non-recursively for *.json",
    )
    parser.add_argument("--gate", default=DEFAULT_GATE, help="Substring selecting the agentic gate cell")
    parser.add_argument("--json", action="store_true", help="Emit JSON rows instead of a markdown table")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    files = [f for p in args.paths for f in (sorted(p.glob("*.json")) if p.is_dir() else [p])]
    if not files:
        print("no result files found", file=sys.stderr)
        return 1

    rows = collect(files, args.gate)
    if args.json:
        payload = [r._asdict() | {"complete": r.complete} for r in sorted(rows, key=rank_key)]
        print(json.dumps(payload, indent=2))
    else:
        print(render_markdown(rows, args.gate), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
