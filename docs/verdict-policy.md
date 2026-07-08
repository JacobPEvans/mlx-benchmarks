# Verdict policy — when a model may be called best or worst

Benchmark numbers on this fabric drift over time — serving-stack state,
concurrent load, quant/toolchain updates, and sampling defaults all shift
results between runs. So **no model may ever be permanently dismissed or crowned
"best" from a single run.** A verdict is earned only after a model clears three
composing gates. Until then every verdict is **PROVISIONAL** and gates *actions*
("don't serve it as the brain this week"), never a permanent judgment.

`RUNBOOK.md`, `RANKINGS.md`, and `AGENTS.md` all defer to this file.

## The three gates

### Gate 1 — temporal maturity (≥4 runs, ≥5 days apart)

A model needs **at least 4 separate benchmark runs with 5 or more days between
each** before its verdict can move from provisional to final. Two runs less than
5 days apart count as one. The gap is the point: it samples across the random
environmental drift that a single run cannot see.

- Re-bench cadence: **≥5 days** between counted runs.
- Each run covers the **same required suite set** (throughput + coding +
  math-hard + reasoning + tool-calling — see [`RUNBOOK.md`](RUNBOOK.md)).
- Record the **environmental context** of every run (host, serving config,
  concurrent load) so variance is explainable rather than mysterious.

### Gate 2 — consecutive replication (validated pairs only)

Every benchmark is run **at least twice, back-to-back, with identical config**,
and the two results are compared **before publishing**:

- **Similar pair → validated.** Publish both (or their mean); the run counts
  toward Gate 1 maturity.
- **Divergent pair → discard entirely.** A large gap between two identical-config
  runs means the environment was unstable, so **both halves are invalid** and the
  run does **not** count toward maturity. Do not cherry-pick the better half.

**Default divergence threshold:** relative Δ > **15%** on the suite's primary
metric between the two runs — or, for a bounded-[0,1] rate metric, absolute
Δ > **0.10**. The threshold is **tunable**; record the value used. Primary
metrics: throughput → output tok/s; coding → pass@1; math-hard → `math_verify`;
reasoning → accuracy; tool-calling → `valid_tool_call_rate` (and
`first_degraded_round`).

A single unreplicated run is never published or scored.

### Gate 3 — both environment classes

Every model is benchmarked in **two** classes, recorded as separate result
dimensions. A divergence between them is itself a first-class finding.

| Class | Definition | Managed window? |
| --- | --- | --- |
| **ISOLATED** | Clean room — only minimal-impact processes; record what ran. | Only if it can't co-reside ([Step 3](RUNBOOK.md#step-3--serve-the-model)). |
| **UNDER-LOAD** | Production stays **live** — Hermes up, traffic flows, bench shares the GPU. | **No** — sharing the machine is the point. |

The under-load class needs no managed window, which drastically reduces
production downtime: managed windows are only for isolated-class runs of models
that cannot co-reside. Record per run: **environment class** + **what was
concurrently running** (a `llama-swap` `/running` snapshot and load average).

**Worked example — why the two classes exist.** Qwen3.6-35B-A3B-OptiQ-4bit
benchmarked **isolated** at 100% valid tool calls with zero multi-turn
degradation (clean through 20 rounds). The **same** model under concurrent
production load degenerated into repetition loops (the same sentence 100+ times,
~37 duplicate tool calls per turn) and needed a `repetition_penalty` guardrail to
serve. The isolated number alone would have crowned it unconditionally; the
under-load number is what caught the production failure mode. (The under-load
figure here is a production observation, pending a formal under-load bench.)

## How the gates compose

A model is **fully benchmarked with a final verdict** only when, **for each
environment class (isolated *and* under-load)**, it has **≥4 dated runs ≥5 days
apart**, where **each run is a validated consecutive pair** across the **full
required suite set**. Missing any of those → the verdict stays PROVISIONAL.

```text
final verdict  ⇐  isolated:   ≥4 runs (≥5 days apart), each a validated pair, full suite set
              AND under-load: ≥4 runs (≥5 days apart), each a validated pair, full suite set
```

## Counting maturity in RANKINGS

`RANKINGS.md` shows a maturity column as `N/4`, counting distinct benchmark dates
≥5 days apart per model. This is a **proxy**: a date only truly counts once its
run is a validated pair (Gate 2) recorded in a named environment class (Gate 3).
Historical shards predate the replicated-pair and env-class protocol, so **every
current verdict is PROVISIONAL regardless of its date count** — even a model
showing `4/4` dates has not yet been re-benched under the full protocol.

## Language rule

Before writing that a model is the best or worst anywhere — docs, PR bodies,
serving comments — check its maturity. Never write "X is the best/worst model."
Write **"X leads/lags as of N runs"** and, once past a gate, name the class
("isolated" vs "under-load"). A dismissal is "not serving it as the brain this
cycle," not "X is bad."
