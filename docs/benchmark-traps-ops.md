# Benchmark traps — infrastructure/operational (19-26)

Continues [benchmark-traps.md](benchmark-traps.md#traps-checklist) (traps
1-12, harness-usage) and
[benchmark-traps-model.md](benchmark-traps-model.md) (traps 13-18,
model/eval-specific). These are not specific to benchmarking — they apply to
any check against this stack's shared infrastructure.

## Traps checklist

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
resident
([trap 17](benchmark-traps-model.md#trap-17-a-health-gate-that-checks-a-claim-not-an-observation-can-pass-while-false)
already covers a stale catalog claim). The failure mode here is different:
on a pipelined serving cluster, requesting an advertised-but-unloaded model
does not 404 — it **triggers a real, multi-hundred-gigabyte model load and
hangs** while it happens, consuming serving capacity and risking a
downstream standdown if that load contends with an already-running rank.
Treating the request itself as a cheap verification probe repeats the cost
every time. Read the process list or the rank's own log to learn what is
actually loaded; never infer residency by sending a request and seeing what
happens.

### Trap 26: a PR listed as "landed" in a summary may still be open

A running list of "what's merged" drifts from reality the moment a PR sits
waiting on review or CI — restating it from memory or from an earlier
summary just propagates the drift. Confirm state directly before relying on
it: `gh pr view <number> --json state,mergedAt`. `state` and a non-null
`mergedAt` are the only trustworthy signal; a PR number appearing in prose
is not.
