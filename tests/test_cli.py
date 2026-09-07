"""CLI smoke tests — argparse + dispatch, no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlx_benchmarks.cli import main


def _write_sample(tmp_path: Path, sample: dict) -> Path:
    path = tmp_path / "results.json"
    path.write_text(json.dumps(sample))
    return path


def test_cli_dry_run_happy_path(tmp_path: Path, lm_eval_sample: dict, capsys: pytest.CaptureFixture) -> None:
    results_path = _write_sample(tmp_path, lm_eval_sample)
    exit_code = main(
        [
            str(results_path),
            "--kind",
            "lm-eval",
            "--suite",
            "reasoning",
            "--git-sha",
            "deadbeef",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "dry-run" in captured.err.lower() or "planned" in captured.err.lower()


def test_cli_vllm_dry_run(tmp_path: Path, vllm_sample: dict, capsys: pytest.CaptureFixture) -> None:
    results_path = _write_sample(tmp_path, vllm_sample)
    exit_code = main(
        [
            str(results_path),
            "--kind",
            "vllm",
            "--suite",
            "throughput",
            "--model",
            "mlx-community/gpt-oss-120b-MXFP4-Q8",
            "--git-sha",
            "deadbeef",
            "--tag",
            "host=mac-studio",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "dry-run" in captured.err.lower() or "planned" in captured.err.lower()


def test_cli_agentic_dry_run(tmp_path: Path, agentic_sample: dict, capsys: pytest.CaptureFixture) -> None:
    results_path = _write_sample(tmp_path, agentic_sample)
    exit_code = main(
        [
            str(results_path),
            "--kind",
            "agentic",
            "--suite",
            "tool-calling",
            "--git-sha",
            "deadbeef",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "dry-run" in captured.err.lower() or "planned" in captured.err.lower()


def test_cli_promptstack_dry_run(
    tmp_path: Path, promptstack_sample: dict, capsys: pytest.CaptureFixture
) -> None:
    results_path = _write_sample(tmp_path, promptstack_sample)
    exit_code = main(
        [
            str(results_path),
            "--kind",
            "promptstack",
            "--suite",
            "promptstack",
            "--git-sha",
            "deadbeef",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "dry-run" in captured.err.lower() or "planned" in captured.err.lower()


def test_cli_hostname_override(tmp_path: Path, lm_eval_sample: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    results_path = _write_sample(tmp_path, lm_eval_sample)
    captured: dict[str, object] = {}

    def fake_publish(envelope: dict, **_: object) -> str:
        captured["envelope"] = envelope
        return "data/x.parquet"

    monkeypatch.setattr("mlx_benchmarks.cli.publish", fake_publish)
    exit_code = main(
        [
            str(results_path),
            "--kind",
            "lm-eval",
            "--suite",
            "reasoning",
            "--git-sha",
            "deadbeef",
            "--hostname",
            "mac-studio",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    envelope = captured["envelope"]
    assert isinstance(envelope, dict)
    assert envelope["system"]["hostname"] == "mac-studio"


def test_cli_rejects_invalid_tag(tmp_path: Path, lm_eval_sample: dict) -> None:
    results_path = _write_sample(tmp_path, lm_eval_sample)
    with pytest.raises(SystemExit, match="invalid --tag"):
        main(
            [
                str(results_path),
                "--kind",
                "lm-eval",
                "--suite",
                "reasoning",
                "--git-sha",
                "deadbeef",
                "--tag",
                "no-equals-sign",
                "--dry-run",
            ]
        )


def test_extract_model_reads_model_id_from_a_json_lines_run() -> None:
    """A coding-replay row must publish under the served model, not "unknown".

    The extractor reads ``model_id`` from a list-shaped run. The coding-replay
    runner's ``model`` field is the agent-CLI reference and carries a provider
    prefix, so it is not the right key: two arms served behind different
    provider names would publish as different models. A row missing
    ``model_id`` yields "unknown" *silently* — the extractor falls back rather
    than raising, and the documented publish command passes no ``--model``.
    """
    from mlx_benchmarks.cli import _extract_model

    row = {
        "model": "kimi/mlx-community/Kimi-Linear-48B-A3B-Instruct-6bit",
        "model_id": "mlx-community/Kimi-Linear-48B-A3B-Instruct-6bit",
        "task": "repo-1",
    }
    assert _extract_model([row]) == "mlx-community/Kimi-Linear-48B-A3B-Instruct-6bit"

    # Anti-vacuity: the assertion above must be carried by model_id, not by the
    # prefixed `model` field happening to be picked up.
    assert _extract_model([{k: v for k, v in row.items() if k != "model_id"}]) == "unknown"


def test_extract_model_still_reads_model_id_for_other_kinds() -> None:
    """bench-serve records already carry model_id; that path must not change."""
    from mlx_benchmarks.cli import _extract_model

    assert _extract_model([{"model_id": "mlx-community/Qwen3.6-35B-A3B-4bit"}]) == (
        "mlx-community/Qwen3.6-35B-A3B-4bit"
    )


def test_cli_rejects_malformed_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{this is not json")
    exit_code = main(
        [
            str(bad),
            "--kind",
            "lm-eval",
            "--suite",
            "reasoning",
            "--git-sha",
            "deadbeef",
            "--dry-run",
        ]
    )
    assert exit_code == 2
