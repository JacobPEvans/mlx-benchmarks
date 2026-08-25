from __future__ import annotations

import datetime
import logging
from typing import Any

from mlx_benchmarks.converters.base import ConverterContext, apply_optional_fields
from mlx_benchmarks.envelope import Envelope, Result, System

log = logging.getLogger(__name__)

_METRICS: tuple[tuple[str, str, str], ...] = (
    ("cumulative_tok_s", "throughput_total_toks_per_s", "tok/s"),
    ("decode_tok_s", "throughput_output_toks_per_s", "tok/s"),
    ("prefill_tok_s", "throughput_prompt_toks_per_s", "tok/s"),
    ("ttft_s", "ttft_p50_ms", "ms"),
    ("total_s", "request_duration_p50_s", "s"),
)


class ThroughputProbeConverter:
    kind = "throughput-probe"

    def build_envelope(self, raw: Any, ctx: ConverterContext) -> Envelope:
        timestamp = (
            ctx.timestamp_override
            or raw.get("started_utc")
            or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        if not isinstance(raw, dict) or not isinstance(raw.get("sequential"), dict):
            log.warning("throughput-probe output has no sequential summary")
            return []

        sequential = raw["sequential"]
        tags = {k: str(v) for k, v in ctx.extra_tags.items()}
        for key in ("n_ok", "n_err", "answered_rate", "truncated_rate"):
            if key in sequential:
                tags[key] = str(sequential[key])
        if isinstance(sequential.get("finish_reasons"), list):
            tags["finish_reasons"] = ",".join(map(str, sequential["finish_reasons"]))
        if "max_tokens" in raw:
            tags["max_tokens"] = str(raw["max_tokens"])
        if "thinking" in raw:
            tags["thinking"] = str(raw["thinking"])
        if "sequential_runs" in raw:
            tags["repetitions"] = str(raw["sequential_runs"])

        results: list[Result] = []
        for source_key, metric, unit in _METRICS:
            stats = sequential.get(source_key)
            if not isinstance(stats, dict) or not isinstance(stats.get("median"), int | float):
                continue
            result_tags = dict(tags)
            for stat in ("min", "max"):
                if isinstance(stats.get(stat), int | float):
                    result_tags[f"{source_key}_{stat}"] = str(stats[stat])
            value = float(stats["median"])
            if source_key == "ttft_s":
                value *= 1000.0
            results.append(
                {
                    "name": "throughput_probe",
                    "metric": metric,
                    "value": value,
                    "unit": unit,
                    "tags": result_tags,
                    "raw": sequential,
                }
            )
        return results
