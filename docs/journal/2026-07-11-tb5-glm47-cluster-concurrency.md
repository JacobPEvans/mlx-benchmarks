# TB5 GLM-4.7 cluster + day-stack concurrency curves

**Date:** 2026-07-11 (supervised daytime session)

## Setup

| | |
| --- | --- |
| Hosts | MacBook (worker) + `jevans-ms` (coordinator), direct TB5 cable, Apple RDMA |
| Day stack | llama-swap + vllm-mlx, Coder-30B on both `:11434` |
| Cluster | `mlx_lm.server --pipeline` (pinned mlx-lm), GLM-4.7-4bit split 2 ranks, `:11440` |
| Harness | `harness/agentic/run.py --concurrency 1,2,4,8 --thinking off --context small --stream stream --repeats 10 --cells conc` |
| Env class | under-load (production live) for the day sweeps |

## Day-stack aggregate throughput under concurrency

Short tool-call requests (prefill included), warm endpoints:

| Concurrency | MacBook agg tok/s | `jevans-ms` agg tok/s |
| --- | --- | --- |
| c1 | 53.8 | 37.4 |
| c2 | 91.8 (**1.71×**) | 63.4 (**1.70×**) |
| c4 | 8/10 requests 429 | 65.0 (0 429s) |
| c8 | 8/10 requests 429 | 67.1 (0 429s) |

Findings (as of this single session — provisional, not a verdict):

- Both hosts show the same knee: **c2 ≈ 1.7× aggregate over c1**, then nothing.
  Concurrency pays on this stack — it is capped, not useless.
- Failure modes differ: the MacBook (`concurrencyLimit=2` at the time of
  measurement — raised to 4 the same day) hard-429s everything past 2
  in-flight with no queueing; `jevans-ms` absorbs 8 in-flight without erroring
  but serializes (flat ~65-67 aggregate).
- The overnight "c2 = 0.71×" result was a long-decode artifact of a different
  workload shape, not a law. Short-request aggregate improves at c2.
- Re-measure after the `concurrencyLimit` 2→4 change deploys: does the knee
  move to c4, and does anything batch rather than serialize?

## RDMA link redesign — validated live

- Cable physically moved ports on the coordinator side today; the new
  prep daemon (bridge detach + role-IP convergence onto the detected port)
  brought the link up with **zero manual steps**: bidirectional ping ~0.5 ms.
- **JACCL rendezvous is IPv4-only** in the pinned mlx-lm: every IPv6 form of
  `MLX_JACCL_COORDINATOR` fails with `Can't parse address` — scoped
  `[fe80::…%en2]:11441`, unscoped, and even `[::1]:11441`. Link-local
  discovery itself works (all-nodes multicast answered at 0.07 ms), so the
  zero-IP design is parked until JACCL learns IPv6; static synthetic IPs are
  the deployed default.
- First bring-up hit a startup race: the worker rank crash-looped with
  `[jaccl] Couldn't connect (error: 60)` while the coordinator rank was still
  initializing its rendezvous socket; launchd `ThrottleInterval` retries are
  the intended recovery. Torn down for the merged-stack redeploy rather than
  ridden out; watch for it on re-bring-up.

## Cluster measurements

(To be appended after re-bring-up on the merged stack: single-stream
two-point warm decode, c1→c8 aggregate on `:11440`, RDMA-transport evidence,
thermal soak, degradation drill, ideal-overnight-config recommendation.)
