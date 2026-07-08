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
