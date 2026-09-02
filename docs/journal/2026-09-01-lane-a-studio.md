# 2026-09-01 — Lane A latency rows, Studio serving tier

Measurement only. Nothing on the serving tier was changed by this run: no config
edit, no unload, no reboot, no launchd action. Two attempts were made against the
27B tier model and one against the 35B-A3B, across two backends. One latency row
was obtained; the other three attempts produced failure-state evidence instead.

## Instrument and method

| Field | Value |
| --- | --- |
| Harness (row 1) | `harness.py`, stdlib only (urllib, ThreadPoolExecutor, time, json, uuid) |
| Harness sha256 (row 1) | `39fafc68734e8c6f3586b0179e5cc8aa68fd67baaf15aae2cbb5c9a7e634ca39` |
| Harness (row 2) | `harness2.py`, sha256 `df692e9c21320b6f5f5575fb9c5634b455ecbdf719525ba9c437779df5aa5665` |
| Run location | on the Studio itself, under `nohup` |
| Endpoint | the llama-swap loopback chat-completions endpoint |
| Client timeout | 300 s socket timeout, enforced in Python |
| Python | system `python3`, 3.9.6 |
| Cells | c = 1, 2, 4; 3 replicates each |
| Waits (row 1) | 15 s between replicates, 30 s between cells |
| Waits (row 2) | 5 s between replicates, 10 s between cells, to fit a shorter box |

`harness2.py` differs from `harness.py` only in what it records —
`finish_reason`, `content_len`, and a `valid` flag — plus wait durations moved to
argv. Request body, prompt hash, cells, and ordering are unchanged, so latency
figures from the two harnesses are comparable.

### Fixed request parameters

| Parameter | Value |
| --- | --- |
| Prompt | one fixed paragraph repeated 8x, pinned by sha256 |
| Prompt chars | 2856 |
| Prompt tokens, measured | 549–552 |
| `max_tokens` | 256 |
| `temperature` | 0 |
| `stream` | false |
| `enable_thinking` | not sent; server default |
| Per-request marker | `[rid=<uuid8>]` appended to the user message |
| Completion tokens, actual | 64–73 |

The brief specified a ~256-input-token prompt; the repeated paragraph renders as
roughly double that. The prompt is pinned by hash, so a post-switch rerun is
exactly comparable to this run. Only comparison against externally measured
figures at a different prompt size is affected.

### Join limitation

The `[rid=...]` markers cannot be joined to the llama-swap request log. That log
records no request body and no model id, so every marker greps to zero
occurrences; this was verified across 7 request ids. The available fields are
source address, method, path, HTTP status, response bytes, user-agent, and
server-side duration. Attributing a log line to a specific model would require
correlating with upstream model-server access lines, which carry a timestamp but
also no model id. All per-model attribution below therefore comes from the
harness and from direct process inspection, not from the request log.

## Row 1 — 35B-A3B on mlx-lm

Window 2026-09-01T21:07:13Z to 21:10:44Z. Admitted concurrency 2. Backend
`mlx-lm-server`, server version string `0.31.3-0.32.0-macOS-26.5.2-arm64`.
Warm-up at c1, excluded from the table: 1.372 s, 64 completion tokens.

| c | replicates | n requests | ok | p50 s | p90 s | max s | rejected 429 | hung TIMEOUT | tokens/s aggregate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | 3 | 3 | 1.23 | 1.26 | 1.26 | 0 | 0 | 56.0 |
| 2 | 3 | 6 | 6 | 1.66 | 1.68 | 1.68 | 0 | 0 | 78.4 |
| 4 | 3 | 12 | 6 | 1.68 | 1.70 | 1.70 | 6 | 0 | 79.1 |

Total requests issued against this model: 22, plus 3 one-token probes.

At an admitted concurrency of 2, exactly half of every 4-request replicate was
rejected, with wall times of 0.007 to 0.013 s. Surplus concurrency is refused at
the door rather than queued, so served latency at c4 is identical to c2 because
only 2 requests ever run. Aggregate throughput moves from 56 to 78 tokens/s
between c1 and c2 and does not move again at c4.

No failure fired during measurement. The post-cell probe returned 200 after every
cell, at 145.2, 147.1, and 176.0 ms.

## The 27B tier model — wedged before measurement began

The 27B dense model is what the router's default tier resolves to, and it was the
intended model under test. The pre-flight probe found it rejecting all traffic
before this session touched the host, and it was still rejecting afterward. Per
the brief it was recorded and not measured.

An instant 429 is produced both by a stuck admission counter and by a genuinely
saturated model, so the following evidence was gathered to separate them.

