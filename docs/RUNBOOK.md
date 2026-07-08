# RUNBOOK — benchmark any model on any host

The end-to-end procedure for taking **any** model (any size, quant, or
architecture) on **either** Apple Silicon host and producing a complete,
published benchmark that lands in the
[HF dataset](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks) and
updates [`../RANKINGS.md`](../RANKINGS.md). Written so a fresh agent with zero
prior context can run it top to bottom.

This repo owns the **result contract and the publisher** — it does not run
models. The run commands (`mlx-eval`, `mlx-bench`, `vllm-mlx serve`) are thin
wrappers from the serving stack; this document says *which* to run, *in what
order*, and *which traps to avoid* (the traps and the serving parser map live in
[`benchmark-traps.md`](benchmark-traps.md)), then how to publish the output.

## What "fully benchmarked" means

A model is fully benchmarked only when all five required suites have a published
shard:

| Suite | `--kind` | `--suite` | Measures |
| --- | --- | --- | --- |
| Throughput | `vllm` | `throughput` | Output tokens/sec under batched load |
| Coding | `lm-eval` | `coding` | `humaneval`/`mbpp` pass@1 (chat overlay) |
| Math | `lm-eval` | `math-hard` | `minerva_math500` `math_verify` |
| Reasoning | `lm-eval` | `reasoning` | `arc_challenge_chat` / `gsm8k` |
| Agentic | `agentic` | `tool-calling` | Valid structured tool calls under load |

A model may be **disqualified for a role** before every suite runs — a 0% agentic
brain is not a brain no matter its throughput — but the catalog row in
`RANKINGS.md` is only "complete" when all five are present.

## Decision tree

```text
model arrives
  └─ 1. Identify + size it   → resident weight GB, architecture, quant recipe
        └─ 2. Fit check      → Σ(weights + caches) < GPU trip < wired ceiling?
              ├─ fits MacBook → run there (workstation; concurrencyLimit=2)
              └─ needs room   → run on Studio jevans-ms (128 GB)
                    └─ 3. Serve → existing llama-swap slot OR solo managed window
                          └─ 4. Run the 5 suites (mind every trap)
                                └─ 5. Publish each shard (Doppler write token)
                                      └─ 6. Update RANKINGS.md in the same PR
```

## Environments

Pick a host by fit and by who else needs the machine.

| | MacBook (workstation) | Mac Studio `jevans-ms` |
| --- | --- | --- |
| Memory | (workstation) | 128 GB unified, **wired ceiling ~118 GB** |
| Serving | `llama-swap`, `concurrencyLimit=2` | nix `dev.vllm-mlx.server` LaunchAgent |
| Endpoint | `http://localhost:11434/v1` | `http://127.0.0.1:11434/v1` (IPv4 plain HTTP) |
| Concurrency | **`MLX_EVAL_CONCURRENT=2` required** | up to 4 |
| HF cache | default | `/Volumes/HuggingFace` (`HF_HOME`) |
| Role | benches compete with your work | production serving host (Hermes) |

Two host rules that silently ruin a run if missed:

- **MacBook: `MLX_EVAL_CONCURRENT=2` is mandatory.** `llama-swap` there caps at
  `concurrencyLimit=2`. lm-eval 0.4.11 with a higher `num_concurrent` fires an
  instant burst of 429s and crashes with `Session is closed`, discarding hours
  of work. Match the eval concurrency to the server cap.
- **Studio: always `curl -s4 127.0.0.1`, never a hostname.** Caddy holds the
  *same* port on IPv6 with TLS; the plain-HTTP vllm-mlx server is on IPv4. Force
  IPv4 with `-4` and the literal `127.0.0.1`.

