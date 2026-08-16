# Benchmark traps + serving reference

The serving parser map, the serving flags that bite, and the traps checklist
that [`RUNBOOK.md`](RUNBOOK.md) links into. If a result looks wrong, walk the
checklist before blaming the model. Per-model-class failure modes live in
[`model-notes.md`](model-notes.md).

## Parser map

Wrong `--tool-call-parser` → empty `function.name` repair storms and 500s at
swap-in. Match the family exactly:

| Family | `--tool-call-parser` | `--reasoning-parser` | Notes |
| --- | --- | --- | --- |
| Qwen3 / Qwen3.6 general + Instruct (dense, MoE) | `hermes` | `qwen3` | Production-verified for the resident brain; **not** `qwen3_coder` |
| Qwen3-Coder / Coder-Next | `qwen3_coder` | `qwen3` | Coder builds only |
| Qwen3-Next (hybrid attention) | `hermes` | `qwen3` | Never spec-decode/MTP; no prefix cache |
| GLM-4.7-Flash | `glm47` | `glm45` | Thinking on by default |
| gpt-oss (harmony) | `harmony` | `gpt_oss` | Add `--disable-prefix-cache`; thinking via `reasoning_effort` |
| DeepSeek-V4-Flash | `deepseek` (+ `--enable-auto-tool-choice`) | `deepseek_r1` | Native `<think>` |
| Hermes-4 | `hermes` | — | — |

## Serving flags that bite

- **`--timeout` defaults to 300 s** and acts as a disconnect guard that kills any
  generation running longer — which a legitimate long agentic turn does. Use
  `--timeout 3600` for any agent-brain serving or bench.
