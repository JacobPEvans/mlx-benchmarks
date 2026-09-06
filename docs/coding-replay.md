# coding-replay — real-PR replay suite

Runs a small merged PR back through an agentic CLI against one served model
and scores whether the model actually landed the change, rather than whether
it produced *some* text and exited 0.

Runner: [`harness/coding-replay/run.py`](../harness/coding-replay/run.py).
Task list: [`configs/coding-replay/tasks.json`](../configs/coding-replay/tasks.json)
(JSON Lines — one real merged PR per line: repo, PR number, base commit,
title/body, changed files, and a named repo check). Converter:
[`../src/mlx_benchmarks/converters/coding_replay.py`](../src/mlx_benchmarks/converters/coding_replay.py),
`--kind coding-replay`.

## What "pass" means

```text
pass@1 = check_rc == 0 AND overlap > 0
```

`check_rc` is the exit code of the task's named repo check
(`markdownlint`, `tofu-validate`, `ansible-lint`, `nix-eval`, `bats:<path>`,
`json-valid`, `none`) run in the worktree after the CLI exits. `overlap` is
the count of changed files that intersect the real PR's file list.

A clean exit or a clean check is not by itself evidence of anything: a
`check: none` task, or a check that happens to pass on an untouched tree,
scores `check_rc == 0` whether or not the model changed a single file. Only
the overlap with the real PR's changed files proves the model touched the
right code — `passed()` in the runner is the single source of truth for this
and is unit-tested against exactly that false-green case.

## Envelope shape

One `pass_at_1` result per task (tags: `task`, `repo`, `check`, `check_rc`,
`overlap`), plus one aggregate `pass_rate` result across every task in the
run — the suite's headline number. `suite` is `coding` (shared with the
`lm-eval`/humaneval-mbpp coding suite in [`RUNBOOK.md`](RUNBOOK.md); this
suite does not feed a `RANKINGS.md` row of its own).

## Running it

Per task: a git worktree of the target repo at the PR's base commit, a
prompt of the PR title + body plus an instruction to implement and stop (no
commit, no PR), the configured agentic CLI headless with a timeout, then
scoring. The local serving gate refuses rather than queues (one slot per
model), so the runner polls for a real 200 completion before each task and
retries once if a run's stdout carries an HTTP 429.

```sh
uv run harness/coding-replay/run.py \
  --tasks-json configs/coding-replay/tasks.json \
  --clone-map-json clone-map.json \
  --work-dir /tmp/coding-replay-wt \
  --base-url http://127.0.0.1:11434/v1 \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --tag run1 \
  --output out.jsonl

.venv/bin/mlx-bench-publish out.jsonl --kind coding-replay --suite coding --dry-run
```

`clone-map.json` maps each task's `repo` (`owner/name`) to the local path of
its clone — environment-specific, not committed.
