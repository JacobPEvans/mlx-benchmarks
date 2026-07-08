# Agentic Tool-Calling — Brain Selection Run

**Date:** 2026-07-08

First full `agentic` tool-calling sweep (suite `tool-calling`, published to the
`mlx-benchmarks` HF dataset with `kind=agentic`, host `jevans-ms`). Goal: pick
the resident tool-calling brain for the always-on serving host by measuring
**valid structured tool calls** under production-shaped load rather than
single-shot toy registries. Per-run numbers live here; the durable per-class
lessons distilled from this run are in [`docs/model-notes.md`](../model-notes.md).

## Setup

| Component | Value |
| --- | --- |
| Host | `jevans-ms` (Apple M4 Max, 128 GB) |
| Registry | 22 tools (Splunk trio, filesystem, shell, memory, wiki, Slack, cron, web fetch + near-duplicate distractors) |
| Grid | concurrency 1 / 4 × thinking on / off × context small / large × streaming / non-streaming |
| Multi-turn | two 20-round tracks (thinking on / off), full accumulated history |
| Candidates | 8 |

## Results

| Model | Valid tool-call rate | Multi-turn (first degraded round) | conc1-large tok/s | Verdict |
| --- | --- | --- | --- | --- |
| **Qwen3.6-35B-A3B-OptiQ-4bit** | **100%** | **clean through 20 (thinking ON)** | 7.4 | **Winner — resident brain** |
| Qwen3-Next-80B-A3B-Thinking-4bit | 100% | round 17 | 12.0 | Runner-up (~45 GB) |
| Qwen3.6-35B-A3B-4bit (stock) | — | clean through 20 | 4.1 | Clean but slower |
| Qwen3.6-35B-A3B (lmstudio 8-bit) | near-clean | round 19 | — | Near-clean |
| Qwen3.6-35B-A3B (mlx 8-bit) | — | round 6 | — | Degrades early |
| GLM-4.7-Flash-4bit | — | tool-dead from round 1 | 15.1 | Fastest, unfit as agent brain |
| Qwen3-Coder-30B-A3B | 0% / 67% | — | — | Unfit as agent brain |
| gpt-oss-120b-MXFP4-Q8 | 0% | — | 2.0 | Unfit as agent brain |

## Reading

- **Thinking is required for this brain.** OptiQ-4bit ran 0/20 degradation with
  thinking ON but degraded at round 6 with thinking OFF — the mixed-precision
  quant alone does not carry multi-turn tool calling without the reasoning pass.
- **Speed does not equal agentic fitness.** GLM-4.7-Flash was fastest (15.1
  tok/s) yet tool-dead from round 1; gpt-oss-120b produced 0% valid structured
  calls. Both are disqualified as autonomous brains despite otherwise-attractive
  numbers.
- **Parser correctness is load-bearing.** A general Qwen3.6 MoE served on the
  `qwen3_coder` tool-call parser produced empty `function.name` repairs; the
  `hermes` parser (with `--reasoning-parser qwen3`, `enable_thinking:true`) runs
  it clean.

The winner is now the resident tool-calling brain and the Hermes agent's default
model behind the router alias.
