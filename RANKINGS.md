# Model rankings

A single-pager ranking every model benchmarked in this repo, seeded from the
[`JacobPEvans/mlx-benchmarks`](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
HF dataset plus the per-run notes in [`docs/journal/`](docs/journal/). It is a
**snapshot**, not a live query — regenerate it with the loop in
[Keeping this page current](#keeping-this-page-current) after every publish.

A model is only "fully benchmarked" once it has a row with the required suites
filled: **throughput**, **coding**, **math-hard**, **reasoning**, and
**agentic tool-calling**. See [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for the
end-to-end procedure that produces each column.

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
- **Role** — the verdict: what this model is good for on this fabric.

## Agent-brain leaderboard (tool-calling, `jevans-ms`, 2026-07-08)

The decisive comparison: eight candidates for the resident tool-calling brain,
all run through the identical 22-tool agentic grid on the Studio. Ranked by
agentic fitness, then throughput. Single-stream tok/s is the agentic
`conc1-large` effective rate from the selection run.

| Rank | Model | Size GB | Agentic valid% (conc4/on/large) | Degraded round (thinking ON) | conc1-large tok/s | Role |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Qwen3.6-35B-A3B-OptiQ-4bit** | ~19.5 | 100% | **clean (20/20)** | 7.4 | **Resident brain** — needs thinking ON + repetition-penalty guardrail |
| 2 | Qwen3-Next-80B-A3B-Thinking-4bit | ~45 | 100% | round 17 | 12.0 | Runner-up; long-transcript pick, higher tok/s but heavier |
| 3 | Qwen3.6-35B-A3B-4bit (stock) | ~19.5 | 100% | clean (20/20) | 4.1 | Clean but ~half the winner's speed |
| 4 | Qwen3.6-35B-A3B-MLX-8bit (lmstudio) | ~35 | 100% | round 19 | 7.2 | Near-clean; 8-bit weight cost for one late slip |
| 5 | Qwen3.6-35B-A3B-8bit (mlx) | ~35 | 100% | round 6 | 7.2 | Degrades early despite 8-bit — quant recipe matters more than bit width |
| 6 | GLM-4.7-Flash-4bit | ~18 | 100% single-shot | round 1 (tool-dead) | 15.1 | Fastest here, but unfit as an autonomous brain |
| 7 | Qwen3-Coder-30B-A3B-Instruct-4bit | ~17 | 0% / 67% | round 1 | — | Coding sidecar only; malformed calls under agentic load |
| 8 | gpt-oss-120b-MXFP4-Q8 | ~63 | 0% | round 1 | 2.0 | Unfit as a tool-calling brain on this stack |

**Production addendum (winner):** OptiQ-4bit must be served with thinking ON
and a repetition-penalty guardrail (`repetition_penalty ~1.05`, `temp 0.6–0.7`).
With production defaults (`temperature=None`, `repetition_penalty=None`) the
4-bit quant degenerates into repetition loops (same sentence 100+ times, ~37
duplicate tool calls/turn) even though the bench cell passed — see the
[sampling-parity trap](docs/benchmark-traps.md#trap-6-sampling-parity) and the
[2026-07-08 journal](docs/journal/2026-07-08-agentic-brain-selection.md).

## Full catalog

Every model with at least one published metric. Blank = not yet run for that
suite. Throughput is the best published output tok/s (concurrency in
parentheses). `math_verify` is `minerva_math500`. Agentic is the pass-gate
`valid%` / `first_degraded_round` (thinking ON) where a `tool-calling` sweep
exists.

| Model | Size GB | Throughput tok/s | math_verify | Agentic (valid% / deg round) | Role |
| --- | --- | --- | --- | --- | --- |
| Qwen3.6-35B-A3B-OptiQ-4bit | ~19.5 | | | 100% / clean | Resident agent brain |
| Qwen3-Next-80B-A3B-Thinking-4bit | ~45 | 25.1 | 0.08 | 100% / r17 | Agent brain runner-up; weak on math_verify |
| Qwen3-Next-80B-A3B-Instruct-4bit | ~45 | 28.2 | 0.34 | | Strong all-rounder MoE |
| Qwen3.6-35B-A3B-4bit | ~19.5 | | | 100% / clean | Clean agent brain, slower |
| Qwen3.6-35B-A3B-8bit | ~35 | | | 100% / r6 | Early multi-turn degrade |
| Qwen3.6-35B-A3B-MLX-8bit (lmstudio) | ~35 | | | 100% / r19 | Near-clean agent brain |
| Qwen3-Coder-30B-A3B-Instruct-4bit | ~17 | 136.7 (c4) | 0.47 | 0–67% / r1 | Coding sidecar; throughput + math leader |
| Qwen3-Coder-30B-A3B-Instruct-8bit | ~32 | 41.2 | 0.37 | | Coding sidecar, 8-bit |
| gpt-oss-120b-MXFP4-Q8 | ~63 | 44.4 (c4) | | 0% / r1 | High-throughput generalist, not a tool brain |
| gpt-oss-120b-4bit | ~63 | 44.9 | 0.42 | | Generalist; strong math_verify |
| GLM-4.7-Flash-4bit | ~18 | | | 100%¹ / r1 | Fast, tool-dead multi-turn |
| Devstral-2-123B-Instruct-2512-4bit | ~63 | 2.5 | 0.42 | | Large coder; very slow decode |
| Devstral-Small-2-24B-Instruct-2512-4bit | ~13 | | 0.37 | | Small coder |
| Qwen3.5-122B-A10B-4bit | ~63 | 24.6 | 0.08 | | Legacy flagship MoE |
| Qwen3.5-35B-A3B-4bit | ~19.5 | 32.9 | | | Legacy A3B workhorse |
| Qwen3.5-27B-4bit | ~15 | 22.9 | | | Legacy dense mid |
| Qwen3.5-9B-MLX-4bit | ~5 | 68.5 | | | Small, fast |
| DeepSeek-R1-0528-Qwen3-8B-4bit | ~5 | 58.7 | | | Small reasoning distill |
| Seed-OSS-36B-Instruct-4bit | ~19 | 18.6 | | | Mid generalist |
| gemma-4-31b-it-4bit | ~17 | 18.4 | | | Dense generalist |
| gemma-4-e4b-it-4bit | ~3 | 59.9 | | | Tiny, fast |
| GLM-4.5-Air-4bit | ~60 | | 0.08 | | Legacy MoE |

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

3. **Edit the table** row for that model: fill the suite column, update the
   verdict if the new evidence changes it, and adjust the leaderboard ordering.
4. **Commit** in the same PR as the publish, so the ranking never drifts from
   the dataset.

A model graduates from "candidate" to a `Role` verdict only once the required
suite set (throughput + coding + math-hard + reasoning + agentic) is filled, or
once a single suite is decisive enough to disqualify it (a 0% agentic brain
needs no throughput number to be ruled out as a brain).
