# `vllm-mlx serve` parameter reference

Every flag `vllm-mlx serve` accepts, grouped by concern, with defaults and
tuning notes. Source of truth is `vllm-mlx serve --help` on the serving host —
regenerate and diff this file when the stack version changes. Do not add
parameters from memory.

Captured from vllm-mlx 0.4.0 (mlx 0.32.0, mlx-lm 0.31.3). Defaults in
parentheses are the tool's defaults, not our house values.

## Model identity and binding

- `model` (positional) — model id or local path to serve.
- `--served-model-name NAME` — name advertised by the API; defaults to the
  model argument.
- `--models-config YAML` — registry of models for lazy multi-model serving.
- `--host HOST` (localhost) — bind address. Use `127.0.0.1` for IPv4 loopback;
  `0.0.0.0` exposes externally.
- `--port PORT` — bind port.
- `--api-key KEY` — require this key for auth. Without it the server is open.
- `--rate-limit N` (0=off) — requests per minute per client.
- `--timeout SECONDS` (300) — default request timeout.
- `--enable-metrics` — expose Prometheus metrics on `/metrics`.

## Batching and concurrency

- `--max-num-seqs N` — max concurrent sequences.
- `--continuous-batching` — enable continuous batching for multiple concurrent
  users. Explicitly slower for a single user; leave off for c1 benchmarking of
  raw single-stream throughput unless matching a production config that uses
  it.
- `--prefill-batch-size N` — prefill batch size.
- `--completion-batch-size N` — completion batch size.
- `--prefill-step-size N` (2048) — chunk size for prompt prefill. Larger uses
  more memory but can raise prefill throughput.
- `--chunked-prefill-tokens N` (0=off) — max prefill tokens per scheduler step.
  Prevents active requests starving during long prefills.
- `--stream-interval N` (1) — tokens batched before streaming. 1 is smooth;
  higher favors throughput. Note: affects when tokens surface to a streaming
  client, which can shift measured TTFT.

## Prefix cache (dominates repeated-prompt throughput)

- `--enable-prefix-cache` (default on) — cache shared prompt prefixes.
- `--disable-prefix-cache` — turn it off.
- `--prefix-cache-size N` (100, legacy mode only) — max entries.
- `--warm-prompts FILE` — JSON list of message arrays pre-run at startup to
  populate the prefix cache, so the first real request hits warm (cold TTFT
  drops 1.3-2.3x on agent workloads). Keep the file small (1-3 entries).

Benchmarking caution: with prefix cache on, repeated identical prompts warm
the cache across reps, so later reps run much faster than the first. This
inflates or destabilizes "throughput" numbers unless the cache policy is
controlled. See `learnings.md` (2026-07-19 OptiQ entry).

## KV cache sizing and quantization

- `--cache-memory-mb MB` (auto ~20% RAM) — cache memory pool limit.
- `--cache-memory-percent F` (0.20) — fraction of RAM for cache when
  auto-detecting.
- `--no-memory-aware-cache` — use legacy entry-count cache instead.
- `--max-kv-size N` — max KV cache size per sequence; when set uses a rotating
  KV cache that bounds memory but loses early context. Reasoning models
  (Qwen3, DeepSeek-R1) should use >= 32768 so the think block is not evicted
  mid-generation.
- `--kv-cache-quantization` — quantize stored KV caches to save memory (8-bit
  by default). Required to actually serve a model whose `kv_config.json`
  declares KV quantization.
- `--kv-cache-quantization-bits {4,8}` (8) — bit width.
- `--kv-cache-quantization-group-size N` (64) — group size.
- `--kv-cache-min-quantize-tokens N` (256) — minimum tokens before quantization
  applies.
- `--ssd-cache-dir DIR` (disabled) — directory for an SSD KV cache tier.
- `--ssd-cache-max-gb GB` (10.0) — max SSD cache size.

Note: these serve flags apply KV quantization uniformly. A model's
`kv_config.json` may declare per-layer bit widths; confirm how the stack
reconciles the two before claiming parity (open question, see `learnings.md`).

## Paged cache

- `--use-paged-cache` (experimental) — paged KV cache for memory efficiency.
- `--paged-cache-block-size N` (64) — tokens per cache block.
- `--max-cache-blocks N` (1000) — maximum cache blocks.

## MTP — Multi-Token Prediction (speculative decoding)

