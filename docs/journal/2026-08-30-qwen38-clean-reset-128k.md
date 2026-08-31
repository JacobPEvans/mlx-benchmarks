# 2026-08-30 — Qwen3.8 clean-reset 128k context campaign

This isolated campaign measured `mlx-community/Qwen3.8-27B-4bit` at a
131,072-token configured window with a 128,000-token prompt and a 64-token
output reservation. It started from a rebooted, zero-swap system with the
production model lifecycle quiesced. Each successful cell contains four
resident repetitions; the initial cold request is preserved separately and is
not included in the warm medians.

## Published cells

| Profile | Resident cumulative tok/s | Resident prefill tok/s | Resident decode tok/s | Concurrent result | Swap growth |
| --- | ---: | ---: | ---: | --- | ---: |
| Base c1 | 166.86 | 167.00 | 17.73 | n/a | 0 MiB |
| Native MTP c1 | 166.77 | 167.04 | 12.45 | n/a | 0 MiB |
| Native MTP c2 | 166.84 | 167.04 | 12.31 | one two-request probe: 2/2, 166.81 aggregate cumulative tok/s | 0 MiB |

The c2 probe admitted both requests without swap, but its aggregate throughput
matched c1. Under this native MTP configuration, long-prefill work queued rather
than increasing aggregate throughput.

Three immutable `throughput-probe` shards were published with campaign ID
`studio-clean-20260830` and distinct base-c1, MTP-c1, and MTP-c2 cell IDs.
Their source revision is `8cd852a4a06770510b3daf3fcab991a510510671`.

## Unscored c4 observation

The c4 server began four-way work with zero swap, but one stream completed and
three reached the harness's fixed 1,800-second stream timeout. This is
transport-limited evidence, not a capacity or quality result. The raw artifact
is retained but intentionally not published as a successful throughput shard.

The follow-up fix makes the probe's stream timeout configurable with
`--request-timeout-s`, so a future c4 test can choose a timeout appropriate to
the observed serialized long-context path.

## Capacity preflight

The model's full-attention component uses 64 KiB of KV per token per sequence.
At 128,000 plus 64 tokens that is 7.816 GiB per sequence, or 31.266 GiB for
four sequences. This is a preflight estimate only; hybrid linear-attention
state, weights, allocator behavior, and scratch space are outside the formula.
Runtime telemetry, rather than this estimate, determined the fit outcome.
