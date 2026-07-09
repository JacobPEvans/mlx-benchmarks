# 2026-07-09 — flagship isolated-window session (jevans-ms)

An 8-hour maintenance window (production offline) used to answer one question:
**can a 50–90 GB "flagship" model replace or complement the 35B-A3B resident
brain on the 128 GB Studio?** Every model below was served *solo* via
`vllm-mlx serve` (isolated environment class) after a clean
`launchctl bootout` of the nix serving agent. All results are **1 run,
PROVISIONAL** per the [verdict policy](../verdict-policy.md).

## Headline

**No 60–70 GB flagship is a viable brain for the concurrent cron fleet on this
hardware.** Two independent walls:

- **Memory wall (weights vs concurrent KV cache).** A ~70 GB-weight model plus
  four concurrent 20K-token KV caches exceeds the ~92 GB Metal allocation limit
  at `gpu-memory-utilization 0.80`. Qwopus-4bit (69 GB peaked at load) OOMs the
  moment the agentic grid hits concurrency 4 + large context.
- **Throughput wall (dense = slow).** A model small enough to leave KV headroom
  at 70B scale must be *dense* (Hermes-4-70B-4bit, 37 GB weights) — and a dense
  70B decodes at ~12 tok/s single-stream, which at concurrency 4 drops to
  ~3 tok/s per stream: the same fleet-saturation failure that took
  `Qwen3-Next-80B` out of the daily rotation.

The 128 GB Studio, **serving the concurrent fleet at 20K contexts**, is
structurally best matched by a **~20–45 GB MoE** brain (low active-param count
for speed, small weights for KV headroom) — which is exactly what the current
resident `Qwen3.6-35B-A3B-OptiQ-4bit` (19.5 GB, A3B) already is. A 70 GB
flagship only pays off for **low-concurrency dedicated serving** (a Hermes-only
endpoint, not shared with the cron fleet) or once **RDMA MacBook→Studio** adds
memory.

## Serviceability findings (vllm-mlx 0.4.0)

| Model | Size | Loads? | Note |
| --- | --- | --- | --- |
| `OpenYourMind/Qwopus3.5-122B-A10B-…-abliterated-MTPLX-4bit` | 69 GB | ✅ (VLM `strict=False`) | MTP weights absent (skipped); **abliterated** |
| `mlx-community/Qwen3.5-122B-A10B-OptiQ-2bit` | 65 GB | ❌ | `vision_tower.*` weights rejected by strict loader |
| `nightmedia/Qwen3.5-122B-A10B-Text-mxfp4-mlx` | 60 GB | ❌ | same `vision_tower` startup failure despite "Text" name |
| `lmstudio-community/Hermes-4-70B-MLX-4bit` | 37 GB | ✅ | dense 70B, text-only, Hermes-family |

The non-abliterated 122B-A10B community quants ship a `vision_tower` in their
weight index that vllm-mlx 0.4.0's strict loader will not skip; only the
abliterated Qwopus repackaging loads (via the tolerant VLM path). Serving a
non-abliterated 122B-A10B here needs a text-only re-export or a loader that
tolerates missing vision weights.

## Measured (isolated, single-stream)

| Model | Peak GB | Single-stream tok/s | conc1 valid (think ON / OFF) | conc4 valid | 20-round multiturn |
| --- | --- | --- | --- | --- | --- |
| Qwopus-122B-A10B-4bit | 69.1 → 75.4 | **52.8** | **1.0** / — | **0.0 (OOM)** | http_error (OOM) |
| Hermes-4-70B-4bit | 39.9 → **102.8** | 11.8 | 0.875 / **0.0** | **0.0 (OOM)** | **OOM (accumulated history)** |

Qwopus is a *flawless* single-stream tool-caller (perfect conc1 validity at
52.8 tok/s — the fastest brain-capable model benched here) but is disqualified
twice over: it OOMs under the production-shaped concurrent load, and it is
safety-**abliterated**, which is unacceptable for an autonomous agent wired to
shell/filesystem/cron tools. It is recorded, not adopted.

Hermes-4-70B-4bit is the opposite profile — tiny weights (37 GB) but a *dense*
70B, so (a) it decodes at only 11.8 tok/s, (b) it needs thinking ON (think-OFF
scored 0.0 at large context), and critically (c) its per-token KV cache is so
large that it OOMs **twice**: at concurrency 4 (peak 102.8 GB), *and* at
concurrency 1 once a 20-round agentic history accumulates. A brain that OOMs on
its own accumulated tool-call history cannot run a real agent loop. Disqualified.

**Both 70B-class models OOM under the real agentic shape (concurrent and/or
long-history) at `util 0.80`** — the memory wall is confirmed from two
independent mechanisms (big weights vs big dense-KV), not a single quant quirk.

## Actions taken this window

- Deleted a corrupt 55 GB `Qwen3.6-27B-4bit` partial (15 `.incomplete` markers,
  no complete safetensors).
- Cloned `mlx-benchmarks` onto the Studio so the agentic harness runs natively.
- Confirmed the `localhost`→IPv6/Caddy-TLS trap bites the agentic runner too
  (use `--base-url http://127.0.0.1:11434/v1`, never `localhost`).

## Recommendation

Keep `Qwen3.6-35B-A3B-OptiQ-4bit` as the resident/optimized brain — it is
correctly sized for this hardware + workload. Do **not** pursue a 70 GB
large-phase rotation brain until either (a) a dedicated low-concurrency Hermes
endpoint exists, or (b) RDMA adds memory. See
[`../../ansible-proxmox-apps` `docs/BRAIN_ROTATION.md`] re-enable gates.