- `--enable-mtp` — enable MTP for models with built-in MTP heads. Uses cache
  snapshot/restore for speculative generation. Required to get the speedup on
  any model that ships MTP weights (`mtp_file` / `mtp_*` in `config.json`).
- `--mtp-num-draft-tokens N` (1) — draft tokens per MTP step.
- `--mtp-optimistic` — skip the MTP acceptance check for max speed, at the cost
  of ~5-10% wrong tokens. Good for chat, not for code.

## SpecPrefill (long-prompt TTFT reduction)

- `--specprefill` — use a small draft model to score token importance, then
  sparse-prefill only the important tokens on the target. Cuts TTFT on long
  prompts. Requires `--specprefill-draft-model`.
- `--specprefill-threshold N` (8192) — minimum suffix tokens to trigger it;
  shorter prompts use full prefill.
- `--specprefill-keep-pct F` (0.3) — fraction of tokens kept during sparse
  prefill. Lower is faster but loses more quality.
- `--specprefill-backbone-pct F` (0.0) — fraction of chunks reserved for evenly
  spaced sparse-prefill coverage.
- `--specprefill-draft-model PATH` — small draft model for importance scoring.
  Must share the target model's tokenizer.

## MLLM draft (vision assistant drafting)

- `--mllm-draft-model PATH` — an mlx-vlm MLLM draft/assistant model.
- `--mllm-draft-kind {mtp}` — draft kind for the MLLM draft model.
- `--mllm-draft-block-size N` — draft block size passed to mlx-vlm.
- `--mllm-prefill-step-size N` (0=MLLM default 1024) — override MLLM prefill
  step guard.
- `--mllm` — force load as multimodal even if the name does not match
  auto-detection.

## Generation defaults (sampling)

These override per-request defaults only when the request omits the field.
Prefer the model's own `generation_config.json` values (see
`model-config-files.md`); set these to match it, not to impose a house value.

- `--default-temperature F` — default temperature.
- `--default-top-p F` — default top_p.
- `--default-top-k N` — default top_k.
- `--default-min-p F` — default min_p.
- `--default-presence-penalty F` — default presence_penalty.
- `--default-repetition-penalty F` — default repetition_penalty.
- `--default-thinking-token-budget N` (None=unlimited) — cap reasoning tokens
  by forcing the end-think sequence when exhausted. Per-request
  `thinking_token_budget` overrides.
- `--default-chat-template-kwargs JSON` — chat template kwargs applied when the
  request omits them, e.g. `{"enable_thinking": true}`.

## Reasoning and tool-call parsing

- `--reasoning-parser NAME` — extract `<think>...</think>` into
  `reasoning_content`. Options: qwen3, deepseek_r1, gpt_oss, harmony, gemma4,
  glm4, mistral. Note: when reasoning is parsed, thinking tokens land in
  `reasoning_content`, not `content` — throughput tools that count only
  `content` will read zero (see `learnings.md`).
- `--enable-auto-tool-choice` — enable auto tool choice; needs a parser.
- `--tool-call-parser NAME` — parser for tool calls. Options: auto, mistral,
  qwen, qwen3_coder, llama, hermes, harmony, gpt-oss, deepseek, kimi, granite,
  nemotron, xlam, functionary, gemma4, glm47, minimax.
- `--trust-remote-code` — allow HF remote code during model/tokenizer load.

## Memory limit and lifecycle

- `--gpu-memory-utilization F` (0.90) — fraction of device memory for the Metal
  allocation limit and the emergency cache-clear threshold. Raise toward 0.95
  for very large models (200GB+) that need headroom.
- `--auto-unload-idle-seconds N` (0=off) — unload the main model after this
  many idle seconds.
- `--lazy-load-model` — register at startup but defer load until first request.
- `--max-tokens N` (32768) — default max generation tokens.
- `--max-request-tokens N` (32768) — max `max_tokens` accepted from clients.

## Auxiliary models and IO limits

- `--embedding-model ID` — pre-load an embedding model at startup.
- `--rerank-model ID` — pre-load a reranker at startup.
- `--mcp-config PATH` — MCP configuration for tool integration.
- `--max-audio-upload-mb N` (25) — max uploaded audio size.
- `--max-tts-input-chars N` (4096) — max characters for `/v1/audio/speech`.

## Download and offline

- `--download-timeout SECONDS` (300) — per-file download timeout.
- `--download-retries N` (3) — download retry attempts.
- `--offline` — only use locally cached models.
