# Config learnings log

Dated, append-only log of what we learn about serving parameters and specific
models. Each entry: what we observed, the evidence, and the takeaway. Newest
first. Do not rewrite past entries; correct them with a new dated entry.

## 2026-07-19 — OptiQ 35B was benchmarked without its own config

Context: c1 throughput benchmarks of `Qwen3.6-35B-A3B-OptiQ-4bit` vs the plain
`Qwen3.6-35B-A3B-4bit`, single-node, on the Studio. Initial reading was
"OptiQ collapses at long context." That reading was wrong; it was a config and
methodology artifact.

Findings, with evidence:

- MTP off. OptiQ `config.json` declares `mtp_file`, `mtp_tensor_count = 37`,
  `mtp_policy = optiq-int4-prequantized-gs64`. The serve command passed no
  `--enable-mtp`, and the served revision lacked `mtp.safetensors` (serve log:
  "[MTP inject] MTP weights not found"). A newer cached revision does contain
  it. So OptiQ ran with speculative decoding disabled.
- KV quant off. OptiQ ships `kv_config.json` (per-layer 4/8-bit, group_size
  64) — the defining feature of an OptiQ build. The serve command passed no
  `--kv-cache-quantization`. Full-precision KV was served.
- Prefix-cache confound. Serve logs show identical repeated long prompts
  warming the prefix cache: first long request ~15-20s, then ~3.3s
  (~77 tok/s) for BOTH models. bench-serve ran at the default
  cache-policy=preserve, so "long" numbers measured cache warm-up, not steady
  state. Warm long was ~77 tok/s for both OptiQ and vanilla.
- Reasoning-token metrics. With thinking enabled, streamed deltas carry
  `reasoning_content`, not `content`. bench-serve counts only `content`, so
  gen_tps read 0 for a thinking model. Ran thinking-off to get a countable
  number. Matches the known non-streaming/reasoning-metrics class.
- Under-load noise. The day-serving brain took live traffic during the runs,
  which alone explains erratic short/medium numbers.

Takeaways:

1. Config parity first. OptiQ must be served with `--enable-mtp` (+ draft
   tokens) and `--kv-cache-quantization` (bits/group-size per `kv_config.json`)
   on a revision that has the MTP weights. Until then any OptiQ number is a
   number for a crippled OptiQ, not OptiQ.
2. Comparisons must match serving correctness. Plain-vanilla (served right) vs
   OptiQ (served without its features) is a config mismatch, not a model
   comparison. Re-run both with each served per its own config.
3. Control the prefix cache when benchmarking. Use bench-serve
   `--cache-policy before-case` (or unique prompts) and interpret warm-only,
   or the numbers measure cache warm-up.
4. For thinking models, either bench thinking-off for a countable content-token
   rate, or use a metric that counts reasoning tokens.

Status of the two parquets published this day (OptiQ b19d7427, vanilla
767b514d): mis-configured OptiQ and cache-confounded; do not cite for model
selection. Re-bench pending a config fix and an isolated window.

## Parameter defaults worth remembering

- Prefix cache is ON by default. Repeated-prompt benchmarks warm it; control
  the cache policy or the throughput number is really a cache-hit-rate number.
- `--continuous-batching` is explicitly slower for a single user; do not enable
  it for c1 raw-throughput measurement unless matching a production config.
- `--max-kv-size` unset means unbounded per-sequence KV; reasoning models want
  >= 32768 so the think block is not evicted mid-generation.
- `--kv-cache-quantization` defaults to 8-bit when enabled; it is OFF unless
  the flag is passed, regardless of what `kv_config.json` says.
- `--enable-mtp` is OFF unless passed, regardless of MTP weights being present.
