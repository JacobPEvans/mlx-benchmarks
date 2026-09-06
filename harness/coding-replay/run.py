#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""coding-replay — replay merged PRs through an agentic CLI, score pass@1.

Per task: check out a worktree of the target repo at the PR's base commit,
prompt the configured agentic CLI (default: ``opencode run --pure --auto
--agent build --format json``) with the PR title + body and an instruction to
implement and stop (no commit, no PR), then score the run:

    pass@1 = check_rc == 0 AND overlap > 0

Exit code 0 alone is not a pass — a run that touches none of the real PR's
changed files and exits cleanly (e.g. a ``check: none`` task) must score a
failure. ``overlap`` is the count of changed files that intersect the real
PR's file list; ``check`` is a named repo check (``markdownlint``,
``tofu-validate``, ``ansible-lint``, ``nix-eval``, ``bats:<path>``,
``json-valid``, ``none``) run in the worktree after the CLI exits.

The local serving gate refuses rather than queues (one slot per model), so a
readiness probe waits for a real 200 completion before each task starts, and
a run whose stdout carries an HTTP 429 is retried once.

Run (never against a busy Studio without asking)::

    uv run harness/coding-replay/run.py \\
        --tasks-json configs/coding-replay/tasks.json \\
        --clone-map-json clone-map.json \\
        --work-dir /tmp/coding-replay-wt \\
        --base-url http://127.0.0.1:11434/v1 \\
        --model mlx/mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \\
        --tag run1 \\
        --output out.jsonl

The agent is PINNED in the default ``--agent-cmd``. An agentic CLI picks a
default primary agent from the runner's own configuration, and an
exploration-oriented one reads and greps without ever editing — which scores
as a model that cannot do the task. Measured on one model and one task: the
machine's default agent made 5 grep / 4 read / 1 glob / 2 bash calls and
changed nothing; ``--agent build`` made 6 edit calls and changed a file. Any
replacement ``--agent-cmd`` must pin an editing agent or the run measures the
operator's config rather than the model.

``--base-url`` is used ONLY for the readiness probe. The agentic CLI resolves
its own endpoint, so it must be configured separately or it will fail to reach
the model at all — for opencode that means ``OPENCODE_CONFIG`` pointing at a
config that declares the provider, and a ``--model`` of the form
``<provider>/<physical id>``. A bare physical id has no provider and the CLI
exits immediately.

``clone-map.json`` maps each task's ``repo`` (``owner/name``) to the local
path of its clone, e.g.
``{"dryvist/tofu-proxmox": "/Users/me/git/.../tofu-proxmox"}`` — not
committed; environment-specific.

Output is one raw-results JSON Lines file (one row per task), appended to as
each task finishes; publish it with ``mlx-bench-publish out.jsonl --kind
coding-replay --suite coding``.

Scoring, prompt construction, check selection, and result parsing live in
importable pure functions so ``tests/test_coding_replay_runner.py`` can
exercise them without a live endpoint, a served model, or a git checkout.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Pure functions (unit-tested via tests/test_coding_replay_runner.py)
# ---------------------------------------------------------------------------


def task_name(repo: str, pr: int) -> str:
    """``dryvist/tofu-proxmox`` + 1046 -> ``tofu-proxmox-1046``."""
    return f"{repo.rsplit('/', 1)[-1]}-{pr}"


def build_prompt(title: str, body: str) -> str:
    return f"Implement this change in the repository, then stop. Do not open a PR or commit.\n\nTitle: {title}\n\n{body or ''}"


def physical_model(model: str) -> str:
    """Strip a router-style ``mlx/`` prefix for the readiness-probe body."""
    return model.removeprefix("mlx/")


def parse_changed_files(porcelain: str) -> list[str]:
    """Parse ``git status --porcelain`` output into a list of changed paths."""
    files: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:  # rename: "old -> new"
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def overlap_files(changed: Sequence[str], pr_files: Sequence[str]) -> list[str]:
    """Changed files that intersect the real PR's file list, order preserved."""
    pr_set = set(pr_files)
    return [f for f in changed if f in pr_set]


def passed(check_rc: int | None, overlap: int) -> bool:
    """pass@1: a clean check AND at least one real-PR file actually touched.

    A clean exit / clean check alone is not enough — a run that touches
    nothing still exits 0 on a ``check: none`` task, and would otherwise
    score a false pass.
    """
    return check_rc == 0 and overlap > 0


def agent_launched(events: Sequence[Mapping[str, Any]], wall_s: float) -> bool:
    """Whether the agentic CLI actually started and produced a transcript.

    A CLI that cannot reach its model exits within a second having emitted no
    events (or one error event) — and that is INDISTINGUISHABLE from a genuine
    failure once scored: `pass` is False either way, `overlap` is 0 either way.
    A whole run in that state reads as a damning verdict on the model when the
    real fault is configuration. Measured: a bare physical model id with no
    provider produced exit 1, zero steps, wall 0.8s, and scored as a legitimate
    task failure.

    A real run always emits at least one ``step_start``/``step_finish``.
    """
    if wall_s < 2.0 and not any(e.get("type", "").startswith("step") for e in events):
        return False
    return any(e.get("type", "").startswith("step") for e in events)