| Check | Result |
| --- | --- |
| Reported state | `ready` |
| 1-token probe, 4 attempts over ~2 min | 429 at 10.7, 19.7, 8.1, 9.0 ms |
| Direct probe to the model's upstream port, admission gate bypassed | timed out at 120 s |
| Model process CPU, sampled over 5 s | 0.0 %, state `S` |
| Process age | 7 h 54 m, alive and listening |
| Re-probe after the 35B run completed | 429 at 9.9 ms |

The process was alive, listening, and doing no work, yet answered neither the
proxy nor a direct request. Both the admission counter and the upstream server
behaved as though work were in flight while the process was idle.

No recovery was attempted during measurement; unloading a model on a serving tier
is a state change outside a measurement brief.

## The 27B after recovery — saturation, not a second wedge

The 27B was reloaded at 21:27Z. The identical harness, prompt hash, cells, waits,
and 300 s timeout were re-run against it at 21:28:38Z, admitted concurrency 2.

No latency baseline was obtained. Every request was rejected at the door.

| Event | Status | Wall |
| --- | --- | --- |
| Pre-flight 1-token probe | 429 | 7.2 ms |
| Warm-up | 429 | 0.006 s |
| c1 replicate 1 | 429 | 0.002 s |
| c1 replicate 2 | 429 | 0.003 s |
| c1 replicate 3 | 429 | 0.002 s |
| Post-cell probe 1 | 429 | 1.2 ms |
| Post-cell probe 2 | 429 | 2.7 ms |
| Post-cell probe 3 | 429 | 1.5 ms |

The harness aborted after cell c=1 per the recovery protocol; cells c=2 and c=4
never ran. Hung count 0.

The instant-429 signature was identical to the pre-recovery state, so the same
discriminator was applied. It returned the opposite verdict.

| Check | Before reload, 21:05Z | After reload, 21:33Z |
| --- | --- | --- |
| Process age | 7 h 54 m | 2 m 59 s |
| CPU, 5 s sample | 0.0 %, state `S` | 44.5 %, state `R` |
| Direct probe, gate bypassed | timed out at 120 s | 200 in 17.4 s |
| Verdict | stuck in-flight count | genuinely full, serving normally |

Twelve 1-token probes at 10 s intervals across 2 minutes were all rejected in 1.3
to 6.6 ms: zero admissions out of twelve.

Server-side durations of recent successful completions in that window included
1 m 33 s and 1 m 37 s. With a decode concurrency of 2 and individual requests
running past 90 seconds, both slots stay occupied. Trailing 150 request lines in
that window: 23 with status 200, 121 with 429, 6 with 404.

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

## Three states, one discriminator

Instant 429s alone separate none of these states. Process CPU plus a direct probe
past the admission gate separates all three.

| State | CPU | Direct probe | Verdict |
| --- | --- | --- | --- |
| 27B, 21:05Z, mlx-lm | 0.0 % | timed out at 120 s | model wedged |
| 27B, 21:33Z, mlx-lm | 44.5 % | 200 in 17.4 s | genuinely saturated |
| 35B, 23:09Z, vllm-mlx | 2.0 % | 200 in 1.93 s | gate rejecting, backend fine |

The rule "429 in under 20 ms while the model reports ready means wedged" fired on
a healthy model in two of the three cases. It cannot distinguish a stuck counter
from a full admission gate, because both produce instant 429s indefinitely.

A fourth state appeared later the same night, in Row 2b below.

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

## Tier-wide status counts

Bucketed from the request log by carrying the last-seen timestamp forward,
aggregated across all three resident models, local time. This spans the
measurement windows plus concurrent production traffic and cannot be attributed
per model, per the join limitation above.

| Window (local) | 200 | 429 |
| --- | --- | --- |
| 08:00 | 126 | 185 |
| 10:00 | 121 | 483 |
| 11:00 | 136 | 863 |
| 13:00 | 132 | 469 |
| 15:00 | 136 | 559 |
| 16:30 | 141 | 592 |

Successful responses are flat at roughly 130 per 30 minutes across the day while
rejections run 400 to 860. The 404s are a constant ~45 per 30 minutes from
something polling a metrics path the proxy does not serve.

## What this does and does not show

Shown:

- One latency row, 35B-A3B on mlx-lm, at c1/c2/c4 with the parameters above.
- That surplus concurrency beyond the admitted limit is rejected rather than
  queued on that backend, which is why c4 latency equals c2 latency.
- Three distinct states behind an identical instant-429 signature, and a
  two-check discriminator that separates them.
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
