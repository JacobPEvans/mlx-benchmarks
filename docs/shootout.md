# Agent-brain shootout — procedure

Which single model, running **alone** on the Studio, is the most accurate brain
for an autonomous agent that makes MCP tool calls, reads the results, and writes
factual digests?

This document is the operator procedure. It composes two existing pieces rather
than inventing a third: the [`agentic`](agentic.md) suite already measures
tool-call fidelity and latency, and the `factual` suite added alongside it
measures what the model does with what the tool returned. The
`mlx-bench-shootout` ranker combines them.

Candidate slate, with measured weights and rejection reasons:
[`../configs/shootout/candidates.toml`](../configs/shootout/candidates.toml).

> Everything this procedure produces is **PROVISIONAL**. One sweep cannot mature
> a verdict — see [`verdict-policy.md`](verdict-policy.md). The output gates
> *this cycle's* choice of brain, not a permanent judgment, and the wording rule
> ("leads/lags as of N runs", never "best") applies to every artifact from it.

## The three criteria, and how each is scored

Priority order is fixed: a model that cannot call tools reliably is not a brain
no matter how fast or how honest it is.

| # | Criterion | Metric | Where it comes from |
| --- | --- | --- | --- |
| 1 | Tool-call fidelity | `valid_tool_call_rate` at the gate cell, then multi-turn survival | `agentic` suite |
| 2 | Factual accuracy | `grounded_accuracy`, then `fabricated_number_rate` | `factual` suite |
| 3 | Latency | `request_latency_p50_ms` at the gate cell (TTFT reported alongside) | `agentic` suite |

Every number is computed by code from the raw results. No criterion needs a
human to read a transcript, and none uses a model as a judge.

### 1. Tool-call fidelity — programmatic pass/fail per call

The agentic runner sends a **22-tool registry** of realistic MCP-shaped
schemas (Splunk query/index/sourcetype, filesystem, shell, memory, wiki, Slack,
cron, web fetch) including near-duplicate distractors that force a choice
between similar names. A response is `valid` only when **all** of these hold:

- at least one structured `tool_calls` entry is present,
- the function name is non-empty **and in the registry**,
- the arguments parse as a JSON object carrying **every required key** for that
  tool,
- `finish_reason == "tool_calls"`.

Anything else lands in a failure taxonomy (`no_tool_call`, `empty_function_name`,
`bad_json_args`, `unknown_tool`, `stream_truncated`, …). Note what this already
covers: a model that emits `[Tool call: ...]` as prose instead of a structured
call produces no `tool_calls` and scores `no_tool_call`. **Leaking raw tool
syntax into prose is therefore already a scored failure**, and the 20-round
multi-turn track is what exposes it — stock 4-bit quants degrade into that
fallback around round 5 while looking perfect on single-shot.

Multi-turn survival is the share of rounds completed before the first
degradation, taken as the **worst** of the thinking-on and thinking-off tracks:
a brain that only holds together in one thinking mode is a brain with a footgun.

### 2. Factual accuracy — fixtures with a known answer

The `factual` runner ([`../harness/factual/run.py`](../harness/factual/run.py))
hands the model a tool result whose contents are known and asks for the digest a
human would read. Bank:
[`../configs/factual/fixtures/homelab-digest.json`](../configs/factual/fixtures/homelab-digest.json).
Four deterministic checks per response:

- **fact recall** — every `required_facts` entry appears (case-insensitive, or
  as a normalized number, so `1,284` satisfies `1284`).
- **fabricated numbers** — the metric the suite exists for. Every numeric token
  in the response must appear in the evidence, in the prompt, or in the case's
  declared `allowed_derived` list (a correct total, a row count — figures a
  faithful summary computes rather than copies). **Any residue is a
  fabrication.** Extraction is deliberately punctuation-blind and runs
  identically over evidence and response, so reformatting (`July 23, 2026` for
  an ISO timestamp) never reads as invention.
