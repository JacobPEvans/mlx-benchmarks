"""Unit tests for the coding-replay runner's pure functions.

``harness/coding-replay/run.py`` is a standalone PEP 723 script (not part of
the package), so it is loaded here via importlib — the same pattern
``test_agentic_runner.py`` and ``test_factual_runner.py`` use. It has no
network or subprocess dependency at import time, so no live endpoint, served
model, or git checkout is needed to exercise these functions.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def _load_runner() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "harness" / "coding-replay" / "run.py"
    spec = importlib.util.spec_from_file_location("coding_replay_run", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


# --- task_name / build_prompt / physical_model ---------------------------------


def test_task_name() -> None:
    assert runner.task_name("dryvist/tofu-proxmox", 1046) == "tofu-proxmox-1046"
    assert runner.task_name("dryvist/ansible-proxmox-ai", 655) == "ansible-proxmox-ai-655"


def test_build_prompt_includes_title_and_body() -> None:
    prompt = runner.build_prompt("fix: ignore plan files", "adds tfplan* to .gitignore")
    assert "fix: ignore plan files" in prompt
    assert "adds tfplan* to .gitignore" in prompt
    assert "Do not open a PR or commit" in prompt


def test_build_prompt_tolerates_empty_body() -> None:
    prompt = runner.build_prompt("title only", "")
    assert prompt.endswith("title only\n\n")


def test_physical_model_strips_router_prefix() -> None:
    assert runner.physical_model("mlx/mlx-community/Qwen3.8-27B-4bit") == "mlx-community/Qwen3.8-27B-4bit"
    assert runner.physical_model("mlx-community/Qwen3.8-27B-4bit") == "mlx-community/Qwen3.8-27B-4bit"


# --- parse_changed_files / overlap_files ----------------------------------------


def test_parse_changed_files_handles_ordinary_and_renamed_entries() -> None:
    porcelain = " M modules/proxmox-stack/locals.tf\n?? new-file.tf\nR  old.tf -> new.tf\n"
    assert runner.parse_changed_files(porcelain) == [
        "modules/proxmox-stack/locals.tf",
        "new-file.tf",
        "new.tf",
    ]


def test_parse_changed_files_empty() -> None:
    assert runner.parse_changed_files("") == []
    assert runner.parse_changed_files("\n\n") == []


def test_overlap_files_intersects_preserving_changed_order() -> None:
    changed = ["b.tf", "a.tf", "unrelated.tf"]
    pr_files = ["a.tf", "b.tf"]
    assert runner.overlap_files(changed, pr_files) == ["b.tf", "a.tf"]


def test_overlap_files_no_overlap() -> None:
    assert runner.overlap_files(["x.tf"], ["a.tf", "b.tf"]) == []


# --- passed: the pass@1 definition ----------------------------------------------


def test_passed_requires_both_clean_check_and_real_overlap() -> None:
    assert runner.passed(0, 1) is True


def test_passed_is_false_on_touched_nothing_but_exited_clean() -> None:
    # The exact false-green this suite exists to catch: check_rc == 0 (a
    # `check: none` task, or a check that happens to pass on an untouched
    # tree) with zero files overlapping the real PR must NOT score a pass.
    assert runner.passed(0, 0) is False


def test_passed_is_false_on_failing_check_even_with_overlap() -> None:
    assert runner.passed(1, 3) is False


def test_passed_is_false_on_unrecognized_check() -> None:
    assert runner.passed(2, 1) is False


# --- check_steps -----------------------------------------------------------------


def test_check_steps_none_is_a_no_op_pass() -> None:
    assert runner.check_steps("none") == []


def test_check_steps_known_checks() -> None:
    assert runner.check_steps("markdownlint") == [["markdownlint-cli2", "**/*.md"]]
    assert runner.check_steps("tofu-validate") == [
        ["tofu", "init", "-backend=false"],
        ["tofu", "validate"],
    ]
    assert runner.check_steps("ansible-lint") == [["ansible-lint", "--offline"]]
    assert runner.check_steps("nix-eval") == [["nix", "flake", "check"]]
    assert runner.check_steps("json-valid") == [["jq", ".", "deployment.json.example"]]


def test_check_steps_bats_prefix_carries_the_path() -> None:
    assert runner.check_steps("bats:tests/shell/test_foo.bats") == [
        ["nix", "shell", "nixpkgs#bats", "-c", "bats", "tests/shell/test_foo.bats"]
    ]


def test_check_steps_unknown_returns_none() -> None:
    assert runner.check_steps("shell-tests") is None
    assert runner.check_steps("") is None


# --- rate-limit / event parsing / token + ttft aggregation ----------------------


def test_is_rate_limited() -> None:
    assert runner.is_rate_limited('{"type":"error","statusCode":429}') is True
    assert runner.is_rate_limited('{"type":"text","part":{}}') is False


def test_parse_events_skips_malformed_lines() -> None:
    raw = '{"type":"text"}\nnot json\n{"type":"step_finish"}\n\n'
    events = runner.parse_events(raw)
    assert events == [{"type": "text"}, {"type": "step_finish"}]


def test_aggregate_tokens_empty() -> None:
    assert runner.aggregate_tokens([]) == {"input": None, "output": None, "cache_read": None, "steps": 0}


def test_aggregate_tokens_sums_step_finish_events() -> None:
    events = [
        {"type": "step_finish", "part": {"tokens": {"input": 100, "output": 10, "cache": {"read": 500}}}},
        {"type": "step_finish", "part": {"tokens": {"input": 50, "output": 5, "cache": {"read": 200}}}},
        {"type": "text", "part": {}},
    ]
    assert runner.aggregate_tokens(events) == {"input": 150, "output": 15, "cache_read": 700, "steps": 2}


def test_first_text_start_ms_returns_first_match() -> None:
    events = [
        {"type": "step_finish"},
        {"type": "text", "part": {"time": {"start": 1234567.0}}},
        {"type": "text", "part": {"time": {"start": 9999999.0}}},
    ]
    assert runner.first_text_start_ms(events) == 1234567.0


def test_first_text_start_ms_none_when_absent() -> None:
    assert runner.first_text_start_ms([{"type": "step_finish"}]) is None


def test_ttft_seconds() -> None:
    # first_text_start_ms is epoch-milliseconds; request_start is epoch-seconds.
    assert runner.ttft_seconds(1237000.0, 1000.0) == 237.0
    assert runner.ttft_seconds(None, 1000.0) is None


# --- serialization round trip for the config the runner reads ------------------


def test_bundled_tasks_json_is_jsonl_of_12_tasks() -> None:
    path = Path(__file__).resolve().parents[1] / "configs" / "coding-replay" / "tasks.json"
    # A single JSON array, not JSON Lines: the repo's check-json pre-commit hook
    # validates every .json file as one document, and JSONL under a .json name
    # fails it. Renaming to .jsonl would have made the check stop applying
    # instead of pass.
    tasks = json.loads(path.read_text())
    assert len(tasks) == 12
    for task in tasks:
        assert {"repo", "pr", "base", "title", "files", "check"} <= task.keys()
        assert runner.check_steps(task["check"]) is not None


# --- timeout stdout normalisation ---------------------------------------------


def test_decode_timeout_stdout_decodes_bytes() -> None:
    # subprocess.TimeoutExpired.stdout carries RAW BYTES even when the call set
    # text=True — the decoding wrapper never runs on the timeout path. A capped
    # run is the common outcome for a slow local model, so this is the hot path,
    # not an edge case.
    assert runner.decode_timeout_stdout(b'{"type":"text"}\n') == '{"type":"text"}\n'


def test_decode_timeout_stdout_passes_str_through() -> None:
    assert runner.decode_timeout_stdout('{"type":"text"}') == '{"type":"text"}'


def test_decode_timeout_stdout_handles_none() -> None:
    assert runner.decode_timeout_stdout(None) == ""


def test_decode_timeout_stdout_survives_invalid_utf8() -> None:
    # A run killed mid-write can leave a partial multi-byte sequence; losing the
    # whole capped task to a UnicodeDecodeError would be worse than one mojibake
    # character in one event line.
    assert runner.decode_timeout_stdout(b"ok\xff") == "ok�"


def test_timed_out_events_still_parse_after_decoding() -> None:
    # End to end for the bug: bytes off a timeout, through the decoder, into the
    # event parser that scoring depends on.
    raw = b'{"type":"text","part":{"time":{"start":1000}}}\n{"type":"step_finish"}\n'
    events = runner.parse_events(runner.decode_timeout_stdout(raw))
    assert len(events) == 2
    assert runner.first_text_start_ms(events) == 1000