- **`--gpu-memory-utilization`** sets the KV-cache clear trip
  (`device_mem × (util + 0.05)`); 0.80 standard, never >0.85. Keep
  `Σ(weights + caches) < trip < wired ceiling` (see
  [RUNBOOK Step 2](RUNBOOK.md#step-2--fit-check-capacity-rules)).
- **gpt-oss (harmony)** additionally needs `--disable-prefix-cache` — its
  alternating sliding-window attention is incompatible with the paged/prefix
  cache and throws `[broadcast_shapes]` failures otherwise.

## Traps checklist

### Trap 1: coding overlay is mandatory

Plain `humaneval`/`mbpp` score ~0 on chat-served models (the extractor grabs the
echoed prompt). Use `--include_path configs/lm-eval/qwen3-tasks --tasks
humaneval_instruct_qwen3,mbpp_instruct_qwen3 --confirm_run_unsafe_code
--log_samples`, with `HF_ALLOW_CODE_EVAL=1`.

### Trap 2: read math_verify

On `math-hard`, read the `math_verify` metric, not `exact_match` (prose-depressed
on chat output).

### Trap 3: lm-eval tasks flag

lm-eval (0.4.x) needs `--tasks a,b`. Positional task names silently select zero
tasks and the run reports success with no data.

### Trap 4: mlx-bench loads directly

`mlx-bench --model <id> --prompts 10` loads its own copy of the model. The server
must be DOWN, or the weights double-load and OOM the host.

### Trap 5: both thinking tracks

Agentic: run thinking ON and OFF, judge at conc4 + thinking-ON + large-ctx,
record the multi-turn `first_degraded_round` for each. Single-shot validity is
not a passing verdict; serve to match the winning track.

### Trap 6: sampling parity

A bench winner can misbehave in production if the sampling differs. The agentic
bench uses client defaults (temp 1.0). Production requests with
`temperature=None` + `repetition_penalty=None` let 4-bit quants degenerate into
repetition loops (same sentence 100+ times, ~37 duplicate tool calls/turn). When
a bench winner misbehaves live, check the **sampling delta first**. Guardrail for
4-bit Qwen-family: `repetition_penalty ~1.05`, `temp 0.6–0.7` in thinking mode.

### Trap 7: parser map

Wrong `--tool-call-parser` → empty `function.name` storms. Qwen3 general/Instruct
→ `hermes` (not `qwen3_coder`); Qwen3-Coder → `qwen3_coder`; GLM-4.7 → `glm47`;
gpt-oss → `harmony` (+ `--disable-prefix-cache`). Full map [above](#parser-map).

### Trap 8: serving flags

`--timeout` defaults to 300 s and kills long agentic generations — use `3600`.
`--gpu-memory-utilization` also sets the KV-cache trip
(`device_mem × (util+0.05)`); 0.80 standard, never >0.85. Keep
`Σ(weights+caches) < trip < wired ceiling`.

### Trap 9: publish token

Ambient `HF_TOKEN` is read-only, and **`doppler run` alone does not fix
this** — the `ai-ci-automation`/`prd` config holds both `HF_TOKEN`
(read-only) and `HF_TOKEN_REPOS_ADMIN` (write) as separate secrets,
`mlx-bench-publish` reads the literal env var `HF_TOKEN`, and `doppler run`
injects both — the ambient read-only one shadows the writer. Result: a 403
("you must use a write token") on the real publish call. **`--dry-run` does
not catch this** — it validates the envelope and schema but never makes the
HTTP call that checks token scope, so a dry-run can pass clean and the real
publish still 403. Override `HF_TOKEN` explicitly instead of trusting the
ambient injection:

```sh
HF_TOKEN="$(doppler secrets get HF_TOKEN_REPOS_ADMIN --plain -p ai-ci-automation -c prd)" \
  .venv/bin/mlx-bench-publish …
```

### Trap 10: run hygiene

Results land in `~/bench-runs*/` per host. Chain long runs with `nohup` and a
`===== <date> START/DONE <model> =====` log convention, and monitor those marker
lines to know where a chain is. Approximate suite timings (30B-A3B class):
coding ~3 h, math ~45 min, reasoning ~2.5–4 h, agentic full grid ~30 min.

### Trap 11: concurrency cascade masquerades as a serving failure

A driver run against a local llama-swap/MLX endpoint that returns a flood of
`429 {"error":"Too many requests"}` is **over-concurrency**, not a broken
model. llama-swap accepts `concurrencyLimit` in-flight requests; exceeding it
returns 429, the aiohttp session dies (`Session is closed` /
`ServerDisconnected`), and lm-eval's exception handler then throws
`UnboundLocalError: ... 'outputs'` — masking the real 429. Symptom on disk:
crashed tasks and invalid/zero results (the 2026-07-08 campaign: 9,262×429).

Fix: cap client concurrency to the endpoint's limit (`MLX_EVAL_CONCURRENT` /
`num_concurrent` / `--concurrency` = the endpoint's `concurrencyLimit`).
Verify: `grep -c 'Too many requests' <queue-log>` on a good run is 0.
Also expect **bimodal** concurrency scaling (2026-07-11 sweep): concurrent
requests either join one continuous batch (1.6–2.3× aggregate) or serialize
(~1.0×) — never assume a single c2 sample characterizes the endpoint.

### Trap 12: cold start folds into row 1 — warm before measuring

The first request after a model (re)load carries the whole cold-load cost
(measured: an 8.55 s 32-token first request vs 0.55 s warm — a +8 s artifact).
A naive sweep silently folds that into its first row. Always fire a throwaway
warm-up request before the measured run, and guard two-point decode math with
`dt > 0` (a cold row makes the slope negative). For TTFT, count the first SSE
`data:` chunk with content — `time_starttransfer` only measures header
arrival (llama-swap flushes SSE headers immediately).

### Trap 13: `mlx-eval`'s default model is host-specific

The wrapper's `${MLX_DEFAULT_MODEL:-<default>}` bakes in a *different*
default per host (e.g. `Qwen3.8-27B-4bit` on one machine,
`Qwen3-Coder-30B-A3B-Instruct-4bit` on another). A run that omits
`MLX_DEFAULT_MODEL` silently scores whatever that host's default happens to
be — no error, a plausible-looking result attributed to the wrong model.
Always pass `MLX_DEFAULT_MODEL=<full model id>` explicitly; never rely on the
wrapper default across hosts.

### Trap 14: task-level `until` stop sequences can zero a model's output

Some lm-eval tasks (e.g. `arc_challenge_chat`) carry a built-in
`until: ['\n\n', '.']`. If a model's answers structurally begin with one of
those strings (Qwen3.8-27B's do, with `"\n\n"`), the stop sequence fires
before any content is emitted — empty `resps`, and lm-eval logs
`"Could not parse generations: 'content'"`. This is a different failure than
the reasoning-budget-exhaustion case (`finish_reason=length` with real
reasoning tokens burned) — this one is an instant zero-length stop, silent
otherwise. Pass `--gen_kwargs "...,until=[]"` on every suite run against a
model with this answer shape.

### Trap 15: `exact_match` filters can score a correct model as zero

`arc_challenge_chat`'s `remove_whitespace`/`exact_match` filter expects a
bare letter answer. A model that reasons in full prose ("The best answer is
C") scores `exact_match=0` even when correct — measured: 15/15 zero while the
model was actually right in 13-14 of 15 (verified by reading `filtered_resps`
against `target`, not clipped — responses topped out at ~330 tokens against a
4096 cap). Same shape as the coding suite's mandatory qwen3-tasks overlay
(trap 1), but for reasoning: the extractor, not the model, is broken. Use a
flexible-extract task (`gsm8k`) instead of `arc_challenge_chat` for models
with this answer shape, and never report an `exact_match` number without
reading samples first.

### Trap 16: a standalone-server quant comparison isn't a production number

Serving through `llama-swap` applies per-model `filters.setParams` (e.g.
`frequency_penalty`/`presence_penalty`) that a bare standalone `mlx-lm-server`
does not — routing one arm of a comparison through llama-swap and the other
standalone samples them differently even at temperature 0, confounding the
one thing the comparison exists to isolate. Fix: run every arm as a
standalone server with byte-identical flags (only the model id differs).
Consequence: label results **"isolated from serving filters"** — they do not
describe production-through-llama-swap behavior. If the arms are also run
sequentially (e.g. hours apart, one quant fully before the next), only
per-item accuracy is a valid cross-arm comparison — temperature-0 greedy
decode makes correctness robust to ambient load, but latency/throughput is
not, so any timing delta between arms is within-arm descriptive only, never
attributed to the quant.

### Trap 17: a health gate that checks a claim, not an observation, can pass while false

A standalone server's `/v1/models` is a **claim** the process makes about
itself — an orphaned process from a prior run can keep answering that
endpoint with a stale or unrelated catalog after the port it's bound to was
meant to be freed. Health-gating on `grep <model-id> <(curl .../v1/models)`
only proves the string appears somewhere in that claim, not that the model
you asked for is the one actually generating. This nearly published a
complete, plausible 8-bit result set that was actually the 4-bit model still
resident from a prior phase — correct-looking sample counts, correct-looking
accuracy, no error anywhere, and nothing downstream could have told the
difference.

Two compounding causes, both worth guarding against on this stack
specifically:

- **`pkill -f "mlx-lm-server --model ..."` does not match the real process.**
  The actual binary launched is a wrapper, `mlx-lm-launch.py`, whose command
  line does not contain the literal string `mlx-lm-server` — a pattern kill
  aimed at the server name misses it, leaving an orphan alive on the port.
  Kill by **port** (`lsof -nP -tiTCP:<port> -sTCP:LISTEN`), not by a guessed
  process-name pattern.
- **A model *list* can be a static/stale claim; only a completion is an
  observation.** Verify readiness with a real chat completion and check the
  response's own `model` field against what was requested — a single-model
  server cannot lie about what it actually generated with, in the way a
  `/v1/models` listing can be stale, cached, or (as here) foreign.

The general lesson extends past this repo: a gate that asks the system what
it *offers* can pass on a claim; a gate that checks what the system just
*did* checks a fact. Prefer the latter for anything a wrong answer would
silently corrupt.

### Trap 18: a handful of sequential samples cannot characterize a bursty tier

A handful of sequential sub-second completions against a shared endpoint were
read as "the tier is idle and fast," while the server's own request log
showed a sustained, high rejection rate over the same window. A quiet minute
coexists fine with heavy contention on a `concurrencyLimit`-gated endpoint —
a handful of samples just has a good chance of landing in a gap. To
characterize load on a shared serving tier, read the server's own request
log for status-code distribution over a real window, not a handful of your
own latency probes.

### Trap 19: errno 65 vs errno 61 discriminates macOS Local Network Privacy from a real outage

A near-instant connection failure to a same-subnet peer is not automatically
"the network is down." **errno 65** (`EHOSTUNREACH`, "no route to host") fired
in under 5 ms means macOS's Local Network Privacy gate blocked the probe
before it left the host — a non-Apple-signed binary reached through a router
is exempt, but an on-link peer is gated unless the calling process holds a
grant. **errno 61** (`ECONNREFUSED`) means the probe reached the peer's TCP
stack and got a real answer — the gate is clear, and any remaining failure is
a real one. One PD-free plain-socket probe from the process that will
actually make the request answers "is this the privacy gate" without
spending anything. Do not diagnose a ~2 ms failure to an on-link host as an
outage, cable fault, or DNS problem before checking which errno it returned.

### Trap 20: a boot-scoped attempt ledger is not a kernel read

A ledger that increments on every *attempt* at a scarce boot-scoped resource
(an RDMA protection domain, a file descriptor, a lock) can overstate real
consumption whenever some attempts fail before ever reaching the point that
actually consumes the resource. Measured on the MLX cluster: a `pd-debt`
ledger counting kickstart attempts read `domains=3` while the real, kernel-
reported count was `0` — the counted attempts had all died before the domain-
allocating call ever ran. Trust the direct kernel instrument
(`ioclasscount <IOKit-class>` on macOS) over an attempt-counting ledger when a
scarce, non-reclaimable-without-reboot resource's exhaustion decides whether
to proceed.

### Trap 21: a shared log file's write order is not its timestamp order

A single log file fed by N concurrent writers (one process multiplexing
several subprocesses' stdout, or several workers logging to one file) has no
guaranteed relationship between line position and event time — two writers'
output can interleave so a later-timestamped line lands before an
earlier-timestamped one. Worse, **not every line class carries its own
timestamp**: on `mlx-model-server`'s `server.log`, the `[INFO]`/`[WARN]`/
`[ERROR]` access lines that carry every request's status code and duration
have no timestamp at all — only the separate Python-logging lines from each
worker do. Dating an access line by proximity to the nearest timestamped
line is unsound under concurrency, which is exactly the condition under
test when measuring serving load. Aggregate statistics over the whole file
can still be valid (measured: <1% of lines affected, aggregate rejection
rate unchanged) — dating any *specific* event this way is not. Also: this
file prints local time, not UTC: confirm which before filtering a window by
clock time.

### Trap 22: a converge/run that exits 0 is not proof it changed anything

At least three distinct causes produced a "success" exit with zero real
effect in one session: a deploy running from a stale checkout that predated
the commits it was meant to ship, an `--limit <group>` missing the
`,localhost` the inventory loader needs and matching zero hosts, and a
`--limit` naming a group the loader could not populate. All three reported
`failed=0`, exited 0, and deployed nothing. **Verify a deploy by its effect on
the target, never by its own exit code or by merge state in the source
repo**: grep the guest for the new code's marker (a string, a config value, a
file mtime), and prefer a two-part check — artifact present *and* some
liveness counter (a `runs` counter, a process restart) advancing across two
samples — over a single check, since a single check is exactly what each of
the failure modes above still passes. **A guard against this class of bug can
itself be defeated the same way**: a preflight that refuses to deploy from a
behind-HEAD checkout can still be bypassed by a detached-HEAD checkout, which
carries no branch name to compare against HEAD. A guard believed to be
protecting you while silently inert is worse than no guard, because nothing
about its presence signals the gap — document what a guard covers *and* what
still defeats it, not just that it exists.

### Trap 23: a source-file path can resolve to a stale build artifact, not the running code

Two agents each grepped "the same file" for a deployed marker and got
opposite answers — both were right about the file they read. A packaging
step had left a stale `build/lib/...` copy alongside the real source tree,
and a path guessed by directory convention landed on the stale one. **Ask
the runtime what it actually loaded, not a path you inferred**: for a Python
service, `<venv>/bin/python -c "import module; print(module.__file__)"`
resolves through the same import machinery (editable installs, `.pth`
finders) the running process uses; for a launchd job, resolve the binary via
`launchctl print`, never a `find` glob — a glob can just as easily return an
unrelated stale derivation. Report the resolved absolute path next to any
verification result, not just the marker it found.

### Trap 24: a cache read can report false agreement between two stale values

A generation-parity cache read `state=ok local=X deploy=X` on a host that
had since moved to a different revision — the cache simply hadn't refreshed
since the last converge, so it compared an equally stale value against
itself and reported success. **Two wrong values that agree with each other
are indistinguishable from two right values that agree** — the comparison
alone cannot tell you which. A false `ok` is worse than a refusal: a refusal
is visible and gets acted on; a false green is invisible until something
downstream breaks. When a cached comparison is load-bearing, cross-check at
least one side against a live read before trusting it, especially right
after any state-changing operation the cache might not have observed yet.

### Trap 25: probing an advertised-but-unloaded model can trigger the exact load you were trying to avoid

A model listed in `/v1/models` is a catalog entry, not evidence it is
resident (trap 17 already covers a stale catalog claim). The failure mode
here is different: on a pipelined serving cluster, requesting an
advertised-but-unloaded model does not 404 — it **triggers a real,
multi-hundred-gigabyte model load and hangs** while it happens, consuming
serving capacity and risking a downstream standdown if that load contends
with an already-running rank. Treating the request itself as a cheap
verification probe repeats the cost every time. Read the process list or the
rank's own log to learn what is actually loaded; never infer residency by
sending a request and seeing what happens.

### Trap 26: a PR listed as "landed" in a summary may still be open

A running list of "what's merged" drifts from reality the moment a PR sits
waiting on review or CI — restating it from memory or from an earlier
summary just propagates the drift. Confirm state directly before relying on
it: `gh pr view <number> --json state,mergedAt`. `state` and a non-null
`mergedAt` are the only trustworthy signal; a PR number appearing in prose
is not.
