"""vllm ``benchmark_serving`` JSON -> envelope v1 converter."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import Envelope, Result, System

log = logging.getLogger(__name__)

# Map from vllm benchmark_serving JSON key -> (metric_name, unit)
# Only keys listed here are extracted; unknown keys are silently ignored so
# the converter remains forward-compatible with new vllm output fields.
_METRIC_MAP: dict[str, tuple[str, str]] = {
    "output_throughput": ("throughput_output_toks_per_s", "tok/s"),
    "total_token_throughput": ("throughput_total_toks_per_s", "tok/s"),
    "request_throughput": ("throughput_requests_per_s", "req/s"),
    "median_ttft_ms": ("ttft_p50_ms", "ms"),
    "p99_ttft_ms": ("ttft_p99_ms", "ms"),
    "median_itl_ms": ("itl_p50_ms", "ms"),
    "p99_itl_ms": ("itl_p99_ms", "ms"),
    "median_tpot_ms": ("tpot_p50_ms", "ms"),
    "p99_tpot_ms": ("tpot_p99_ms", "ms"),
}


class VllmConverter:
    kind = "vllm"

    def build_envelope(self, raw: dict[str, Any], ctx: ConverterContext) -> Envelope:
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

        if ctx.pr_number is not None:
            envelope["pr_number"] = ctx.pr_number

        return envelope

    def _iter_results(self, raw: dict[str, Any], ctx: ConverterContext) -> list[Result]:
        results: list[Result] = []
        duration = raw.get("duration")
        completed = raw.get("completed")
        num_input = raw.get("total_input_tokens")
        num_output = raw.get("total_output_tokens")

        tags: dict[str, str] = {k: str(v) for k, v in ctx.extra_tags.items()}
        if isinstance(completed, int | float):
            tags["completed_requests"] = str(int(completed))
        if isinstance(num_input, int | float):
            tags["total_input_tokens"] = str(int(num_input))
        if isinstance(num_output, int | float):
            tags["total_output_tokens"] = str(int(num_output))

        for raw_key, (metric_name, unit) in _METRIC_MAP.items():
            raw_val = raw.get(raw_key)
            if not isinstance(raw_val, int | float):
                log.debug("vllm sample missing key %r — skipping metric %r", raw_key, metric_name)
                continue
            result: Result = {
                "name": "benchmark_serving",
                "metric": metric_name,
                "value": float(raw_val),
                "unit": unit,
                "tags": dict(tags),
            }
            if isinstance(duration, int | float):
                result["duration_seconds"] = float(duration)
            results.append(result)

        if not results:
            log.warning("vllm sample produced no results; raw keys: %s", list(raw))

        return results
