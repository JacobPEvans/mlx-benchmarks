# Benchmark traps — infrastructure/operational (19-29)

Continues [benchmark-traps.md](benchmark-traps.md#traps-checklist) (traps
1-12, harness-usage) and
[benchmark-traps-model.md](benchmark-traps-model.md) (traps 13-18,
model/eval-specific). These are not specific to benchmarking — they apply to
any check against this stack's shared infrastructure. Next:
[benchmark-traps-consistency.md](benchmark-traps-consistency.md) (trap 30).

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

### Trap 27: splitting a file to satisfy a limit can silently break a reference nothing tests

Splitting an oversized file is the right fix for a size/token-limit
violation (see traps 19-22's own history: the split that produced this
file). But a split can sever a reference that nothing in the test suite
exercises, and the result passes green while quietly doing less than
before. Two real instances: a test that read an Ansible task **by name**
lost half its assertions the moment the task moved to a different file — it
kept passing, just against less; and a defaults file split to satisfy a size
limit left a lazily-resolved Jinja reference pointing at a variable
namespace that no longer had all the inputs it needed — latent until the
next clean run. **Splitting to satisfy a limit is correct. Preserving every
cross-reference across the split, and then verifying each one still
resolves, is the other half of the job** — the way this repo's own traps
splits kept every trap's numbering stable as an anchor and grepped the
whole repo for existing references before calling the split done (traps
19-22's split history). A split with no matching verification step is a
regression waiting for a quiet moment.

### Trap 28: absence of data is not evidence of absence of events

A dead-looking feed, an empty index, a silent log — all read as "nothing is
happening," and that reading is not always available to check independently
against reality: a service can be sending zero events for reasons that have
nothing to do with whether it has anything to say. On a config-driven
listener/ingest layer (log shippers, syslog listeners, metrics scrapers),
one common cause is a whole-file config template overwrite: a converge that
deploys a partial list silently deletes every entry not in that run's list,
and a target with no listener behaves identically, from the outside, to a
target with nothing to report — nothing alarms, because there is no signal
to alarm on. Treat a suspiciously quiet data source as **unverified, not
confirmed-idle**: check the listener/config side (is anything actually
configured to receive this) before concluding the silence is real.

### Trap 29: a `default()` on a value whose absence is an error condition turns a loud failure into a silent one

`| default('')` (or any language's equivalent — `.get(key, '')`, `?? ''`) is
correct when the value's absence is a legitimate, expected case: an optional
field, a feature flag nobody set. It is a bug magnet when the value's
absence means something upstream already broke, because the default doesn't
just fill in a gap — it replaces what would have been a loud, first-run
failure (an undefined-key error, a `KeyError`, a template render abort) with
a quiet, downstream one. One real instance: a template gated a config
stanza's emission on `{% if token_val | length > 0 %}`, where `token_val`
came from `some_map[key] | default('')`. A pre-role variable-combine bug (a
file split — see trap 27 — broke a lazy reference feeding that map) meant
some keys were silently absent from the map. Without the default, the
missing-key lookup would have raised on the very first run after the split,
failing loud and pointing straight at the cause. With it, the lookup
resolved to `''`, the `{% if %}` gate failed, and the config stanza simply
never rendered — exit 0, no error, and the missing output looked like normal
"not configured" state rather than a broken reference. It stayed
undiscovered for multiple days, the same shape as trap 22 (an exit code that
isn't proof) and trap 28 (missing output that reads as configured-absent
rather than broken). **Before adding a default to satisfy an
undefined-value error, ask whether the value's absence is expected or is
itself the failure.** If it's the failure, use a `mandatory`/assertion form
that fails loud at the point of absence, not a fallback that lets the gap
propagate downstream as missing output with no error attached.
