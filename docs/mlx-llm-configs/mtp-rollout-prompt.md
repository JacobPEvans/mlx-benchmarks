# MTP configuration-update prompt

Use this prompt in the source configuration repository, not in a generated host checkout.

```text
Update the local Mac LLM configurations using the Qwen3.8 MTP evidence in the mlx-benchmarks dataset.

First inspect the live catalog, model snapshot, serving backend/version, aliases, and host roles. Keep the model catalog as the single source of truth; do not duplicate per-host model commands. Preserve current parser, thinking, memory, security, and production-role behavior unless evidence below explicitly justifies a change.

Facts to preserve:
- Default 4-bit MTP at c1 measured 42.97/39.22 decode tok/s and 54.11/49.34 cumulative tok/s; the version-matched base measured 12.95/12.94 decode tok/s and 16.93/16.90 cumulative tok/s.
- Every throughput probe was capped at 256 output tokens, so it is a throughput result only, not a long-context, completion, or quality result.
- MTP c2/c4 did not scale in this probe: aggregate decode was 33.00/28.13 tok/s at c2 and 24.61/24.88 tok/s at c4, below serial MTP.
- c4 large-context tool calling was unsuitable in its small sample: 10%/10% valid on the pair; a longer-timeout smoke reached 33%. Do not select it as an agent brain.
- The math 20-sample difference (65% MTP vs 60% base) is not general quality proof because the base hit its 1024-token cap.

Implement only a capability-gated experimental MTP profile for a served snapshot that proves it has MTP weights and for a backend that supports the flags. It must be opt-in, c1-only, and unavailable to production or clustered roles. Retain the normal non-MTP profile as the default.

Do not modify clustered roles because this single-node experiment was faster. Before any routing change, run matched baseline/MTP pairs at 32k, 64k, and 128k contexts with 1, 2, and 4 concurrent requests where supported, output caps 512, 2048, and 8192, and record tok/s, TTFT, p50/p95 E2E latency, errors, completion/truncation, memory, and human quality. Publish every valid pair to the dataset run index. Screenpipe can promote only after shadow traffic shows p95 E2E latency no worse than 25% over the live 9B path and a clear human quality win.

Run the repository formatter, evaluation, and test suite. Report changed source files, matched tok/s evidence, and every remaining deployment gate.
```
