#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = ["httpx>=0.27"]
# ///
"""Measured throughput probe for an OpenAI-compatible endpoint.

Streams so time-to-first-token separates prefill from decode:
  prefill tok/s    = prompt_tokens / ttft
  decode  tok/s    = (completion_tokens - 1) / (total - ttft)
  cumulative tok/s = (prompt_tokens + completion_tokens) / total   <- HEADLINE

``cumulative_tok_s`` is the primary, consumer-facing number this probe
reports: decode-only throughput hides prefill-engine improvements entirely,
even though a faster prefill is a real, felt latency win for anyone sending
non-trivial prompts. Two models with identical decode speed but a 4-6x
prefill gap are *not* equivalent in practice, and a decode-only headline
metric reports them as if they were. ``prefill_tok_s`` and ``decode_tok_s``
are kept as supporting detail — useful for root-causing *why* the cumulative
number moved — but neither is the figure to lead with.

Run 1 of every sequence is a discarded warm-up (cold-start cost, per the
measurement-discipline rule). Reports median + min/max over the measured runs.

Output is one raw-results JSON. There is currently no ``mlx-bench-publish
--kind`` converter for this exact shape (it predates being tracked in the
repo) — publishing it through the envelope pipeline is tracked as a
follow-up, not done by this script.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

PROMPT = (
    "You are reviewing a production incident. Write a clear, structured "
    "postmortem covering: what happened, the root cause, the blast radius, "
    "the fix that was applied, and three concrete follow-up actions. "
    "The incident: a two-node compute cluster failed to re-form after a "
    "network link was taken down for maintenance, and a resource guard "
    "latched, requiring a reboot. Be specific and thorough."
)

# Order matters: this is also the order fields are reported in, and the
# first entry is the headline metric.
_SUMMARY_KEYS = (
    "cumulative_tok_s",
    "decode_tok_s",
    "prefill_tok_s",
    "ttft_s",
    "total_s",
    # Numeric, so they aggregate like the rates. finish_reason is deliberately
    # NOT here — it is a string and would break median/min/max; it is reported
    # separately in summarize().
    "answer_chars",
    "reasoning_chars",
)


def cumulative_tok_s(
    prompt_tokens: int | None, completion_tokens: int | None, total_s: float
) -> float | None:
    """Headline throughput: (prompt + completion) tokens / wall-clock seconds.

    This is the consumer-visible measure — it counts prefill (prompt
    processing) and decode (completion generation) toward the same number,
    because both are real time a caller waits on. Returns ``None`` when the
    inputs can't produce a meaningful rate (missing token counts or
    non-positive duration).
    """
    if not prompt_tokens and not completion_tokens:
        return None
    if total_s <= 0:
        return None
    return round(((prompt_tokens or 0) + (completion_tokens or 0)) / total_s, 2)


async def one(client, url, model, max_tokens, think_kwarg, think_val) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if think_kwarg:
        body["chat_template_kwargs"] = {think_kwarg: think_val}

    t0 = time.perf_counter()
    try:
        return await _stream(client, url, body, t0)
    except Exception as e:  # server restart / disconnect mid-run
        return {"error": f"{type(e).__name__}: {e}"}


async def _stream(client, url, body, t0) -> dict[str, Any]:
    ttft = None
    usage = None
    ntok = 0
    # Separate answer from reasoning. Counting them together makes a model that
    # emits pure reasoning and zero answer produce a perfect throughput row —
    # the exact failure a throughput table cannot otherwise see. finish_reason
    # is captured for the same reason: a truncated stream and a completed one
    # are indistinguishable from the rates alone.
    answer_chars = 0
    reasoning_chars = 0
    finish_reason = None
    async with client.stream("POST", url, json=body, timeout=1800.0) as r:
        status = r.status_code
        if status != 200:
            txt = await r.aread()
            return {"error": f"HTTP {status}: {txt[:300].decode(errors='replace')}"}
        async for line in r.aiter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices") or []:
                if ch.get("finish_reason"):
                    finish_reason = ch["finish_reason"]
                d = ch.get("delta") or {}
                content = d.get("content") or ""
                reasoning = (d.get("reasoning") or "") + (d.get("reasoning_content") or "")
                if content or reasoning:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    ntok += 1
                answer_chars += len(content)
                reasoning_chars += len(reasoning)
    total = time.perf_counter() - t0
    if ttft is None:
        return {"error": "no tokens streamed", "total_s": total, "usage": usage}
    ptok = (usage or {}).get("prompt_tokens")
    ctok = (usage or {}).get("completion_tokens") or ntok
    return {
        "ttft_s": round(ttft, 3),
        "total_s": round(total, 3),
        "prompt_tokens": ptok,
        "completion_tokens": ctok,
        "cumulative_tok_s": cumulative_tok_s(ptok, ctok, total),
        "prefill_tok_s": round(ptok / ttft, 2) if ptok else None,
        "decode_tok_s": round((ctok - 1) / (total - ttft), 2) if ctok > 1 else None,
        "answer_chars": answer_chars,
        "reasoning_chars": reasoning_chars,
        "finish_reason": finish_reason,
    }


async def one_retry(
    client, url, model, max_tokens, think_kwarg, think_val, attempts=6, label=""
) -> dict[str, Any]:
    """Retry around a shared, actively-churned endpoint (429 / worker restart).

    A failed attempt is never scored; only a clean streamed run is returned.
    """
    # Never None: callers test `"error" in result`, and returning None there
    # raises TypeError instead of reporting the failure it was meant to carry.
    last: dict[str, Any] = {"error": f"no attempt made (attempts={attempts})"}
    for i in range(attempts):
        r = await one(client, url, model, max_tokens, think_kwarg, think_val)
        if "error" not in r:
            if i:
                r["retries"] = i
            return r
        last = r
        print(f"  {label}retry {i + 1}/{attempts}: {r['error'][:120]}", file=sys.stderr, flush=True)
        await asyncio.sleep(20)
    return last


def summarize(runs) -> dict[str, Any]:
    """Aggregate a sequence of per-run dicts into median/min/max per key.

    ``_SUMMARY_KEYS`` is ordered headline-first: ``cumulative_tok_s`` (the
    number to report) before the decode/prefill breakdown (why it moved).
    """
    ok = [r for r in runs if "error" not in r]
    if not ok:
        return {"n_ok": 0, "errors": [r.get("error") for r in runs]}
    # Annotated because this dict is deliberately heterogeneous: counts (int),
    # rates (nested dict), rates-as-fractions (float) and finish_reasons (list).
    # Without it the type is inferred as dict[str, int] from the first two keys
    # and every later assignment is flagged.
    out: dict[str, object] = {"n_ok": len(ok), "n_err": len(runs) - len(ok)}
    for k in _SUMMARY_KEYS:
        vals = [r[k] for r in ok if r.get(k) is not None]
        if vals:
            out[k] = {
                "median": round(statistics.median(vals), 2),
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
            }
    # The stuck-model guard. A model that emits only reasoning and never an
    # answer scores a perfect row on every rate above, because reasoning deltas
    # count as tokens exactly like answer deltas. answered_rate is the metric
    # that catches it: 1.0 means every run produced answer text, 0.0 means the
    # throughput figures describe a model that answered nothing.
    out["answered_rate"] = round(sum(1 for r in ok if (r.get("answer_chars") or 0) > 0) / len(ok), 3)
    stops = [r.get("finish_reason") for r in ok]
    out["finish_reasons"] = sorted({s for s in stops if s})
    # length = the generation hit max_tokens. On a thinking model that usually
    # means the answer was cut off, or never reached, rather than that the model
    # is slow. Treat any rate measured alongside it as suspect.
    out["truncated_rate"] = round(sum(1 for s in stops if s == "length") / len(ok), 3)
    errs = [r["error"] for r in runs if "error" in r]
    if errs:
        out["errors"] = errs
    return out


async def main():
    import httpx

    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--repeats", type=int, default=4, help="measured runs (plus 1 warm-up)")
    ap.add_argument("--concurrency", type=int, default=4, help="parallel probe width")
    ap.add_argument("--think-kwarg", default=None)
    ap.add_argument("--think", default="off", choices=["on", "off"])
    ap.add_argument("--skip-concurrent", action="store_true")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()

    url = a.base_url.rstrip("/") + "/chat/completions"
    think_val = a.think == "on"
    if a.think_kwarg == "reasoning_effort":
        think_val = "high" if a.think == "on" else "low"

    res = {
        "model": a.model,
        "base_url": a.base_url,
        "max_tokens": a.max_tokens,
        "thinking": a.think,
        "think_kwarg": a.think_kwarg,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    async with httpx.AsyncClient() as client:
        print("warm-up run (discarded)...", file=sys.stderr, flush=True)
        warm = await one_retry(client, url, a.model, a.max_tokens, a.think_kwarg, think_val, label="warmup ")
        res["warmup"] = warm
        print(f"  warmup: {warm}", file=sys.stderr, flush=True)
        if "error" in warm:
            res["aborted"] = "warm-up failed; refusing to record scores"
            print(json.dumps(res, indent=2))
            Path(a.output).write_text(json.dumps(res, indent=2))
            return 1

        seq = []
        for i in range(a.repeats):
            r = await one_retry(
                client, url, a.model, a.max_tokens, a.think_kwarg, think_val, label=f"seq[{i}] "
            )
            print(f"  seq[{i}]: {r}", file=sys.stderr, flush=True)
            seq.append(r)
        res["sequential_runs"] = seq
        res["sequential"] = summarize(seq)

        if not a.skip_concurrent:
            print(f"concurrent probe x{a.concurrency}...", file=sys.stderr, flush=True)
            t0 = time.perf_counter()
            conc = await asyncio.gather(
                *[
                    one(client, url, a.model, a.max_tokens, a.think_kwarg, think_val)
                    for _ in range(a.concurrency)
                ]
            )
            wall = time.perf_counter() - t0
            ok = [c for c in conc if "error" not in c]
            out_toks = sum(c.get("completion_tokens") or 0 for c in ok)
            in_toks = sum(c.get("prompt_tokens") or 0 for c in ok)
            res["concurrent_runs"] = conc
            res["concurrent"] = {
                "width": a.concurrency,
                "wall_s": round(wall, 2),
                "n_ok": len(ok),
                "n_err": len(conc) - len(ok),
                # Headline first: aggregate cumulative throughput across the
                # concurrent batch, then the decode-only figure as detail.
                "aggregate_cumulative_tok_s": round((in_toks + out_toks) / wall, 2) if wall else None,
                "aggregate_decode_tok_s": round(out_toks / wall, 2) if wall else None,
                "errors": [c["error"] for c in conc if "error" in c],
            }
            print(f"  concurrent: {res['concurrent']}", file=sys.stderr, flush=True)

    res["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    Path(a.output).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k in ("model", "sequential", "concurrent")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