- **forbidden claims** — the plausible-but-wrong answer for that case:
  transposed digits on a large count, an inverted status, a retention figure for
  a case where the evidence carries none.
- **tool-syntax leak** — raw call syntax in prose that should carry none.

One case (`digest-004-absent-field`) has **no correct value to state**: the field
is missing from the evidence. A model that invents one fails; a model that says
so passes. That is the abstention behavior a digest-writing agent needs.

A response passes only on all four counts; `grounded_accuracy` is the share that
does.

### 3. Latency

Gate-cell `request_latency_p50_ms` and `first_token_p50_ms` from the agentic
suite, measured at concurrency 1 — the shootout is a single-user question.

### How the ranking combines them

`mlx-bench-shootout` sorts **lexicographically by the priority above**, never by
a weighted sum (a weighted sum would smuggle in importance numbers nobody
agreed). Rates are quantized to **0.10** before comparison, which is the verdict
policy's own Gate 2 divergence threshold for a bounded-[0,1] metric: two rates
closer than that are inside run-to-run drift, so they tie and the next criterion
decides. Latency — the one criterion where a small difference is real and
repeatable — is the final tiebreak. A model missing either suite is listed but
not ranked.

## Memory ceiling

The Studio is 128 GB unified with `iogpu.wired_limit_mb = 104000` (~109 GB
decimal), set in nix-darwin's `mac-studio` host config. The 2026-07-09 flagship
session measured the practical Metal allocation wall at **~92 GB** with
`--gpu-memory-utilization 0.80`.

The slate therefore caps candidate **weights at 75 GB**, leaving ~17 GB for the
KV cache, framework, and activation scratch. A 64K-token KV cache costs ~1.6 GB
on a `qwen3_next`-class hybrid but several times that on a dense 70B, so the
headroom is sized for the dense worst case.

Two things this budget is **not**:

- It is not the resident-fleet budget. Today the Studio holds an 80B brain plus
  a 27B judge simultaneously; the shootout evaluates one model alone, so it has
  materially more room than the deployed configuration.
- It is not the concurrency-4 budget that produced the 2026-07-09 negative
  result on the 50–90 GB tier. That wall was weights + **four** concurrent 20K
  KV caches. Every 40B+ model here is served single-slot, so the shootout runs
  at concurrency 1 and a 70 GB model is not disqualified by it.

## Running the sweep

### Before you start

