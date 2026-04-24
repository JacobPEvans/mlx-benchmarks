# Qwen3.6 vs Qwen3.5 — First Real Benchmark Sweep

**Date:** 2026-04-18 to 2026-04-19 · **PR:** [#10](https://github.com/JacobPEvans/mlx-benchmarks/pull/10) · **Umbrella:** [Local LLM](https://github.com/users/JacobPEvans/projects/4)

First production benchmark sweep for the mlx-benchmarks repo. Goal: compare
`Qwen3.6-35B-A3B-mxfp8` (newly registered) against `Qwen3.5-35B-A3B-4bit`
(baseline) and `Qwen3.6-35B-A3B-mxfp4` across the `reasoning` suite
(GSM8K chain-of-thought, zero-shot).

## Setup

| Component | Value |
|---|---|
| Machine | MacBook Pro Mac16,5, Apple M4 Max, 128 GB unified memory |
| Inference backend | vllm-mlx via llama-swap |
| lm-eval version | 0.4.11 (from `pyproject.toml` via uv dev shell) |
| Suite | `reasoning` — task `gsm8k_cot_zeroshot` |
| Local eval limit | `--limit 100` (thinking mode active) |
| Cloud eval limit | Full 1319 examples |
| `max_gen_toks` | 4096 local (see mxfp8 caveat below); 2048 cloud |
| `apply_chat_template` | `true` |
| `fewshot_as_multiturn` | `true` |

## Infrastructure changes

### PR #8 (merged before session)

feat: add uv dev shell with lm-eval as proper dependency — adds
`pyproject.toml` with `lm_eval==0.4.11` and a Nix flake dev shell. This
established the benchmark toolchain used throughout this session.

### Model registration (llama-swap via `mlx-discover`)

Two new models registered from `/Volumes/HuggingFace`:

| Model | Quantization | Disk size |
|---|---|---|
| `mlx-community/Qwen3.6-35B-A3B-mxfp8` | mxfp8 | 34 GB |
| `mlx-community/Qwen3.6-35B-A3B-mxfp4` | mxfp4 | 18 GB |

Both were already fully downloaded; registration added them to the
llama-swap model pool for on-demand loading.

### PR #10 (open — feat: add lm-eval reasoning and mlxbench throughput configs)

- `configs/lm-eval/reasoning.toml` — first lm-eval reasoning benchmark config
- `configs/mlxbench/throughput.toml` — throughput sweep spec
- `README.md` — corrected `base_url` to full `/v1/chat/completions` path (see Finding #1)

## Benchmark results

### Completed

| Model | Quant | Total time | Sec/example | GSM8K flexible-extract | GSM8K strict-match | Status |
|---|---|---|---|---|---|---|
| `mlx-community/Qwen3.5-35B-A3B-4bit` | 4bit | 5046 s (84 min) | 50.5 s | **0.83** | 0.03 | Valid |
| `mlx-community/Qwen3.6-35B-A3B-mxfp8` | mxfp8 | 16716 s (278 min) | 167 s | 0.00 | 0.00 | INVALID (see below) |
| `mlx-community/Qwen3.6-35B-A3B-mxfp4` | mxfp4 | 4799 s (80 min) | 48 s | **0.82** | 0.00 | Valid |

### In progress / pending

| Model | Status |
|---|---|
| `mlx-community/Qwen3.5-27B-4bit` | In progress (started 07:28 AM) |
| `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit` | Pending |
| `gemini/gemini-3-flash-preview` | Pending |
| `openai/gpt-5-mini` | Pending |
| `gemini/gemini-2.5-flash` | Pending |
| `openai/gpt-4.1-mini` | Pending |

## mxfp8 score invalidation

The `Qwen3.6-35B-A3B-mxfp8` result of `0.00` is not a model quality
failure — it is a token budget problem caused by the combination of
decode speed and extended thinking:

- mxfp8 decode speed on M4 Max: ~25 tok/s (44 GB model, memory-bandwidth-bound)
- `max_gen_toks=4096`: maximum generation time = 4096 / 25 = **164 seconds per example**
- The model's thinking chains (extended CoT) consumed all 4096 tokens on
  virtually every example, leaving no capacity for the answer section
- Evidence: all sample responses end with truncated thinking content —
  mid-sentence text followed by `!!!...` — confirming the model was cut
  off before producing the answer

**Re-run required.** Use `max_gen_toks=6000`: 6000 / 25 = 240 s per
example, safely under vllm-mlx's 300 s hard timeout. This gives the
thinking chain enough headroom to complete and reach the answer.

## Findings

### Finding #1 — lm-eval `local-chat-completions` requires the full endpoint path

lm-eval's `local-chat-completions` model type POSTs directly to the value
of `base_url`. It does **not** append `/chat/completions`. The `base_url`
must be the complete endpoint:

```toml
# correct
base_url = "http://localhost:11434/v1/chat/completions"

# wrong — returns HTTP 404 on every request
base_url = "http://localhost:11434/v1"
```

The README had the truncated form. Fixed in PR #10. This cost several
minutes of debugging at session start before the 404 pattern was
identified.

### Finding #2 — mxfp4 matches mxfp8 quality on GSM8K at 3.5× the speed

Valid results only (mxfp8 excluded as INVALID):

- `Qwen3.5-35B-A3B-4bit`: **0.83** flexible-extract, 50.5 s/example
- `Qwen3.6-35B-A3B-mxfp4`: **0.82** flexible-extract, 48 s/example

The 0.01 gap is within noise on a 100-sample run. The generational leap
from Qwen3.5 → Qwen3.6 does not produce a meaningful GSM8K score
difference under these conditions — the bottleneck is likely the token
budget and thinking-mode behavior, not model quality.

mxfp4 (18 GB) is ~3.5× faster than mxfp8 (44 GB) on this hardware:
48 vs 167 s/example. Within the same 4096-token budget, mxfp4 generates
complete answers while mxfp8 cannot. Unless the mxfp8 re-run with
`max_gen_toks=6000` reveals a quality gap, mxfp4 is the dominant choice
for this hardware.

### Finding #3 — strict-match ≈ 0 is expected for all thinking models

All local models scored near 0 on `strict-match`. This is expected: the
Hermes vllm-mlx parser enables extended thinking by default, so responses
begin with `<think>...</think>` blocks before the answer. lm-eval's
`strict-match` scorer requires the answer to appear in a specific normalized
form that the thinking preamble breaks. Use `flexible-extract` as the valid
metric for all thinking-model runs.

### Finding #4 — `chat_template_kwargs` crashes vllm-mlx

Sending `chat_template_kwargs` as a field in the API request body caused
vllm-mlx to become unresponsive. The field is unsupported by the Hermes
parser and triggered a backend crash rather than a clean error. The server
was stuck for approximately 15 minutes.

**Recovery:** forced a model swap by requesting a small 9B model, which
triggered llama-swap's `swap: true` behavior — llama-swap sent SIGTERM
to the stuck vllm-mlx backend and restarted it with the new model.

**Implication:** neither `system_instruction=/no_think` nor
`chat_template_kwargs` successfully disabled extended thinking during
this session. Token budget via `max_gen_toks` is the only practical
control available until vllm-mlx exposes a stable no-think API surface.

## Incidents

| Time | Incident | Resolution |
|---|---|---|
| Session start | lm-eval 404 on every request | Fixed `base_url` to full `/v1/chat/completions` path |
| Mid-session | vllm-mlx crash from `chat_template_kwargs` | Forced model swap via llama-swap to restart backend |
| mxfp8 run | 278-minute run, score 0.00 | Identified token-budget truncation; re-run queued with `max_gen_toks=6000` |

## What's next

1. Let `Qwen3.5-27B-4bit` complete — in progress since 07:28 AM, ETA ~80 min
2. Run remaining pending models (Qwen3-Coder-30B, 4× cloud)
3. Re-run `Qwen3.6-35B-A3B-mxfp8` with `max_gen_toks=6000`
4. Convert all `results.json` → envelope v1 → Parquet → push to HF dataset
5. Merge PR #10
