#!/usr/bin/env python3
"""Backfill tokens-per-second columns into historical parquet files.

Walks every parquet file in the HuggingFace ``JacobPEvans/mlx-benchmarks``
dataset, locates the matching local ``samples_*.jsonl`` files (by ``git_sha``
+ ``model`` + ``suite`` + result name + timestamp slug), re-tokenizes prompts
and responses, computes aggregate tok/s per row, and writes a new parquet
revision with the new columns populated.

Defaults are dry-run + read-only. Use ``--commit`` to upload the rewritten
dataset revision. The previous HF revision is preserved as the rollback
target (HF dataset history is immutable per revision).

Examples
--------
Inspect what would be rewritten (no network upload, prints summary)::

    .venv/bin/python scripts/backfill_tokens_per_sec.py \\
        --samples-root run-output

Apply for real (requires HF_TOKEN with write access to the dataset)::

    HF_TOKEN=hf_xxx .venv/bin/python scripts/backfill_tokens_per_sec.py \\
        --samples-root run-output \\
        --commit
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download, list_repo_files
from huggingface_hub.errors import HfHubHTTPError

from mlx_benchmarks.converters.lm_eval import (
    _default_tokenizer_loader,
    _sum_tokens,
)

log = logging.getLogger("backfill_tok_per_sec")

DEFAULT_REPO_ID = "JacobPEvans/mlx-benchmarks"
DEFAULT_REPO_TYPE = "dataset"


@dataclass(slots=True)
class BackfillStats:
    rows_total: int = 0
    rows_with_existing_tokps: int = 0
    rows_updated: int = 0
    rows_skipped_no_samples: int = 0
    rows_skipped_no_duration: int = 0
    rows_skipped_no_tokenizer: int = 0
    files_total: int = 0
    files_changed: int = 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        format="%(levelname)s %(name)s | %(message)s",
        level=getattr(logging, args.log_level),
    )

    api = HfApi(token=args.token)
    parquet_paths = list(_iter_dataset_parquet_paths(args.repo_id))
    log.info("found %d parquet files in %s", len(parquet_paths), args.repo_id)

    stats = BackfillStats()
    operations: list[CommitOperationAdd] = []

    for path in parquet_paths:
        stats.files_total += 1
        new_bytes = _process_one_parquet(api, args, path, stats)
        if new_bytes is None:
            log.debug("no change for %s", path)
            continue
        stats.files_changed += 1
        operations.append(CommitOperationAdd(path_in_repo=path, path_or_fileobj=new_bytes))

    log.info(
        "summary: files_total=%d files_changed=%d rows_total=%d rows_updated=%d "
        "rows_skipped_no_samples=%d rows_skipped_no_duration=%d "
        "rows_skipped_no_tokenizer=%d rows_with_existing_tokps=%d",
        stats.files_total,
        stats.files_changed,
        stats.rows_total,
        stats.rows_updated,
        stats.rows_skipped_no_samples,
        stats.rows_skipped_no_duration,
        stats.rows_skipped_no_tokenizer,
        stats.rows_with_existing_tokps,
    )

    if not args.commit:
        log.info("dry-run: pass --commit to upload the %d changed file(s)", len(operations))
        return 0
    if not operations:
        log.info("nothing to upload — exiting without commit")
        return 0
    if not args.token:
        log.error("--commit requires HF_TOKEN (env or --token)")
        return 2
    try:
        api.create_commit(
            repo_id=args.repo_id,
            repo_type=DEFAULT_REPO_TYPE,
            operations=operations,
            commit_message="feat(backfill): populate tokens-per-second metrics on historical runs",
        )
    except HfHubHTTPError as exc:
        log.error("upload failed: %s", exc)
        return 3
    log.info("uploaded %d rewritten parquet file(s) to %s", len(operations), args.repo_id)
    return 0


def _process_one_parquet(
    api: HfApi,
    args: argparse.Namespace,
    repo_path: str,
    stats: BackfillStats,
) -> bytes | None:
    """Download, rewrite, and return new parquet bytes (or None if unchanged)."""
    local_file = hf_hub_download(
        repo_id=args.repo_id,
        repo_type=DEFAULT_REPO_TYPE,
        filename=repo_path,
        token=api.token,
    )
    table = pq.read_table(local_file)  # type: ignore[no-untyped-call]
    rows: list[dict[str, Any]] = table.to_pylist()
    changed = False
    tokenizer_cache: dict[str, Any] = {}

    for row in rows:
        stats.rows_total += 1
        if row.get("decode_tokens_per_second") is not None:
            stats.rows_with_existing_tokps += 1
            continue
        duration = row.get("duration_seconds")
        if not isinstance(duration, int | float) or duration <= 0:
            stats.rows_skipped_no_duration += 1
            continue
        samples_path = _locate_samples_file(Path(args.samples_root), row)
        if samples_path is None:
            stats.rows_skipped_no_samples += 1
            continue
        model = row.get("model")
        if not isinstance(model, str):
            stats.rows_skipped_no_tokenizer += 1
            continue
        tokenizer = tokenizer_cache.get(model)
        if tokenizer is None:
            tokenizer = _default_tokenizer_loader(model)
            tokenizer_cache[model] = tokenizer
        if tokenizer is None:
            stats.rows_skipped_no_tokenizer += 1
            continue

        prompt_total, response_total, sample_count = _sum_tokens(samples_path, tokenizer)
        if sample_count == 0:
            stats.rows_skipped_no_samples += 1
            continue
        row["prompt_tokens_per_second"] = prompt_total / duration
        row["decode_tokens_per_second"] = response_total / duration
        row["total_tokens_per_second"] = (prompt_total + response_total) / duration
        stats.rows_updated += 1
        changed = True

    if not changed:
        return None
    new_table = pa.Table.from_pylist(rows)
    buf = io.BytesIO()
    pq.write_table(new_table, buf)  # type: ignore[no-untyped-call]
    return buf.getvalue()


def _locate_samples_file(samples_root: Path, row: dict[str, Any]) -> Path | None:
    """Reconstruct the ``samples_<task>_<ts>.jsonl`` path for a parquet row.

    Two-step search:

    1. Build the run-output directory the publisher would have used by
       walking the conventional layout
       ``<root>/<run-tag>/<task-name>/<model-slug>/<model-id>/``. We don't
       know the exact ``<run-tag>``, so walk subdirectories and look for any
       ``samples_<name>_*.jsonl`` whose timestamp slug matches the row's
       ``timestamp`` field.

    2. Fall back to any ``samples_<name>_*.jsonl`` matching just the task
       name. Returns None if nothing is found.
    """
    task_name = row.get("name")
    timestamp = row.get("timestamp")
    if not isinstance(task_name, str) or not samples_root.is_dir():
        return None
    ts_slug = None
    if isinstance(timestamp, str):
        ts_slug = timestamp.replace(":", "-").rstrip("Z")

    matches = list(samples_root.rglob(f"samples_{task_name}_*.jsonl"))
    if not matches:
        return None
    if ts_slug is not None:
        for candidate in matches:
            if ts_slug in candidate.name:
                return candidate
    matches.sort(key=lambda p: p.stat().st_mtime)
    return matches[-1]


def _iter_dataset_parquet_paths(repo_id: str) -> Iterator[str]:
    for entry in list_repo_files(repo_id=repo_id, repo_type=DEFAULT_REPO_TYPE):
        if entry.startswith("data/") and entry.endswith(".parquet"):
            yield entry


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="backfill_tokens_per_sec",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help="HuggingFace dataset repo to backfill (default: %(default)s)",
    )
    parser.add_argument(
        "--samples-root",
        type=Path,
        default=Path("run-output"),
        help="Local directory tree containing original samples_*.jsonl files (default: %(default)s)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Upload the rewritten parquet files. Without this flag the script is a pure dry-run.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("HF_TOKEN"),
        help="HuggingFace token (default: HF_TOKEN env var)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
