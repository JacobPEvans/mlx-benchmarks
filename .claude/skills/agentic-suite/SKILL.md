---
name: agentic-suite
description: Use when driving the agentic tool-calling benchmark specifically — running harness/agentic/run.py against an endpoint, choosing the cell matrix, reading the multi-turn degradation track, or recovering partial results after a crash. For the general five-suite flow use the run-benchmark skill.
---

# Agentic tool-calling suite

Measures whether a served model produces **valid structured tool calls** while
carrying a 22-tool registry under load. Full description:
[`docs/agentic.md`](../../../docs/agentic.md). Runner:
[`harness/agentic/run.py`](../../../harness/agentic/run.py) — a standalone
PEP 723 script (`uv run` resolves its one dependency, httpx).

## Run it

```bash
uv run harness/agentic/run.py --base-url http://localhost:11434/v1 \
    --model <served-id> --api-key-env OPENAI_API_KEY
```

Never run against a busy Studio without asking — **one actor per host**.

- **Matrix:** thinking on/off × concurrency 1/4 × context small/large ×
  stream/nostream, plus the multi-turn track. Narrow with `--cells` (a
  comma-separated substring filter; include `multiturn` to keep that track).
- **Run both thinking tracks** — thinking changes the tool-call formatting path.
- **Pass signal:** `valid_tool_call_rate` (function name in the registry,
  arguments parse as JSON with all required keys, `finish_reason == tool_calls`).
- **Primary quant discriminator:** the multi-turn `first_degraded_round` —
  stock 4-bit Qwen3.x quants fall back to plain-text `[Tool call: ...]` around
  round 5 (mlx-lm #1011); single-shot cells cannot catch this.

## Warm-up and crash recovery

Each cell fires one **untimed warm-up** request excluded from every statistic
(first-request cold-start would skew the cell). The canonical results JSON is
written only after the whole matrix finishes; if a run dies mid-matrix, every
completed cell survives in `<output>.partial.jsonl` beside the output — one
JSON object per line, tagged `kind: cell` or `kind: multiturn`. A clean run
deletes it.

## Publish

```bash
mlx-bench-publish <output.json> --kind agentic --suite tool-calling
```

See the `publish-results` skill for the dry-run + write-token flow.
