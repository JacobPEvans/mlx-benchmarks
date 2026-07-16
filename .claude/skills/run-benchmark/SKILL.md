---
name: run-benchmark
description: Use when about to benchmark an MLX or locally-served model on this repo's hosts — running one or more of the five required suites, producing a dataset shard, or deciding whether a model counts as "fully benchmarked". Routes to the canonical RUNBOOK and the traps that silently corrupt results.
---

# Run a benchmark

The full any-model-any-host procedure is [`docs/RUNBOOK.md`](../../../docs/RUNBOOK.md).
Read it before running anything — this skill is the checklist, not a replacement.

## Do not get these wrong

1. **Five suites for "fully benchmarked":** `throughput`, `coding`, `math-hard`,
   `reasoning`, `tool-calling`. A model is not complete in
   [`RANKINGS.md`](../../../RANKINGS.md) until all five have a published shard
   (or one suite is decisive enough to disqualify the role).
2. **Fit check before serving** ([RUNBOOK Step 2](../../../docs/RUNBOOK.md#step-2--fit-check-capacity-rules)).
   **One actor per host** — never edit `llama-swap` config or restart serving
   while a bench is in flight.
3. **Environment class.** *under-load* = existing serving slot, production live.
   *isolated* = solo managed window ([RUNBOOK Step 3 Option B](../../../docs/RUNBOOK.md#step-3--serve-the-model));
   notify the user before taking production offline and restore after. A final
   verdict needs **both** classes ([`docs/verdict-policy.md`](../../../docs/verdict-policy.md)).
4. **Replicate.** Never score a single run — every benchmark is a consecutive
   pair; if the two diverge past the threshold (default >15% on the primary
   metric) discard both halves.
5. **Traps checklist before each suite:** [`docs/benchmark-traps.md`](../../../docs/benchmark-traps.md#traps-checklist)
   (coding overlay, `math_verify` not `exact_match`, `--tasks a,b`, server up/down
   per kind, both agentic thinking tracks, parser-family match).

## After a run

Publish each shard, then update `RANKINGS.md` in the **same PR** — see the
`publish-results` skill.
