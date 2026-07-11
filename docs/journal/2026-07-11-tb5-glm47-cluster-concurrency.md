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
- A/B after the `concurrencyLimit` 2→4 deploy (same host, same cells):
  c1 42.9 · c2 90.6 · **c4 105.9 (0 429s)** · c8 113.8 (6/10 429). The knee
  moved to the new limit: c4 is absorbed at ~2.5× c1 aggregate, but scaling
  past c2 is sub-linear (+17%), so this stack saturates around ~110 agg
  tok/s for short requests. Past-the-limit requests still hard-429 — the
  remaining gap is a queue at the router tier, not a bigger limit.

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
