# 2026-09-01 — Lane A under vllm-mlx, Studio serving tier

The vllm-mlx half of the same run. Instrument, method, fixed request parameters,
and the mlx-lm rows are in
[2026-09-01-lane-a-studio.md](2026-09-01-lane-a-studio.md); this entry does not
repeat them. Three attempts are recorded here and none produced a complete row.

## Row 2 — 35B-A3B under vllm-mlx

Attempted at 2026-09-01T23:08Z. No latency row was obtained. The proxy rejected
100 % of traffic while the backend was idle and healthy.

The backend was `mlx-model-server` with continuous batching, prefix cache, paged
cache, a GPU memory utilization of 0.48, and a maximum of 8 sequences. Admitted
concurrency was therefore 8, not 2, and the c4 cell should have batched rather
than rejected.

| Event | Status | Wall |
| --- | --- | --- |
| Warm-up | 429 | 0.005 s |
| c1 replicate 1 | 429 | 0.002 s |
| c1 replicate 2 | 429 | 0.002 s |
| c1 replicate 3 | 429 | 0.002 s |
| Post-cell probe 1 | 429 | 1.3 ms |
| Post-cell probe 2 | 429 | 1.7 ms |
| Post-cell probe 3 | 429 | 1.9 ms |

Aborted after cell c=1; cells c=2 and c=4 never ran. No `finish_reason`,
`completion_tokens`, or `valid` value was recorded for any of these events,
because none of them reached the model.

The discriminator separates this from both earlier states.

| Check | Result |
| --- | --- |
| Model process CPU, up 7 m 13 s | 2.0–2.1 %, state `S` |
| Direct probe to the upstream port, gate bypassed | 200 in 1.93 s, `finish_reason=length`, 8 completion tokens, 31 chars, valid content |
| Via the proxy | 429 in 1.3–5 ms, every request |

The model answered a bypassing request in under 2 seconds with valid content at
2 % CPU. Trailing 60 request lines during the window: 12 with status 200, 45 with
429, 3 with 404.

## Row 2b — 35B-A3B under vllm-mlx, 35B-only variant

Attempted 2026-09-02T00:13Z. Partial row. The admission gate accepted and
rejected the same request shape seconds apart, on a model that was demonstrably
serving.

Only the 35B had moved to `mlx-model-server`; the 9B and 27B were still on
`mlx-lm-server`. Harness `harness3.py`, sha256
`22c354b250553a743373cca71750084922b99ce17d6e459aa66e65b092de5f54`. Its request
body and prompt hash are identical to rows 1 and 2; the only changes are an extra
c8 cell and cells moved to argv. The c8 cell is extra and is not part of the
identical comparison. Waits were the row-1 values on the first attempt and the
row-2 values on the second.

### Attempt 1, 00:13:51 to 00:15:17Z — total rejection

The warm-up, all three c1 replicates, and all three post-cell probes were
rejected. Seven 429s, zero served. Aborted after cell c=1.

### Interleaved manual check, 00:15:30Z — every path served

Run seconds after attempt 1 aborted, against the same model.

| Path | `max_tokens` | Result |
| --- | --- | --- |
| Via the proxy, small | 2 | 200 in 435 ms, `finish_reason=stop`, 2 tokens |
| Direct to the upstream port, small | 2 | 200 in 460 ms, `stop`, 2 tokens |
| Direct to the upstream port, exact harness payload | 256 | 200 in 5.94 s, `stop`, 73 tokens, 537 prompt tokens |
| Via the proxy, exact harness payload | 256 | 200 in 5.23 s, `stop`, 67 tokens, 537 prompt tokens |

Worker CPU 55–58 %, state `R`. Every path served valid content, including the
exact payload that had just been rejected seven times through the same proxy. The
payload shape is therefore not the cause.

### Attempt 2, 00:16:12 to 00:18:27Z — intermittent

| c | n | ok | valid | p50 s | p90 s | max s | rejected | hung | tokens/s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | 0 | 0 | — | — | — | 3 | 0 | — |
| 2 | 6 | 3 | 3 | 5.97 | 8.80 | 8.80 | 3 | 0 | 10.4 |
| 4 | 12 | 0 | 0 | — | — | — | 12 | 0 | — |

Aborted after cell c=4; the extra c8 cell never ran. The warm-up was rejected.
Every served response was valid: `finish_reason=stop`, 55 to 73 completion
tokens, no zero-token and no error finishes. The six post-cell probes alternated
429, 200 at 380.9 ms, 200 at 449.7 ms, 429, 429, 429.

### Classification — gate flapping, not wedged and not saturated

Probes returned 200 mid-run, the worker sat at 55–58 % CPU in state `R`, and a
manual request of the identical shape was served in 5.2 s. The gate admitted some
requests and refused others of the same shape within seconds. Half of the c2 cell
was served while the whole of c1 and c4 was refused, which is not an ordering a
concurrency limit produces.

### The one usable latency figure

At c2 the three served requests gave p50 5.97 s, p90 8.80 s, and 10.4 tokens/s
aggregate. Row 1 on mlx-lm at the same c2 gave p50 1.66 s and 78.4 tokens/s.
Both figures are recorded as measured. The c2 vllm-mlx figure rests on three
served requests drawn from a flapping gate, so no ratio between the two is
carried forward and no cause is assigned to the difference. A clean rerun is
required before either number is compared.

## What this does and does not show

Shown across both entries:

- One latency row, 35B-A3B on mlx-lm, at c1/c2/c4, in the
  [mlx-lm entry](2026-09-01-lane-a-studio.md).
- That surplus concurrency beyond the admitted limit is rejected rather than
  queued on that backend, which is why c4 latency equals c2 latency.
- Three distinct states behind an identical instant-429 signature, and a
  two-check discriminator that separates them, tabulated in the mlx-lm entry.
- A fourth state in Row 2b: a gate that admits and refuses the same request shape
  within seconds, on a worker that is serving.
- One partial row under vllm-mlx: at c2, three served requests gave p50 5.97 s
  and 10.4 tokens/s.

The serving tier was returned to mlx-lm after these runs.

Not shown:

- Any 27B latency figure on the current backend. Both attempts were rejected
  before reaching the model.
- Any complete 35B row under vllm-mlx. Row 2 was rejected entirely, and Row 2b
  produced only the c2 cell, from three requests.
- Any cause for the vllm-mlx rejections. What was measured is that the backend
  answered requests the gate was refusing; why the gate refused them was not
  determined here.
- Any valid comparison between the c2 figures on the two backends. Both are
  recorded as measured, but three requests from a flapping gate cannot support a
  ratio, and no cause is assigned to the difference.
- Any 9B behaviour. The 9B was out of scope and was not probed.

The 1.7 s figures in the 35B-A3B table are **not** comparable to the previously
quoted 16.8 s p50 / 21.1 s p90 / 79.1 s max at c4. Those were measured against
the 27B dense model, which could not be measured today. The 35B-A3B is a
mixture-of-experts model with roughly 3B active parameters per token, and this
run produced only 64–73 output tokens per request. Reading 1.7 s as an
improvement over 16.8 s would be an error.

Raw per-request JSON lines from these runs are held outside the repository; this
journal carries the derived tables only.