1. **Take a maintenance window.** This procedure takes the Studio's production
   serving offline. Notify first, restore after — [`RUNBOOK.md` Step 3 Option
   B](RUNBOOK.md#step-3--serve-the-model) is the canonical bootout/restore
   sequence, including the watcher agents that will otherwise relaunch serving
   mid-window.
2. **One actor per host.** Confirm no other bench is in flight.
3. **Pre-fetch weights** into `/Volumes/HuggingFace` (`HF_HOME`) *before* the
   window. Downloading ~500 GB of candidates inside the window wastes the
   window; `hf download <id>` per candidate, outside it.
4. **Check the served name against the live catalog** once serving is up:
   `curl -s4 http://127.0.0.1:11434/v1/models`. Never trust a filename.

### Per candidate

Serve one model at a time — the memory budget assumes exactly one resident.

```sh
MODEL=<id from configs/shootout/candidates.toml>
SLUG=$(basename "$MODEL")

vllm-mlx serve "$MODEL" \
  --port 11434 \
  --tool-call-parser <parser> \
  --reasoning-parser <parser> \
  --gpu-memory-utilization 0.80 \
  --max-num-seqs 1 \
  --timeout 3600

# 1. Agentic — criteria 1 and 3. conc1 only: this is a single-user question.
uv run harness/agentic/run.py \
  --base-url http://127.0.0.1:11434/v1 --api-key-env OPENAI_API_KEY \
  --model "$MODEL" --concurrency 1 \
  --output "run-output/agentic_${SLUG}.json"

# 2. Factual — criterion 2.
uv run harness/factual/run.py \
  --base-url http://127.0.0.1:11434/v1 --api-key-env OPENAI_API_KEY \
  --model "$MODEL" \
  --output "run-output/factual_${SLUG}.json"
```

Parser flags come from the [parser map](benchmark-traps.md#parser-map). Two that
bite on this slate: **gpt-oss needs `--reasoning-parser gpt_oss`** or its harmony
channel markers leak into `message.content` (and it needs
`--thinking-kwarg reasoning_effort` on both runners); **`qwen3_next` models need
the paged KV cache off**, because paged-block reconstruction fails on every
multi-turn request.

Then rank:

```sh
mlx-bench-shootout run-output/ --gate conc1_think-on_ctx-large
```

### Wall-clock budget

Per candidate, at concurrency 1:

| Step | Time |
| --- | --- |
| Load + warm | 2–10 min (a 70 GB model from a cold cache is the slow end) |
| Agentic, conc1 only (8 cells × 10 repeats + 2×20 multi-turn rounds) | ~60–90 min |
| Factual (5 cases × 5 repeats × 2 thinking modes) | ~10–20 min |
| **Subtotal** | **~1.5–2 h** |

For 11 candidates: **~17–22 h of serving time for a single pass.** The verdict
policy requires a **validated consecutive pair** — every suite run twice with
identical config, both discarded if they diverge past the threshold — so a
protocol-valid sweep is **~35–45 h**, and that is one run of the four the policy
needs before any verdict stops being provisional.

Plan accordingly. Two ways to cut it that do not break the protocol:

- **Screen first, then replicate.** Run one unreplicated pass over all 11 to
  find the top ~4, then run validated pairs on those only. The screening pass is
  directional and must not be published or scored as a verdict.
- **Smoke before committing.** `--cells conc1_think-on_ctx-large_stream
  --repeats 3` on the agentic runner and `--thinking off --repeats 1` on the
  factual runner takes minutes per model and catches a wrong parser, a bad
  thinking kwarg, or a model that will not load — before you spend two hours on
  it.

### Afterwards

1. **Restore production first**, before any analysis:
   `launchctl bootstrap gui/501 ~/Library/LaunchAgents/dev.vllm-mlx.server.plist`
   plus the warmup and watcher agents ([RUNBOOK Step 3](RUNBOOK.md#step-3--serve-the-model)),
   then verify every resident reads `ready` at
   `curl -s4 http://127.0.0.1:11434/running`. **The incumbent brain is restored
   whether or not a challenger won** — adopting a new brain is a separate,
   deliberate change to the nix-ai catalog selection, never a side effect of
   benchmarking.
2. **Publish every run.** Never discard completed benchmark time — publish with
   `--tag caveat=<reason>` and file an issue instead.

   ```sh
   doppler run -p ai-ci-automation -c prd -- \
     .venv/bin/mlx-bench-publish run-output/factual_<slug>.json \
     --kind factual --suite grounded-summary --hostname jevans-ms
   ```

3. **Update [`../RANKINGS.md`](../RANKINGS.md)** in the same PR as the publish,
   keeping the maturity count and the provisional wording honest.

## Adopting a winner

A shootout result is an input to a decision, not the decision. Adoption means
changing the `class`/`roles` of a catalog entry in nix-ai's
`lib/hosts/mac-studio.nix`, and it needs the model's serve args validated into
`modules/mlx/catalog-data.nix` first. Physical model ids belong in that catalog
and in this repo's candidate list — **never in a nix module option or option
example**, which a CI check rejects.

Two adoption traps this fabric has already hit:

- **Sampling parity.** The 2026-07-08 winner passed every bench cell and then
  degenerated into repetition loops under production defaults, needing a
  `repetition_penalty` guardrail. Bench numbers are only valid at the sampling
  settings that produced them — ship the winning track's config, or re-bench at
  the config you intend to ship.
- **Environment class.** An isolated-window result says nothing about behavior
  under concurrent production load. The verdict policy requires both classes;
  the gap between them is itself a finding.
