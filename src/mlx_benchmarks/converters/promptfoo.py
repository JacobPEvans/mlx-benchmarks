"""promptfoo ``eval -o output.json`` -> envelope v1 converter.

promptfoo compares one or more *providers* (models under test) across a set of
test cases, each with pass/fail assertions and optional named LLM-rubric scores.
This converter aggregates that per-result output into envelope rows keyed by the
model under test, so a single comparison run yields one row per
(model, metric) — ``pass_rate`` and ``mean_score`` for every provider, plus a
row for each named rubric metric.

Only promptfoo's JSON output is parsed; the promptfoo package is not a
dependency of this repo (mirrors how the lm-eval and vllm converters work).
"""

from __future__ import annotations

import datetime
import logging
from collections import defaultdict
from typing import Any

from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import Envelope, Result, System

log = logging.getLogger(__name__)


class _ProviderAggregate:
    """Running totals for one provider (model under test) across all test cases."""

    __slots__ = ("n_passed", "n_tests", "named_scores", "score_sum")

    def __init__(self) -> None:
        self.n_tests = 0
        self.n_passed = 0
        self.score_sum = 0.0
        self.named_scores: dict[str, list[float]] = defaultdict(list)


class PromptfooConverter:
    kind = "promptfoo"

    def build_envelope(self, raw: dict[str, Any], ctx: ConverterContext) -> Envelope:
        timestamp = ctx.timestamp_override or _extract_timestamp(raw)
        system: System = ctx.system or {}  # type: ignore[assignment]

        envelope: Envelope = {
            "schema_version": "1",
            "timestamp": timestamp,
            "git_sha": ctx.git_sha,
            "trigger": ctx.trigger,
            "suite": ctx.suite,
            "model": ctx.model,
            "system": system,
            "results": self._iter_results(raw, ctx),
            "errors": [],
        }

        if ctx.pr_number is not None:
            envelope["pr_number"] = ctx.pr_number

        return envelope

    def _iter_results(self, raw: dict[str, Any], ctx: ConverterContext) -> list[Result]:
        eval_results = _extract_results_list(raw)
        if not eval_results:
            log.warning("promptfoo output has no results[]; raw keys: %s", list(raw))
            return []

        aggregates: dict[str, _ProviderAggregate] = defaultdict(_ProviderAggregate)
        for item in eval_results:
            provider = _provider_name(item.get("provider"))
            agg = aggregates[provider]
            agg.n_tests += 1
            if item.get("success"):
                agg.n_passed += 1
            score = item.get("score")
            if isinstance(score, int | float):
                agg.score_sum += float(score)
            for key, value in (item.get("namedScores") or {}).items():
                if isinstance(value, int | float):
                    agg.named_scores[key].append(float(value))

        extra_tags = {k: str(v) for k, v in ctx.extra_tags.items()}

        results: list[Result] = []
        for provider in sorted(aggregates):
            agg = aggregates[provider]
            if agg.n_tests == 0:
                continue
            # ``model`` tag carries the model under test so a comparison run's
            # rows stay per-model downstream (e.g. the Splunk model_eval alert),
            # even though the envelope-level ``model`` is the sweep label.
            tags = {"model": provider, "n_tests": str(agg.n_tests), **extra_tags}
            results.append(_row(provider, "pass_rate", agg.n_passed / agg.n_tests, tags))
            results.append(_row(provider, "mean_score", agg.score_sum / agg.n_tests, tags))
            for metric_name in sorted(agg.named_scores):
                values = agg.named_scores[metric_name]
                results.append(_row(provider, metric_name, sum(values) / len(values), tags))

        return results


def _row(provider: str, metric: str, value: float, tags: dict[str, str]) -> Result:
    return {
        "name": provider,
        "metric": metric,
        "value": value,
        "unit": "ratio",
        "tags": dict(tags),
    }


def _provider_name(provider: Any) -> str:
    """Best-effort human label for a promptfoo provider entry.

    promptfoo serializes ``provider`` as ``{"id": ..., "label": ...}`` (label
    optional) but older/edge outputs use a bare string. Prefer the label, then
    the id, then a stable placeholder so results never collapse into one row.
    """
    if isinstance(provider, dict):
        for key in ("label", "id"):
            value = provider.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(provider, str) and provider:
        return provider
    return "unknown"


def _extract_results_list(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Locate the per-test result list across promptfoo output-file shapes.

    ``promptfoo eval -o output.json`` writes ``{"results": {"results": [...]}}``
    (EvaluateSummary v2/v3). Some callers persist the summary object directly,
    giving a top-level ``{"results": [...]}``. Handle both; anything else yields
    an empty list (the converter logs and returns no rows rather than guessing).
    """
    outer = raw.get("results")
    if isinstance(outer, dict):
        inner = outer.get("results")
        if isinstance(inner, list):
            return inner
    if isinstance(outer, list):
        return outer
    return []


def _extract_timestamp(raw: dict[str, Any]) -> str:
    """Pull the run timestamp from the promptfoo summary, else current UTC.

    promptfoo stamps ``results.timestamp`` as an ISO-8601 string; normalize it to
    the envelope's ``...Z`` second-precision form. Any parse failure falls back
    to now (never fails the conversion over a cosmetic field).
    """
    outer = raw.get("results")
    stamp = outer.get("timestamp") if isinstance(outer, dict) else None
    if isinstance(stamp, str):
        try:
            parsed = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            return parsed.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            log.debug("unparseable promptfoo timestamp %r; using now()", stamp)
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
