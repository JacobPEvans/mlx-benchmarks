"""Serialize envelope -> Parquet and upload to the HuggingFace dataset repo."""

from __future__ import annotations

import io
import logging
import os
import re
import subprocess
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import CommitOperationAdd, HfApi

from mlx_benchmarks.envelope import Envelope, validate_envelope

log = logging.getLogger(__name__)

DEFAULT_REPO_ID = "JacobPEvans/mlx-benchmarks"
DEFAULT_REPO_TYPE = "dataset"


def slugify(model: str) -> str:
    """Filesystem-safe slug of a model identifier.

    ``mlx-community/Qwen3.5-9B-MLX-4bit`` -> ``mlx-community-qwen3-5-9b-mlx-4bit``.
    """
    return re.sub(r"[^a-zA-Z0-9-]", "-", model).lower().strip("-")


def current_git_sha(fallback: str = "unknown") -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, timeout=3).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return fallback


def envelope_to_rows(envelope: Envelope) -> list[dict[str, Any]]:
    """Explode ``envelope['results']`` into one flat row per measurement."""
    system = dict(envelope.get("system") or {})
    base: dict[str, Any] = {
        "schema_version": envelope.get("schema_version"),
        "timestamp": envelope.get("timestamp"),
        "git_sha": envelope.get("git_sha"),
        "trigger": envelope.get("trigger"),
        "suite": envelope.get("suite"),
        "model": envelope.get("model"),
        "os": system.get("os"),
        "chip": system.get("chip"),
        "memory_gb": system.get("memory_gb"),
    }
    if "model_revision" in envelope:
        base["model_revision"] = envelope["model_revision"]
    if "quantization" in envelope:
        base["quantization"] = envelope["quantization"]
    if "seed" in envelope:
        base["seed"] = envelope["seed"]

    rows: list[dict[str, Any]] = []
    for r in envelope.get("results", []):
        row: dict[str, Any] = {
            **base,
            "name": r.get("name"),
            "metric": r.get("metric"),
            "value": r.get("value"),
            "unit": r.get("unit"),
        }
        if "duration_seconds" in r:
            row["duration_seconds"] = r["duration_seconds"]
        for k, v in (r.get("tags") or {}).items():
            row[f"tag_{k}"] = v
        rows.append(row)
    return rows


def rows_to_parquet(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise ValueError("No result rows to serialize — envelope has empty results[]")
    table = pa.Table.from_pylist(rows)
    buf = io.BytesIO()
    pq.write_table(table, buf)  # type: ignore[no-untyped-call]
    return buf.getvalue()


def target_path(envelope: Envelope) -> str:
    """Deterministic HF-dataset path for this envelope.

    Includes timestamp + git_sha + suite + model_slug so historical shards
    are never overwritten, matching the policy documented in CLAUDE.md.
    """
    timestamp = envelope["timestamp"]
    ts_slug = timestamp.replace(":", "-").rstrip("Z")
    model_slug = slugify(envelope["model"])[:50]
    return f"data/run-{ts_slug}-{envelope['git_sha']}-{envelope['suite']}-{model_slug}.parquet"


def publish(
    envelope: Envelope,
    *,
    repo_id: str = DEFAULT_REPO_ID,
    repo_type: str = DEFAULT_REPO_TYPE,
    dry_run: bool = False,
    token: str | None = None,
    validate: bool = True,
) -> str:
    """Validate, serialize and optionally upload ``envelope`` to the HF dataset.

    Returns the target path. When ``dry_run`` is True no network I/O happens;
    otherwise ``HF_TOKEN`` (or an explicit ``token`` arg) is required.
    """
    if validate:
        validate_envelope(envelope)

    rows = envelope_to_rows(envelope)
    parquet_bytes = rows_to_parquet(rows)
    path = target_path(envelope)

    if dry_run:
        log.info("dry-run: would publish %d bytes to %s in %s", len(parquet_bytes), path, repo_id)
        return path

    effective_token = token or os.environ.get("HF_TOKEN")
    if not effective_token:
        raise RuntimeError("HF_TOKEN not set — export HF_TOKEN before publishing, or pass token=...")

    api = HfApi(token=effective_token)
    api.create_commit(
        repo_id=repo_id,
        repo_type=repo_type,
        operations=[CommitOperationAdd(path_in_repo=path, path_or_fileobj=parquet_bytes)],
        commit_message=f"feat: add {envelope['suite']} run for {envelope['model']}",
    )
    log.info("published %d-byte parquet to %s", len(parquet_bytes), path)
    return path
