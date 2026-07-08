# Model rankings

A single-pager ranking every model benchmarked in this repo, seeded from the
[`JacobPEvans/mlx-benchmarks`](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
HF dataset plus the per-run notes in [`docs/journal/`](docs/journal/). It is a
**snapshot**, not a live query — regenerate it with the loop in
[Keeping this page current](#keeping-this-page-current) after every publish.

A model is only "fully benchmarked" once it has the required suites filled —
**throughput**, **coding**, **math-hard**, **reasoning**, **agentic
tool-calling** — in **both** environment classes. See
[`docs/RUNBOOK.md`](docs/RUNBOOK.md) for the procedure that produces each column.

> **Every verdict below is PROVISIONAL.** Per the
> [verdict policy](docs/verdict-policy.md), no model is permanently dismissed or
> crowned "best" until it has **≥4 runs ≥5 days apart**, each a **validated
> consecutive pair**, in **both the isolated and under-load environment
> classes**. The Maturity column counts distinct benchmark dates ≥5 days apart
> as a proxy; historical shards predate the replicated-pair + env-class protocol,
> so even a `4/4` row is provisional until re-benched under it. Verdicts here read
> "leads/lags as of N runs", and they gate *this cycle's* actions, not permanent
> judgment.

## How to read the columns

- **Size GB** — approximate resident weight footprint of the quant, not the
  file size. Nominal; the capacity math in the RUNBOOK is what gates fit.
- **Throughput tok/s** — batched output tokens/sec from the `throughput` suite
  (vllm `benchmark_serving`), at the listed concurrency. This is *not* the same
  as the agentic single-stream tok/s — the two measure different things and are
  not comparable cell-to-cell.
- **math_verify** — `minerva_math500`, the `math_verify` metric (read this, not
  `exact_match`, which is prose-depressed on chat-served models).
- **Agentic** — `valid_tool_call_rate` at the pass gate cell
  (concurrency 4, thinking ON, large context), then the multi-turn
  `first_degraded_round` with **thinking ON** (`clean` = ran all 20 rounds).
  Multi-turn degradation, not single-shot validity, is the decisive signal.
- **Maturity** — `N/4`: distinct benchmark dates ≥5 days apart for the model (a
  proxy for [verdict maturity](docs/verdict-policy.md); all rows are provisional
  until `4/4` *and* collected as validated pairs in both environment classes).
- **Role** — the provisional verdict ("leads/lags as of N runs"): what this model
  is good for *this cycle*, not a permanent judgment.

All numbers below are **isolated-class** (or single-run legacy) measurements; no
model yet has a published **under-load** counterpart, which is required before
any verdict is final.

## Agent-brain leaderboard (tool-calling, `jevans-ms`, 2026-07-08)

The decisive comparison: eight candidates for the resident tool-calling brain,
all run through the identical 22-tool agentic grid on the Studio. Ranked by
agentic fitness, then throughput. Single-stream tok/s is the agentic
`conc1-large` effective rate from the selection run.

Ordered by *provisional* agentic standing this cycle; every row is 1 validated
run or fewer, so the order is a lead/lag as of now, not a final ranking.

| Prov. rank | Model | Size GB | Maturity | Agentic valid% (conc4/on/large) | Degraded round (thinking ON) | conc1-large tok/s | Role (as of N runs) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Qwen3.6-35B-A3B-OptiQ-4bit** | ~19.5 | 1/4 | 100% | **clean (20/20)** | 7.4 | Leads this cycle — resident brain; thinking ON + rep-penalty guardrail |
| 2 | Qwen3-Next-80B-A3B-Thinking-4bit | ~45 | 2/4 | 100% | round 17 | 12.0 | Runner-up; long-transcript pick, higher tok/s but heavier |
| 3 | Qwen3.6-35B-A3B-4bit (stock) | ~19.5 | 1/4 | 100% | clean (20/20) | 4.1 | Clean but ~half the leader's speed |
| 4 | Qwen3.6-35B-A3B-MLX-8bit (lmstudio) | ~35 | 1/4 | 100% | round 19 | 7.2 | Near-clean; 8-bit weight cost for one late slip |
| 5 | Qwen3.6-35B-A3B-8bit (mlx) | ~35 | 1/4 | 100% | round 6 | 7.2 | Degrades early despite 8-bit — quant recipe matters more than bit width |
| 6 | GLM-4.7-Flash-4bit | ~18 | 1/4 | 100% single-shot | round 1 (tool-dead) | 15.1 | Fastest here; lags as a brain this cycle |
| 7 | Qwen3-Coder-30B-A3B-Instruct-4bit | ~17 | 4/4† | 0% / 67% | round 1 | — | Coding sidecar this cycle; malformed calls under agentic load |
| 8 | gpt-oss-120b-MXFP4-Q8 | ~63 | 2/4 | 0% | round 1 | 2.0 | Lags as a tool-calling brain this cycle |

† Coder-30B has 4 distinct benchmark dates, but they are scattered single suites
predating the replicated-pair + env-class protocol — its verdict is still
provisional, a worked example of why date count alone does not finalize one.

**Production addendum (winner):** OptiQ-4bit must be served with thinking ON
and a repetition-penalty guardrail (`repetition_penalty ~1.05`, `temp 0.6–0.7`).
With production defaults (`temperature=None`, `repetition_penalty=None`) the
4-bit quant degenerates into repetition loops (same sentence 100+ times, ~37
duplicate tool calls/turn) even though the bench cell passed — see the
[sampling-parity trap](docs/benchmark-traps.md#trap-6-sampling-parity) and the
[2026-07-08 journal](docs/journal/2026-07-08-agentic-brain-selection.md). This
isolated-vs-under-load gap is the worked example behind
[verdict-policy Gate 3](docs/verdict-policy.md#gate-3--both-environment-classes):
the isolated pass and the under-load failure are both required before a verdict.

## Full catalog

Every model with at least one published metric. Blank = not yet run for that
suite. Throughput is the best published output tok/s (concurrency in
parentheses). `math_verify` is `minerva_math500`. Agentic is the pass-gate
`valid%` / `first_degraded_round` (thinking ON) where a `tool-calling` sweep
exists.

| Model | Size GB | Maturity | Throughput tok/s | math_verify | Agentic (valid% / deg round) | Role (as of N runs) |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B-OptiQ-4bit | ~19.5 | 1/4 | | | 100% / clean | Leads as agent brain this cycle |
| Qwen3-Next-80B-A3B-Thinking-4bit | ~45 | 2/4 | 25.1 | 0.08 | 100% / r17 | Agent brain runner-up; weak on math_verify |
| Qwen3-Next-80B-A3B-Instruct-4bit | ~45 | 1/4 | 28.2 | 0.34 | | Strong all-rounder MoE |
| Qwen3.6-35B-A3B-4bit | ~19.5 | 1/4 | | | 100% / clean | Clean agent brain, slower |
| Qwen3.6-35B-A3B-8bit | ~35 | 1/4 | | | 100% / r6 | Early multi-turn degrade |
| Qwen3.6-35B-A3B-MLX-8bit (lmstudio) | ~35 | 1/4 | | | 100% / r19 | Near-clean agent brain |
| Qwen3-Coder-30B-A3B-Instruct-4bit | ~17 | 4/4 | 136.7 (c4) | 0.47 | 0–67% / r1 | Coding sidecar; throughput + math leader this cycle |
| Qwen3-Coder-30B-A3B-Instruct-8bit | ~32 | 1/4 | 41.2 | 0.37 | | Coding sidecar, 8-bit |
| gpt-oss-120b-MXFP4-Q8 | ~63 | 2/4 | 44.4 (c4) | | 0% / r1 | High-throughput generalist; lags as a tool brain |
| gpt-oss-120b-4bit | ~63 | 1/4 | 44.9 | 0.42 | | Generalist; strong math_verify |
| GLM-4.7-Flash-4bit | ~18 | 1/4 | | | 100%¹ / r1 | Fast, tool-dead multi-turn |
| Devstral-2-123B-Instruct-2512-4bit | ~63 | 1/4 | 2.5 | 0.42 | | Large coder; very slow decode |
| Devstral-Small-2-24B-Instruct-2512-4bit | ~13 | 1/4 | | 0.37 | | Small coder |
| Qwen3.5-122B-A10B-4bit | ~63 | 4/4 | 24.6 | 0.08 | | Legacy flagship MoE |
| Qwen3.5-35B-A3B-4bit | ~19.5 | 1/4 | 32.9 | | | Legacy A3B workhorse |
| Qwen3.5-27B-4bit | ~15 | 1/4 | 22.9 | | | Legacy dense mid |
| Qwen3.5-9B-MLX-4bit | ~5 | 1/4 | 68.5 | | | Small, fast |
| DeepSeek-R1-0528-Qwen3-8B-4bit | ~5 | 1/4 | 58.7 | | | Small reasoning distill |
| Seed-OSS-36B-Instruct-4bit | ~19 | 1/4 | 18.6 | | | Mid generalist |
| gemma-4-31b-it-4bit | ~17 | 1/4 | 18.4 | | | Dense generalist |
| gemma-4-e4b-it-4bit | ~3 | 1/4 | 59.9 | | | Tiny, fast |
| GLM-4.5-Air-4bit | ~60 | 1/4 | | 0.08 | | Legacy MoE |

¹ GLM-4.7-Flash passes the single-shot pass-gate cell (100% valid) but the
multi-turn track collapses at round 1 — the exact case the degradation track
exists to expose. Single-shot validity alone is not a passing agentic verdict.

Cloud baselines (`reasoning` suite, `arc`/`gsm8k`, limit 100): `gemini-2.5-flash`,
`openrouter/auto`, `openai/gpt-4.1-mini` — reference points, not local candidates.

## Keeping this page current

This page is a snapshot of the dataset. After you publish a new shard
(`mlx-bench-publish …`), refresh the affected row here in the same PR. The
publish→edit loop:

1. **Publish** the run (see [`docs/RUNBOOK.md`](docs/RUNBOOK.md) → "Publish").
2. **Pull the new numbers back** from the dataset so the page reflects what was
   actually stored, not what you think you ran:

   ```sh
   .venv/bin/python - <<'PY'
   from huggingface_hub import HfApi, hf_hub_download
   import pyarrow.parquet as pq
   api = HfApi()
   files = [f for f in api.list_repo_files("JacobPEvans/mlx-benchmarks",
                                           repo_type="dataset") if f.endswith(".parquet")]
   rows = []
   for f in files:
       rows += pq.read_table(hf_hub_download("JacobPEvans/mlx-benchmarks", f,
                                             repo_type="dataset")).to_pylist()
   # filter rows to your model/suite and read metric/value/tag_* columns
   PY
   ```

3. **Edit the table** row: fill the suite column, bump the **Maturity** count if
   this is a new date ≥5 days from the last (and a validated pair — a divergent
   pair is discarded, not counted), and re-word the provisional verdict.
4. **Commit** in the same PR as the publish, so the ranking never drifts from
   the dataset.

A provisional verdict only becomes **final** once the model clears all three
gates of the [verdict policy](docs/verdict-policy.md) — ≥4 runs ≥5 days apart,
each a validated consecutive pair, in **both** the isolated and under-load
environment classes. Until then keep the "leads/lags as of N runs" wording; a
verdict gates this cycle's actions, not a permanent judgment.
