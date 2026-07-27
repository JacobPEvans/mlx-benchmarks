"""vllm-mlx ``bench-serve`` JSON -> envelope v1 converter.

``vllm-mlx bench-serve --format json`` emits a flat *list* of per-run records
(one per prompt-set x concurrency x repetition). Repetitions are aggregated to
a median per (prompt_set, concurrency) group so one benchmark invocation
yields one row per metric per group, with the sweep dimensions carried as
string tags.
"""

from __future__ import annotations

import datetime
import logging
import statistics
from typing import Any

from mlx_benchmarks.converters.base import ConverterContext, apply_optional_fields
from mlx_benchmarks.envelope import Envelope, Result, System

log = logging.getLogger(__name__)

# Map from bench-serve per-run key -> (metric_name, unit). Metric names match
# the vllm benchmark_serving converter where semantics coincide, so both tools
# land on comparable columns. Median over repetitions -> the *_p50 names.
#
# Headline metric policy (2026-07-27, see docs/schema.md): throughput_total_toks_per_s
# (cumulative prompt+completion tok/s) is the PRIMARY figure — throughput_output_toks_per_s
# (decode-only) is supporting detail that hides prefill-engine gains.
_METRIC_MAP: dict[str, tuple[str, str]] = {
    "gen_tps": ("throughput_output_toks_per_s", "tok/s"),
    "throughput_tps": ("throughput_total_toks_per_s", "tok/s"),
    "ttft_ms": ("ttft_p50_ms", "ms"),
    "tpot_ms": ("tpot_p50_ms", "ms"),
}


class BenchServeConverter:
    kind = "bench-serve"

    def build_envelope(self, raw: Any, ctx: ConverterContext) -> Envelope:
        timestamp = ctx.timestamp_override or datetime.datetime.now(datetime.UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
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

        return apply_optional_fields(envelope, ctx)

    def _iter_results(self, raw: Any, ctx: ConverterContext) -> list[Result]:
        runs = raw if isinstance(raw, list) else raw.get("runs", [])
        groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
        for run in runs:
            if not isinstance(run, dict):
                continue
            key = (str(run.get("prompt_set", "default")), int(run.get("concurrency", 1)))
            groups.setdefault(key, []).append(run)

        results: list[Result] = []
        for (prompt_set, concurrency), members in sorted(groups.items()):
            tags: dict[str, str] = {k: str(v) for k, v in ctx.extra_tags.items()}
            tags["prompt_set"] = prompt_set
            tags["concurrency"] = str(concurrency)
            tags["repetitions"] = str(len(members))
            validated = [m.get("validated") for m in members if m.get("validated") is not None]
            if validated:
                tags["validated"] = str(all(validated)).lower()

            peak_gb = [m["metal_peak_gb"] for m in members if isinstance(m.get("metal_peak_gb"), int | float)]

            for raw_key, (metric_name, unit) in _METRIC_MAP.items():
                values = [m[raw_key] for m in members if isinstance(m.get(raw_key), int | float)]
                if not values:
                    log.debug(
                        "bench-serve group %s missing key %r — skipping metric %r",
                        (prompt_set, concurrency),
                        raw_key,
                        metric_name,
                    )
                    continue
                result: Result = {
                    "name": "bench_serve",
                    "metric": metric_name,
                    "value": float(statistics.median(values)),
                    "unit": unit,
                    "tags": dict(tags),
                }
                if peak_gb:
                    result["peak_rss_mb"] = float(max(peak_gb)) * 1024.0
                results.append(result)

        if not results:
            log.warning("bench-serve output produced no results; raw type: %s", type(raw).__name__)

        return results
