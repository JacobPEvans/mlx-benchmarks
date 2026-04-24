"""Cover publish.py without touching the network."""

from __future__ import annotations

import pytest

from mlx_benchmarks.envelope import EnvelopeValidationError
from mlx_benchmarks.publish import (
    envelope_to_rows,
    publish,
    rows_to_parquet,
    slugify,
    target_path,
)


def test_slugify_strips_special_chars() -> None:
    assert slugify("mlx-community/Qwen3.5-9B-MLX-4bit") == "mlx-community-qwen3-5-9b-mlx-4bit"
    assert slugify("openrouter/openai/gpt-5-mini") == "openrouter-openai-gpt-5-mini"


def test_target_path_format(valid_envelope: dict) -> None:
    path = target_path(valid_envelope)
    assert path.startswith("data/run-")
    assert path.endswith(".parquet")
    # No colons (filesystem-hostile on Windows/CI, and HF commit paths)
    assert ":" not in path
    # Contains git_sha and suite
    assert valid_envelope["git_sha"] in path
    assert valid_envelope["suite"] in path


def test_envelope_to_rows_explodes_results(valid_envelope: dict) -> None:
    rows = envelope_to_rows(valid_envelope)
    assert len(rows) == len(valid_envelope["results"])
    row = rows[0]
    # Base envelope fields propagated
    assert row["suite"] == "reasoning"
    assert row["model"] == "mlx-community/Qwen3.5-9B-MLX-4bit"
    # Tags exploded with tag_ prefix
    assert row["tag_lm_eval_key"] == "exact_match,flexible-extract"
    # Duration promoted to top-level column
    assert row["duration_seconds"] == 123.4


def test_rows_to_parquet_roundtrip(valid_envelope: dict) -> None:
    import io

    import pyarrow.parquet as pq

    rows = envelope_to_rows(valid_envelope)
    parquet_bytes = rows_to_parquet(rows)
    assert parquet_bytes[:4] == b"PAR1"  # parquet magic
    table = pq.read_table(io.BytesIO(parquet_bytes))
    assert table.num_rows == len(rows)


def test_publish_dry_run_returns_path(valid_envelope: dict) -> None:
    path = publish(valid_envelope, dry_run=True)
    assert path == target_path(valid_envelope)


def test_publish_refuses_invalid_envelope(invalid_envelope: dict) -> None:
    with pytest.raises(EnvelopeValidationError):
        publish(invalid_envelope, dry_run=True)


def test_publish_can_skip_validation(invalid_envelope: dict) -> None:
    # --no-validate is escape hatch; still rejects empty results downstream in rows_to_parquet.
    with pytest.raises(ValueError, match="No result rows"):
        publish(invalid_envelope, dry_run=True, validate=False)
