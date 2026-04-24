"""lm-eval ``results.json`` -> envelope v1 converter."""

from __future__ import annotations

import datetime
import logging
from collections.abc import Iterator
from typing import Any

from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import Envelope, GenKwargs, Result, System

log = logging.getLogger(__name__)

# Friendly display names for common lm-eval metric keys. Unknown keys fall
# through via a deterministic normalization.
_METRIC_MAP = {
    "exact_match,flexible-extract": "exact_match_flexible",
    "exact_match,strict-match": "exact_match_strict",
    "acc,none": "accuracy",
    "acc_norm,none": "accuracy_normalized",
    "pass@1,none": "pass_at_1",
}


class LmEvalConverter:
    kind = "lm-eval"

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
            "results": list(self._iter_results(raw, ctx)),
            "errors": [],
        }

        if ctx.pr_number is not None:
            envelope["pr_number"] = ctx.pr_number

        gen_kwargs = _extract_gen_kwargs(raw)
        if gen_kwargs:
            envelope["gen_kwargs"] = gen_kwargs

        seed = raw.get("config", {}).get("seed")
        if isinstance(seed, int):
            envelope["seed"] = seed

        revision = raw.get("model_source") or raw.get("config", {}).get("model_args", {}).get("revision")
        if revision:
            envelope["model_revision"] = str(revision)

        return envelope

    def _iter_results(self, raw: dict[str, Any], ctx: ConverterContext) -> Iterator[Result]:
        raw_results: dict[str, dict[str, Any]] = raw.get("results", {})
        eval_times: dict[str, float] = raw.get("group_subtasks", {}) or {}
        task_durations = raw.get("total_evaluation_time_seconds_per_task", {}) or {}

        for task_name, task_metrics in raw_results.items():
            for metric_key, metric_val in task_metrics.items():
                if "stderr" in metric_key or metric_key == "alias":
                    continue
                if not isinstance(metric_val, int | float):
                    log.debug("skip non-numeric metric %s=%r for task %s", metric_key, metric_val, task_name)
                    continue

                display_metric = _METRIC_MAP.get(metric_key, metric_key.replace(",", "_"))
                result: Result = {
                    "name": task_name,
                    "metric": display_metric,
                    "value": float(metric_val),
                    "unit": _guess_unit(display_metric),
                }

                tags: dict[str, str] = {
                    "lm_eval_key": metric_key,
                    **{k: str(v) for k, v in ctx.extra_tags.items()},
                }
                total_eval_time = raw.get("total_evaluation_time_seconds")
                if total_eval_time is not None:
                    tags["total_eval_time_s"] = str(total_eval_time)
                limit = raw.get("config", {}).get("limit")
                if limit is not None:
                    tags["n_limit"] = str(limit)
                max_gen_toks = raw.get("config", {}).get("gen_kwargs", {}).get("max_gen_toks")
                if max_gen_toks is not None:
                    tags["max_gen_toks"] = str(max_gen_toks)
                result["tags"] = tags

                duration = task_durations.get(task_name) or eval_times.get(task_name)
                if isinstance(duration, int | float):
                    result["duration_seconds"] = float(duration)

                yield result


def _extract_timestamp(raw: dict[str, Any]) -> str:
    raw_date = raw.get("date")
    if isinstance(raw_date, int | float):
        return datetime.datetime.fromtimestamp(raw_date, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(raw_date, str):
        return raw_date
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_gen_kwargs(raw: dict[str, Any]) -> GenKwargs | None:
    cfg = raw.get("config", {}).get("gen_kwargs") or {}
    if not isinstance(cfg, dict) or not cfg:
        return None
    result: GenKwargs = {}
    max_gen_toks = cfg.get("max_gen_toks")
    if isinstance(max_gen_toks, int):
        result["max_gen_toks"] = max_gen_toks
    temperature = cfg.get("temperature")
    if isinstance(temperature, int | float):
        result["temperature"] = float(temperature)
    top_p = cfg.get("top_p")
    if isinstance(top_p, int | float):
        result["top_p"] = float(top_p)
    top_k = cfg.get("top_k")
    if isinstance(top_k, int):
        result["top_k"] = top_k
    return result or None


def _guess_unit(display_metric: str) -> str:
    if display_metric in {
        "accuracy",
        "accuracy_normalized",
        "pass_at_1",
        "exact_match_flexible",
        "exact_match_strict",
    }:
        return "ratio"
    if display_metric.endswith("_seconds"):
        return "seconds"
    if display_metric.endswith("_ms"):
        return "ms"
    return "ratio"
