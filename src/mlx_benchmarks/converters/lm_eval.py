"""lm-eval ``results.json`` -> envelope v1 converter."""

from __future__ import annotations

import datetime
import json
import logging
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Protocol, cast

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


class _TokenizerLike(Protocol):
    """Minimal duck-type for the bits of a tokenizer the converter needs.

    ``encode(text)`` must return an object with ``.ids`` (matches
    ``tokenizers.Tokenizer`` and ``transformers.PreTrainedTokenizerFast``).
    """

    def encode(self, text: str) -> Any:  # pragma: no cover - protocol
        ...


TokenizerLoader = Callable[[str], _TokenizerLike | None]


def _default_tokenizer_loader(model: str) -> _TokenizerLike | None:
    """Load a HF tokenizer for ``model`` via the ``tokenizers`` library.

    Returns ``None`` on any failure (missing dep, unknown repo, offline). The
    converter degrades gracefully — tok/s fields stay unset for that result
    rather than failing the whole publish.
    """
    try:
        from tokenizers import Tokenizer
    except ImportError:
        log.debug("tokenizers package not available; tok/s fields will be unset")
        return None
    try:
        # tokenizers.Tokenizer.encode has a wider signature than the converter
        # needs; at runtime it satisfies _TokenizerLike (encode(text).ids).
        return cast(_TokenizerLike, Tokenizer.from_pretrained(model))
    except Exception as exc:
        log.warning("could not load tokenizer for %s: %s — tok/s fields will be unset", model, exc)
        return None


class LmEvalConverter:
    kind = "lm-eval"

    def __init__(self, tokenizer_loader: TokenizerLoader | None = None) -> None:
        self._tokenizer_loader: TokenizerLoader = tokenizer_loader or _default_tokenizer_loader
        self._tokenizer_cache: dict[str, _TokenizerLike | None] = {}

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

        cfg = raw.get("config") or {}
        seed = cfg.get("seed")
        if isinstance(seed, int):
            envelope["seed"] = seed

        model_args = cfg.get("model_args") or {}
        revision = raw.get("model_source") or model_args.get("revision")
        if revision:
            envelope["model_revision"] = str(revision)

        return envelope

    def _iter_results(self, raw: dict[str, Any], ctx: ConverterContext) -> Iterator[Result]:
        raw_results: dict[str, dict[str, Any]] = raw.get("results") or {}
        task_durations = raw.get("total_evaluation_time_seconds_per_task") or {}
        cfg = raw.get("config") or {}
        cfg_gen_kwargs = cfg.get("gen_kwargs") or {}
        # lm-eval tasks emit several metrics each (acc / acc_norm / exact_match /
        # stderr-pairs / etc.). All of them share the same duration and would
        # produce identical tok/s, so we tokenize each samples file at most once
        # per task and reuse the result across this task's metric rows.
        task_throughput_cache: dict[str, dict[str, float] | None] = {}

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
                limit = cfg.get("limit")
                if limit is not None:
                    tags["n_limit"] = str(limit)
                max_gen_toks = cfg_gen_kwargs.get("max_gen_toks")
                if max_gen_toks is not None:
                    tags["max_gen_toks"] = str(max_gen_toks)
                result["tags"] = tags

                # Use an explicit None check so genuinely-zero durations are preserved.
                # (``group_subtasks`` was previously checked here but it maps
                # group -> list of subtask names, never durations — removed.)
                duration = task_durations.get(task_name)
                if isinstance(duration, int | float):
                    result["duration_seconds"] = float(duration)
                    throughput = self._throughput_for_task(
                        task_name, float(duration), ctx, task_throughput_cache
                    )
                    if throughput is not None:
                        for key, value in throughput.items():
                            result[key] = value  # type: ignore[literal-required]

                yield result

    def _throughput_for_task(
        self,
        task_name: str,
        duration_s: float,
        ctx: ConverterContext,
        cache: dict[str, dict[str, float] | None],
    ) -> dict[str, float] | None:
        """Compute the aggregate tok/s dict for ``task_name`` once and cache it.

        Returns a dict keyed by the optional Result field name (``prompt_tokens_per_second``,
        ``decode_tokens_per_second``, ``total_tokens_per_second``) or ``None`` when
        the throughput cannot be computed. A cached ``None`` is a real negative
        answer — do not retry.
        """
        if task_name in cache:
            return cache[task_name]
        cache[task_name] = None  # negative cache; overwritten if compute succeeds
        if duration_s <= 0 or ctx.source_path is None:
            return None
        samples_file = _find_samples_file(ctx.source_path, task_name)
        if samples_file is None:
            return None
        tokenizer = self._get_tokenizer(ctx.model)
        if tokenizer is None:
            return None

        try:
            prompt_total, response_total, sample_count = _sum_tokens(samples_file, tokenizer)
        except OSError as exc:
            log.warning("could not read %s: %s — tok/s fields unset", samples_file, exc)
            return None
        if sample_count == 0:
            return None

        throughput = {
            "prompt_tokens_per_second": prompt_total / duration_s,
            "decode_tokens_per_second": response_total / duration_s,
            "total_tokens_per_second": (prompt_total + response_total) / duration_s,
        }
        cache[task_name] = throughput
        return throughput

    def _get_tokenizer(self, model: str) -> _TokenizerLike | None:
        if model not in self._tokenizer_cache:
            self._tokenizer_cache[model] = self._tokenizer_loader(model)
        return self._tokenizer_cache[model]


