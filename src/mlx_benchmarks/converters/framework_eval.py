"""framework-eval harness JSON -> envelope v1 converter.

Accepts the stdout JSON from any ``harness/framework-eval/eval_*.py``
script. Each script run produces one JSON object; pass it to
``mlx-bench-publish`` via ``--kind framework-eval``.

Example::

    uv run eval_openai_tool_calling.py > result.json
    mlx-bench-publish result.json \\
        --kind framework-eval --suite framework-eval \\
        --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import Envelope, Result, System

log = logging.getLogger(__name__)

_ERROR_PREFIXES = ("Error:", "(empty)", "(max steps reached)")


class FrameworkEvalConverter:
    kind = "framework-eval"

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
            "results": self._build_results(raw, ctx),
            "errors": [],
        }

        if ctx.pr_number is not None:
            envelope["pr_number"] = ctx.pr_number

        return envelope

    def _build_results(self, raw: dict[str, Any], ctx: ConverterContext) -> list[Result]:
        framework = raw.get("framework")
        if not isinstance(framework, str) or not framework:
            log.warning("framework-eval sample missing 'framework' key; using 'unknown'")
            framework = "unknown"

        latency = raw.get("latency")
        tags: dict[str, str] = {**{k: str(v) for k, v in ctx.extra_tags.items()}}

        results: list[Result] = []

        score = _compute_score(raw)
        score_result: Result = {
            "name": framework,
            "metric": "score",
            "value": score,
            "unit": "bool",
            "tags": dict(tags),
        }
        results.append(score_result)

        if isinstance(latency, int | float):
            latency_result: Result = {
                "name": framework,
                "metric": "latency",
                "value": float(latency),
                "unit": "seconds",
                "tags": dict(tags),
                "duration_seconds": float(latency),
            }
            results.append(latency_result)

        tokens = raw.get("tokens")
        if isinstance(tokens, int | float):
            tokens_result: Result = {
                "name": framework,
                "metric": "tokens",
                "value": float(tokens),
                "unit": "count",
                "tags": dict(tags),
            }
            results.append(tokens_result)

        steps = raw.get("steps")
        if isinstance(steps, int | float):
            steps_result: Result = {
                "name": framework,
                "metric": "steps",
                "value": float(steps),
                "unit": "count",
                "tags": dict(tags),
            }
            results.append(steps_result)

        return results


def _compute_score(raw: dict[str, Any]) -> float:
    answer = raw.get("answer", "")
    if not isinstance(answer, str) or not answer:
        return 0.0
    if any(answer.startswith(prefix) for prefix in _ERROR_PREFIXES):
        return 0.0
    return 1.0
