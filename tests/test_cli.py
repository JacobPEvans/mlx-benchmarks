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
