# 2026-07-11 — MBP concurrency sweep: batching is real but bimodal; 429 wall moves 2→4

**Question.** The 2026-07-08 campaign collapsed in a 429 cascade (9,262×429 →
`Session is closed` → lm-eval `UnboundLocalError`), and an overnight two-point
probe (2026-07-11) measured c2 = 0.71× aggregate, concluding "MLX doesn't
batch". Is that true, and should the llama-swap `concurrencyLimit=2` cap move?

**Method.** Warm endpoint (`http://localhost:11434`, llama-swap v224 →
vllm-mlx 0.4.0, `--continuous-batching --max-num-seqs 4`), model
`Qwen3-Coder-30B-A3B-Instruct-4bit`. Per concurrency c: fire c identical
non-streaming 400-token chat completions in parallel; aggregate tok/s = Σ
`usage.completion_tokens` / wall. Warm-up request first (trap 12). Replicated
three times at `concurrencyLimit=4`.

**Results.**

| conc | limit=2 | limit=4 s1 | limit=4 s2 | limit=4 s3 |
| --- | --- | --- | --- | --- |
| c1 | 115.0 | 112.9 | 112.6 | 118.1 |
| c2 | 181.2 | 85.0 | 85.0 | 184.9 |
| c4 | 2 served + 2×429 | 134.4 | 269.0 | 116.6 |
| c8 | — | 4 served + 4×429 (268.4 agg on survivors) | — | — |

(aggregate tok/s; zero non-429 errors in every run)

**Findings.**

1. **Continuous batching works — sometimes.** Scheduling is bimodal: parallel
   requests either join one batch (c2 → 1.58×, c4 → up to 2.34×) or serialize
   (c2 → 0.74×, c4 → ~1.0×). The overnight "0.71×, MLX doesn't batch" claim
   sampled the serialized mode once; both modes are real (trap 11).
2. **Within the limit, nothing errors.** Worst case equals queueing —
   strictly better than the 429 the proxy returns above the limit.
3. **Decision:** raise `concurrencyLimit` 2→4 to match `maxNumSeqs`
   (nix-ai#1190); absorb above-limit 429s at the LiteLLM router tier with a
   rate-limit retry policy instead of deployment cooldown
   (ansible-proxmox-apps#863). Bench drivers stay pinned to the endpoint
   limit (RUNBOOK).

**Root cause of 2026-07-08 (for the record).** Client over-concurrency, not a
serving fault: lm-eval drove above the cap → 429 flood → aiohttp session death
→ lm-eval's own exception handler crashed (`UnboundLocalError: 'outputs'`),
masking the 429s. The crashed accuracy numbers are discarded, not
"real-but-degraded".
