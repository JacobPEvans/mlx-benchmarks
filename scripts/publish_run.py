#!/usr/bin/env python3
"""Convert an lm-eval results.json to envelope v1 and publish to HF dataset.

Usage:
    .venv/bin/python scripts/publish_run.py <results.json> \
        --suite reasoning \
        --model mlx-community/Qwen3.5-35B-A3B-4bit \
        [--git-sha b11881b] \
        [--dry-run]

The script reads the lm-eval output, maps it to envelope v1 (schema.json),
serializes to Parquet, and appends to JacobPEvans/mlx-benchmarks via a unique
filename commit so historical shards are never overwritten.

Requires $HF_TOKEN with write scope on the dataset namespace.
"""

import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi, CommitOperationAdd


REPO_ID = "JacobPEvans/mlx-benchmarks"
REPO_TYPE = "dataset"

SYSTEM = {
    "os": "macOS 26.4.1",
    "chip": "Apple M4 Max",
    "memory_gb": 128,
}

# Metric display names from lm-eval key patterns
_METRIC_MAP = {
    "exact_match,flexible-extract": "exact_match_flexible",
    "exact_match,strict-match": "exact_match_strict",
    "acc,none": "accuracy",
    "acc_norm,none": "accuracy_normalized",
    "pass@1,none": "pass_at_1",
}


def slugify(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]", "-", model).lower().strip("-")


def current_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def build_envelope(data: dict, suite: str, model: str, sha: str) -> dict:
    ts_unix = data.get("date", datetime.datetime.now(datetime.UTC).timestamp())
    ts = datetime.datetime.fromtimestamp(ts_unix, datetime.UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    results_entries = []
    raw_results = data.get("results", {})
    for task_name, task_metrics in raw_results.items():
        for metric_key, metric_val in task_metrics.items():
            # Skip stderr and alias fields
            if "stderr" in metric_key or metric_key == "alias":
                continue
            if not isinstance(metric_val, (int, float)):
                continue
            display_metric = _METRIC_MAP.get(metric_key, metric_key.replace(",", "_"))
            results_entries.append(
                {
                    "name": task_name,
                    "metric": display_metric,
                    "value": float(metric_val),
                    "unit": "ratio",
                    "tags": {
                        "lm_eval_key": metric_key,
                        "total_eval_time_s": str(
                            data.get("total_evaluation_time_seconds", "")
                        ),
                        "n_limit": str(data.get("config", {}).get("limit", "")),
                        "max_gen_toks": str(
                            data.get("config", {})
                            .get("gen_kwargs", {})
                            .get("max_gen_toks", "")
                        ),
                    },
                }
            )

    return {
        "schema_version": "1",
        "timestamp": ts,
        "git_sha": sha,
        "trigger": "local",
        "suite": suite,
        "model": model,
        "system": SYSTEM,
        "results": results_entries,
        "errors": [],
    }


def envelope_to_rows(envelope: dict) -> list[dict]:
    """Explode envelope results[] into flat scalar rows for Parquet storage."""
    base = {
        "schema_version": envelope["schema_version"],
        "timestamp": envelope["timestamp"],
        "git_sha": envelope["git_sha"],
        "trigger": envelope["trigger"],
        "suite": envelope["suite"],
        "model": envelope["model"],
        "os": envelope["system"]["os"],
        "chip": envelope["system"]["chip"],
        "memory_gb": envelope["system"]["memory_gb"],
    }
    rows = []
    for r in envelope["results"]:
        row = {
            **base,
            "name": r["name"],
            "metric": r["metric"],
            "value": r["value"],
            "unit": r["unit"],
        }
        for k, v in (r.get("tags") or {}).items():
            row[f"tag_{k}"] = v
        rows.append(row)
    return rows


def rows_to_parquet(rows: list[dict]) -> bytes:
    if not rows:
        raise ValueError("No result rows to serialize")
    table = pa.Table.from_pylist(rows)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


def publish(parquet_bytes: bytes, envelope: dict, dry_run: bool = False) -> str:
    ts_slug = envelope["timestamp"].replace(":", "-").rstrip("Z")
    model_slug = slugify(envelope["model"])[:50]
    path = (
        f"data/run-{ts_slug}-{envelope['git_sha']}"
        f"-{envelope['suite']}-{model_slug}.parquet"
    )

    if dry_run:
        print(f"[dry-run] would publish {len(parquet_bytes)} bytes to {path}")
        return path

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN not set — export HF_TOKEN before publishing")

    api = HfApi(token=token)
    api.create_commit(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        operations=[
            CommitOperationAdd(
                path_in_repo=path,
                path_or_fileobj=parquet_bytes,
            )
        ],
        commit_message=f"feat: add {envelope['suite']} run for {envelope['model']}",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_json", help="Path to lm-eval results.json")
    parser.add_argument("--suite", required=True, help="Suite name (e.g. reasoning)")
    parser.add_argument("--model", help="Model ID (defaults to model_name in JSON)")
    parser.add_argument(
        "--git-sha",
        help="Override git SHA recorded in the envelope (default: current HEAD)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan, no upload")
    args = parser.parse_args()

    with open(args.results_json) as f:
        data = json.load(f)

    model = (
        args.model
        or data.get("model_name")
        or data.get("config", {}).get("model_args", {}).get("model", "unknown")
    )
    sha = args.git_sha or current_git_sha()
    envelope = build_envelope(data, suite=args.suite, model=model, sha=sha)

    rows = envelope_to_rows(envelope)
    print(f"Built {len(rows)} result rows for {model}")
    for r in rows:
        print(f"  {r['name']} / {r['metric']} = {r['value']}")

    parquet_bytes = rows_to_parquet(rows)
    path = publish(parquet_bytes, envelope, dry_run=args.dry_run)
    print(f"Published → {path}")


if __name__ == "__main__":
    main()