def check_steps(check: str) -> list[list[str]] | None:
    """Ordered shell argv steps for a named repo check; ``None`` if unrecognized.

    Every step must exit 0 for the check to pass; the first non-zero exit
    short-circuits the rest.
    """
    if check == "none":
        return []
    if check == "markdownlint":
        return [["markdownlint-cli2", "**/*.md"]]
    if check == "tofu-validate":
        return [["tofu", "init", "-backend=false"], ["tofu", "validate"]]
    if check == "ansible-lint":
        return [["ansible-lint", "--offline"]]
    if check == "nix-eval":
        return [["nix", "flake", "check"]]
    if check == "json-valid":
        return [["jq", ".", "deployment.json.example"]]
    if check.startswith("bats:"):
        return [["nix", "shell", "nixpkgs#bats", "-c", "bats", check.removeprefix("bats:")]]
    return None


def is_rate_limited(raw_stdout: str) -> bool:
    """Whether a headless run's JSON stdout carries an HTTP 429 status."""
    return '"statusCode":429' in raw_stdout


def parse_events(raw_stdout: str) -> list[dict[str, Any]]:
    """Parse one JSON object per line, skipping any line that fails to parse."""
    events: list[dict[str, Any]] = []
    for line in raw_stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def aggregate_tokens(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Sum token counts across every ``step_finish`` event."""
    steps = [e["part"]["tokens"] for e in events if e.get("type") == "step_finish" and "part" in e]
    if not steps:
        return {"input": None, "output": None, "cache_read": None, "steps": 0}
    return {
        "input": sum(t.get("input") or 0 for t in steps),
        "output": sum(t.get("output") or 0 for t in steps),
        "cache_read": sum((t.get("cache") or {}).get("read") or 0 for t in steps),
        "steps": len(steps),
    }


def first_text_start_ms(events: Iterable[Mapping[str, Any]]) -> float | None:
    """Epoch-ms timestamp of the first streamed text part, or ``None``."""
    for e in events:
        if e.get("type") == "text":
            start = ((e.get("part") or {}).get("time") or {}).get("start")
            if start is not None:
                return float(start)
    return None


def ttft_seconds(first_text_start_ms_value: float | None, request_start_epoch_s: float) -> float | None:
    if first_text_start_ms_value is None:
        return None
    return round(first_text_start_ms_value / 1000 - request_start_epoch_s, 1)


# ---------------------------------------------------------------------------
# Orchestration (network + subprocess; exercised against fixtures, not live)
# ---------------------------------------------------------------------------


def wait_for_slot(base_url: str, model: str, attempts: int = 60, interval_s: float = 5.0) -> bool:
    """Poll the endpoint for a real 200 completion; the gate refuses rather than queues."""
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": "OK"}], "max_tokens": 1}
    ).encode()
    for _ in range(attempts):
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(interval_s)
    return False


def decode_timeout_stdout(raw: bytes | str | None) -> str:
    """Normalise ``TimeoutExpired.stdout`` to text.

    ``subprocess.TimeoutExpired.stdout`` carries RAW BYTES even when the call
    set ``text=True`` — the decoding wrapper never runs on the timeout path.
    This matters here rather than being a formality: a capped run is the common
    outcome for a slow local model, so the timeout branch is the hot path, and
    handing bytes to the event parser downstream would lose every task that ran
    out of clock.
    """
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", "replace")
    return raw


def run_agent(
    prompt: str, worktree: Path, model: str, agent_cmd: Sequence[str], timeout_s: int
) -> tuple[int, str]:
    """Run the agentic CLI headless in ``worktree``; returns (exit_code, stdout)."""
    argv = [*agent_cmd, "-m", model, prompt]
    try:
        proc = subprocess.run(
            argv, cwd=worktree, capture_output=True, text=True, timeout=timeout_s, stdin=subprocess.DEVNULL
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        return 124, decode_timeout_stdout(exc.stdout)


def run_check(check: str, cwd: Path) -> int:
    steps = check_steps(check)
    if steps is None:
        return 2
    for step in steps:
        rc = subprocess.run(step, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        if rc != 0:
            return rc
    return 0


def prepare_worktree(clone: Path, base: str, worktree: Path) -> None:
    subprocess.run(["git", "-C", str(clone), "worktree", "prune"], check=False)
    subprocess.run(["git", "-C", str(clone), "fetch", "-q", "origin", base], check=False)
    subprocess.run(["rm", "-rf", str(worktree)], check=False)
    subprocess.run(
        ["git", "-C", str(clone), "worktree", "add", "-q", "--detach", str(worktree), base], check=True
    )


def run_task(
    task: dict[str, Any],
    clone_map: Mapping[str, str],
    work_dir: Path,
    model: str,
    tag: str,
    agent_cmd: Sequence[str],
    base_url: str,
    task_timeout_s: int,
) -> dict[str, Any]:
    repo, pr, base = task["repo"], task["pr"], task["base"]
    name = task_name(repo, pr)
    clone = Path(clone_map[repo])
    worktree = work_dir / f"{name}-{tag}"
    prepare_worktree(clone, base, worktree)
    prompt = build_prompt(task["title"], task.get("body", ""))
    phys = physical_model(model)

    start = end = time.time()
    rc, stdout = -1, ""
    for attempt in range(2):
        if not wait_for_slot(base_url, phys):
            break
        start = time.time()
        rc, stdout = run_agent(prompt, worktree, model, agent_cmd, task_timeout_s)
        end = time.time()
        if is_rate_limited(stdout) and attempt == 0:
            subprocess.run(["git", "-C", str(worktree), "checkout", "-q", "--", "."], check=False)
            continue
        break

    events = parse_events(stdout)
    # Keep the agent's raw transcript. A scored zero is otherwise unexplainable
    # after the fact: `pass` false with `overlap` 0 looks identical whether the
    # model reasoned for the whole cap without reaching an edit, or emitted one
    # error and quit. Reconstructing that needed a separate probe run against a
    # live model, which is a poor substitute for having kept the evidence.
    transcript = work_dir / f"{name}-{tag}.transcript.jsonl"
    transcript.write_text(stdout)

    status = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain"], capture_output=True, text=True, check=False
    )
    changed = parse_changed_files(status.stdout)
    overlap = overlap_files(changed, task.get("files", []))
    check_rc = run_check(task["check"], worktree)

    return {
        "model": model,
        "tag": tag,
        "task": name,
        "repo": repo,
        "pr": pr,
        "exit_code": rc,
        "check": task["check"],
        "check_rc": check_rc,
        "overlap": len(overlap),
        "overlap_files": overlap,
        "changed": changed,
        "pass": passed(check_rc, len(overlap)),
        "agent_launched": agent_launched(events, round(end - start, 1)),
        "transcript": str(transcript),
        "tokens": aggregate_tokens(events),
        "ttft_s": ttft_seconds(first_text_start_ms(events), start),
        "wall_s": round(end - start, 1),
        "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--tasks-json", type=Path, required=True, help="task list: a JSON array of task objects")
    ap.add_argument(
        "--clone-map-json", type=Path, required=True, help="JSON file mapping repo -> local clone path"
    )
    ap.add_argument("--work-dir", type=Path, required=True, help="scratch directory for per-task worktrees")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", required=True, help="run tag recorded on every task row")
    ap.add_argument("--filter", default=".", help="regex over 'repo#pr', matched with re.search")
    ap.add_argument("--task-timeout-s", type=int, default=900)
    ap.add_argument(
        "--agent-cmd",
        # `--agent build` is load-bearing, not decoration. Without it the CLI
        # uses whatever primary agent the RUNNER'S OWN config makes default,
        # which on a customised machine is not a stock editing agent — measured
        # side by side on one model and one task, the default agent made 5 grep
        # / 4 read / 1 glob / 2 bash calls and changed no files, while
        # `--agent build` made 6 edit calls and changed one. Same model, same
        # prompt, same config: the benchmark was scoring the operator's agent,
        # not the model.
        default="opencode run --pure --auto --agent build --format json",
        help="agentic CLI invocation, split on whitespace; '-m <model> <prompt>' is appended. "
        "Must pin an editing agent, or results measure the runner's local agent config",
    )
    ap.add_argument("--output", type=Path, required=True, help="JSON Lines file; one row appended per task")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tasks = json.loads(args.tasks_json.read_text())
    clone_map = json.loads(args.clone_map_json.read_text())
    args.work_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(args.filter)
    agent_cmd = args.agent_cmd.split()

    with args.output.open("a") as out:
        for task in tasks:
            label = f"{task['repo']}#{task['pr']}"
            if not pattern.search(label):
                continue
            if task["repo"] not in clone_map:
                print(f"no clone mapped for {task['repo']}; skipping {label}", file=sys.stderr)
                continue
            row = run_task(
                task,
                clone_map,
                args.work_dir,
                args.model,
                args.tag,
                agent_cmd,
                args.base_url,
                args.task_timeout_s,
            )
            out.write(json.dumps(row) + "\n")
            out.flush()
            print(
                f"{row['task']}: pass={row['pass']} overlap={row['overlap']} check_rc={row['check_rc']}",
                file=sys.stderr,
            )
            if not row["agent_launched"]:
                # Abort rather than grind through the remaining tasks. Every
                # one would score a false failure, and a full sheet of zeros
                # reads as a verdict on the model instead of a broken setup.
                print(
                    f"ABORT: the agentic CLI did not run for {row['task']} "
                    f"(exit {row['exit_code']}, {row['wall_s']}s, no step events). "
                    "This is a configuration fault, not a model result — the CLI "
                    "resolves its own endpoint, so check its config and that "
                    "--model carries a provider prefix. No further tasks attempted.",
                    file=sys.stderr,
                )
                return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