def _find_samples_file(source_path: Path, task_name: str) -> Path | None:
    """Locate ``samples_{task_name}_{ts}.jsonl`` next to a ``results_{ts}.json``.

    lm-eval writes them as siblings. Prefer the exact timestamp match (so a
    directory holding multiple runs picks the right pair); fall back to the
    most recent matching file when the stem does not match the convention.
    """
    if not source_path.exists():
        return None
    directory = source_path.parent
    matches = sorted(directory.glob(f"samples_{task_name}_*.jsonl"))
    if not matches:
        return None
    stem = source_path.stem
    if stem.startswith("results_"):
        ts = stem.removeprefix("results_")
        candidate = directory / f"samples_{task_name}_{ts}.jsonl"
        if candidate.is_file():
            return candidate
    return matches[-1]


def _sum_tokens(samples_path: Path, tokenizer: _TokenizerLike) -> tuple[int, int, int]:
    """Walk a samples JSONL, return (prompt_tokens, response_tokens, sample_count)."""
    prompt_total = 0
    response_total = 0
    sample_count = 0
    with samples_path.open() as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                sample = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            prompt_total += _count(tokenizer, _extract_prompt(sample))
            response_total += _count(tokenizer, _extract_response(sample))
            sample_count += 1
    return prompt_total, response_total, sample_count


def _count(tokenizer: _TokenizerLike, text: str) -> int:
    if not text:
        return 0
    encoded = tokenizer.encode(text)
    ids = getattr(encoded, "ids", None)
    if ids is not None:
        return len(ids)
    # ``transformers``-style tokenizers return a plain list of ints from encode().
    if isinstance(encoded, list):
        return len(encoded)
    return 0


def _extract_prompt(sample: dict[str, Any]) -> str:
    """Reconstruct the prompt text from an lm-eval sample line.

    lm-eval's ``arguments`` is the list of (prompt_str, gen_kwargs_dict) tuples
    actually sent to the API. We join the prompts to get the total prefill
    text. Falls back to ``doc.{question,input,prompt}`` if arguments are
    structured differently for this task.
    """
    args = sample.get("arguments")
    if isinstance(args, list):
        chunks: list[str] = []
        for arg in args:
            if isinstance(arg, list) and arg and isinstance(arg[0], str):
                chunks.append(arg[0])
            elif isinstance(arg, dict):
                text = arg.get("text") or arg.get("prompt")
                if isinstance(text, str):
                    chunks.append(text)
            elif isinstance(arg, str):
                chunks.append(arg)
        if chunks:
            return "\n".join(chunks)
    doc = sample.get("doc")
    if isinstance(doc, dict):
        for key in ("question", "input", "prompt"):
            value = doc.get(key)
            if isinstance(value, str):
                return value
    return ""


def _extract_response(sample: dict[str, Any]) -> str:
    """Reconstruct the response text from an lm-eval sample line.

    Prefers ``filtered_resps`` (post-processing applied) over raw ``resps``
    so the token count reflects what scoring actually saw.
    """
    resps = sample.get("filtered_resps") or sample.get("resps")
    if not isinstance(resps, list):
        return ""
    flat: list[str] = []
    for r in resps:
        if isinstance(r, str):
            flat.append(r)
        elif isinstance(r, list):
            flat.extend(str(x) for x in r if isinstance(x, str | int | float))
    return "\n".join(flat) if flat else ""


_ISO8601_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _extract_timestamp(raw: dict[str, Any]) -> str:
    raw_date = raw.get("date")
    if isinstance(raw_date, int | float):
        return datetime.datetime.fromtimestamp(raw_date, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(raw_date, str) and _ISO8601_UTC.match(raw_date):
        return raw_date
    if isinstance(raw_date, str):
        log.warning(
            "ignoring non-ISO-8601 raw['date']=%r; falling back to current UTC time",
            raw_date,
        )
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_gen_kwargs(raw: dict[str, Any]) -> GenKwargs | None:
    cfg_raw = raw.get("config") or {}
    cfg = cfg_raw.get("gen_kwargs") or {}
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