**One actor at a time.** Never edit the `llama-swap` config, restart the serving
LaunchAgent, or start a second `vllm-mlx serve` while a bench is in flight on
that host — the second loader contends for the same GPU memory and both runs
corrupt or OOM. Check for a live `mlx-eval` / `mlx-bench` / `vllm-mlx` / `run.py`
process and for a bench chain's log heartbeat
([trap 10](benchmark-traps.md#trap-10-run-hygiene)) before you start.

## Step 1 — Identify and size the model

1. **Confirm the served name against the live catalog** — never trust a doc or a
   filename:

   ```sh
   curl -s4 http://127.0.0.1:11434/v1/models | grep -o '"id":"[^"]*"'
   ```

2. **Estimate resident weight footprint.** Roughly 4-bit ≈ 0.55 GB/B params,
   8-bit ≈ 1.1 GB/B. A MoE keeps its *whole* weight set resident even though only
   the active experts compute per token — size by total params, not active. Add
   the KV cache budget (Step 2).

3. **Note the architecture and quant recipe** — they drive the serving flags and
   the [parser map](benchmark-traps.md#parser-map). Quant *recipe*
   (OptiQ/DWQ mixed-precision vs a stock uniform quant) matters more than bit
   width for agentic fitness — see [`model-notes.md`](model-notes.md).

## Step 2 — Fit check (capacity rules)

The GPU-memory-utilization flag also sets the point at which vllm-mlx **clears
the KV cache**:

```text
kv_cache_clear_trip = device_memory_gb × (gpu_memory_utilization + 0.05)
```

The invariant to satisfy:

```text
Σ(resident weights + KV caches for all resident models) < trip < wired ceiling
```

- `--gpu-memory-utilization 0.80` is standard. **Never exceed 0.85** — above it
  the trip crowds the wired ceiling (~118 GB on the Studio) and the machine
  swaps or the server is OOM-killed.
- If weights + caches don't clear the trip with headroom, the model doesn't fit
  on that host at that utilization — move to the Studio, drop to a smaller quant,
  or serve it solo.

## Step 3 — Serve the model

### Option A — existing `llama-swap` slot (no downtime)

If the model is already a `llama-swap` model on the host, target the endpoint;
`llama-swap` loads it on first request. Default on the MacBook and for any Studio
run that does not need a solo model. Do not edit the swap config mid-run.

### Option B — solo `vllm-mlx serve` in a managed window (Studio)

When the model isn't in the swap config, or you need the whole machine's memory
for one large model, take a **managed window** on the Studio. This takes
production serving (the Hermes brain) offline, so:

> **Notify the user before opening a managed window, and restore after.**
> Production Hermes is down for the duration.

```sh
# 1. Stop the production serving LaunchAgent
launchctl bootout gui/501/dev.vllm-mlx.server

# 2. Serve the target model solo (parser flags from the parser map + Step 2)
vllm-mlx serve <model-id> \
  --port 11434 \
  --tool-call-parser <parser> \
  --reasoning-parser <parser> \
  --gpu-memory-utilization 0.80 \
  --timeout 3600

# 3. ... run your suites against http://127.0.0.1:11434/v1 ...

# 4. Restore production serving when done
launchctl bootstrap gui/501 ~/Library/LaunchAgents/dev.vllm-mlx.server.plist
```

Pick `--tool-call-parser` / `--reasoning-parser` from the
[parser map](benchmark-traps.md#parser-map); mind the
[serving flags that bite](benchmark-traps.md#serving-flags-that-bite)
(`--timeout 3600`, `--gpu-memory-utilization ≤0.85`, gpt-oss needs
`--disable-prefix-cache`). On the Studio, HF auth may be unset — `export
HF_TOKEN=…` if the model needs downloading (cache on `/Volumes/HuggingFace`).

## Step 4 — Run the required suites

Run against the served endpoint. Timings are for a 30B-A3B-class model; scale up
for larger models. Full trap detail:
[`benchmark-traps.md`](benchmark-traps.md).

### 4a. Throughput (`--kind vllm --suite throughput`)

Two ways, never at the same time as anything else:

- **Against the running server** — vllm `benchmark_serving` (what the published
  Studio baseline uses). See
  [`../configs/vllm/benchmark_serving.toml`](../configs/vllm/benchmark_serving.toml).
- **Direct-load** — the nix-ai `mlx-bench` wrapper loads the model **itself**, so
  the server must be DOWN first ([trap 4](benchmark-traps.md#trap-4-mlx-bench-loads-directly)).

### 4b. Coding (`--kind lm-eval --suite coding`) — ~3 h

Chat-served models answer in prose + fenced code, so the **plain** `humaneval`
/`mbpp` extractors score ~0 as an artifact. **Always use the overlay**
([trap 1](benchmark-traps.md#trap-1-coding-overlay-is-mandatory)):

```sh
HF_ALLOW_CODE_EVAL=1 MLX_EVAL_CONCURRENT=2 mlx-eval \
  --include_path configs/lm-eval/qwen3-tasks \
  --tasks humaneval_instruct_qwen3,mbpp_instruct_qwen3 \
  --confirm_run_unsafe_code --log_samples \
  --output_path ./run-output/<slug>
```

Coding benchmarks **execute model-generated code** — read
[`../SECURITY.md`](../SECURITY.md) before running outside a sandbox.

### 4c. Math (`--kind lm-eval --suite math-hard`) — ~45 min

```sh
MLX_EVAL_CONCURRENT=2 mlx-eval minerva_math500 --output_path ./run-output/<slug>
```

Read the **`math_verify`** metric, not `exact_match`
([trap 2](benchmark-traps.md#trap-2-read-math_verify)).

### 4d. Reasoning (`--kind lm-eval --suite reasoning`) — ~2.5–4 h full

`arc_challenge_chat` (`--limit 15` ≈ 10 min) for a quick pass, `gsm8k` for the
canonical run. lm-eval 0.4.11 needs `--tasks a,b` — positional names select zero
tasks ([trap 3](benchmark-traps.md#trap-3-lm-eval-tasks-flag)). Excluded-task
rationale: [`../configs/lm-eval/reasoning.toml`](../configs/lm-eval/reasoning.toml).

### 4e. Agentic tool-calling (`--kind agentic --suite tool-calling`) — ~30 min

The decisive suite for an agent brain; the runner lives in this repo:

```sh
uv run harness/agentic/run.py \
  --base-url http://127.0.0.1:11434/v1 \
  --api-key-env OPENAI_API_KEY \
  --model <model-id> \
  --output run-output/agentic_<slug>.json
```

Run **both** thinking tracks and judge at the pass gate — concurrency 4, thinking
ON, large context. Single-shot validity is not sufficient; the multi-turn
degradation track is where quants fail
([trap 5](benchmark-traps.md#trap-5-both-thinking-tracks)). The serving config
you ship must match the winning track. Full grid + pass gate:
[`agentic.md`](agentic.md).

## Step 5 — Publish each shard

The publisher validates against `schema.json` and uploads a content-addressed
parquet shard. **Dry-run first.** The ambient `HF_TOKEN` is **read-only**;
publishing needs the Doppler write token
([trap 9](benchmark-traps.md#trap-9-publish-token)):

```sh
# Dry-run: validates + plans, no network
.venv/bin/mlx-bench-publish run-output/<...>.json \
  --kind <lm-eval|agentic|vllm> --suite <suite> --hostname <host> --dry-run

# Publish with the write token injected
doppler run -p ai-ci-automation -c prd -- \
  .venv/bin/mlx-bench-publish run-output/<...>.json \
  --kind <lm-eval|agentic|vllm> --suite <suite> --hostname <host>
```

`--hostname` records the producing machine even when you publish from another
(e.g. a Studio run uploaded from the MacBook). Dataset: `JacobPEvans/mlx-benchmarks`.
Never discard a completed run — publish it with `--tag caveat=<reason>` and file
an issue rather than throwing away benchmark time.

## Step 6 — Update RANKINGS.md

In the **same PR** as the publish, update the affected row in
[`../RANKINGS.md`](../RANKINGS.md) so the ranking never drifts from the dataset.
Pull the stored numbers back from the dataset (don't transcribe from memory) —
the exact loop is in that file's
["Keeping this page current"](../RANKINGS.md#keeping-this-page-current) section.

## See also

- [`benchmark-traps.md`](benchmark-traps.md) — traps checklist, parser map,
  serving-flag pitfalls.
- [`agentic.md`](agentic.md) — the agentic suite in depth (grid, pass gate).
- [`model-notes.md`](model-notes.md) — durable per-model-class serving quirks.
- [`../configs/LAYOUT.md`](../configs/LAYOUT.md) — the per-(tool, suite) configs.
- [`../RANKINGS.md`](../RANKINGS.md) — the current model leaderboard.
- Worked host walkthroughs: [`../examples/`](../examples/).
