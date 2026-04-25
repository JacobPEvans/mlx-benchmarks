"""Cover publish.py without touching the network."""

from __future__ import annotations

import pytest

from mlx_benchmarks.envelope import EnvelopeValidationError
from mlx_benchmarks.publish import (
    PublishError,
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


def test_target_path_includes_payload_hash(valid_envelope: dict) -> None:
    bare = target_path(valid_envelope)
    stamped_a = target_path(valid_envelope, payload=b"alpha")
    stamped_b = target_path(valid_envelope, payload=b"beta")
    # Same prefix, distinct suffixes: re-runs producing different bytes in the
    # same second MUST NOT collide.
    assert stamped_a != stamped_b
    assert stamped_a != bare
    assert stamped_b != bare
    assert stamped_a.startswith(bare.removesuffix(".parquet"))


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


def test_rows_to_parquet_rejects_empty() -> None:
    with pytest.raises(PublishError, match="No result rows"):
        rows_to_parquet([])


def test_publish_dry_run_returns_path(valid_envelope: dict) -> None:
    path = publish(valid_envelope, dry_run=True)
    # The returned path carries a content-addressed suffix when payload is real.
    assert path.startswith(target_path(valid_envelope).removesuffix(".parquet"))


def test_publish_refuses_invalid_envelope(invalid_envelope: dict) -> None:
    with pytest.raises(EnvelopeValidationError):
        publish(invalid_envelope, dry_run=True)


def test_publish_skipping_validation_still_rejects_empty(invalid_envelope: dict) -> None:
    # --no-validate is the escape hatch; rows_to_parquet still raises PublishError
    # (not plain ValueError) so the CLI can catch it via a single exception type.
    with pytest.raises(PublishError, match="No result rows"):
        publish(invalid_envelope, dry_run=True, validate=False)
