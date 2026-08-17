# Benchmark traps — multi-source-of-truth disagreement (30)

Continues [benchmark-traps.md](benchmark-traps.md#traps-checklist) (traps
1-12, harness-usage), [benchmark-traps-model.md](benchmark-traps-model.md)
(traps 13-18, model/eval-specific), and
[benchmark-traps-ops.md](benchmark-traps-ops.md) (traps 19-29,
infrastructure/operational). Not specific to benchmarking — it applies to
any system assembled from more than one independently-authored piece.

## Traps checklist

### Trap 30: two independently-correct sources can be combined into a value neither author would have written

A value built from two pieces — two formulas reading the same state, two
config fragments concatenated into one runtime input, two files merged at
load time — can have each piece individually correct and the combination
still wrong, because nothing forces anyone to read both pieces together.
Two real instances in one session, in unrelated systems: two memory-reading
formulas that each measured something real gave readings on opposite sides
of a decision threshold — both live, both a fair characterization of what
they measured, silently disagreeing with each other. Separately, a
scheduled job's prompt was assembled as one older instruction block plus a
newer override block concatenated into a single runtime prompt; the older
half asked for a health probe the newer half — added later, after an
incident that probe caused — explicitly forbade. Each half read as complete
and correct on its own; the contradiction was invisible until someone
traced the actual assembled prompt rather than either source file in
isolation. **Fix by tracing the actual combined/live value, not by trusting
either source read in isolation** — and where the combination is meant to
express one decision, prefer a single source of truth (a deterministic
script, one formula, one prompt) over runtime concatenation of parts
authored at different times for different reasons.
