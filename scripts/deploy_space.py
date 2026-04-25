#!/usr/bin/env python3
"""Push ``space/`` contents to the HuggingFace Space as a single atomic commit.

Called by ``.github/workflows/deploy-space.yml`` on ``main`` pushes that
touch ``space/``. Expects these environment variables:

    HF_TOKEN        — HF token with write scope on SPACE_REPO_ID
    SPACE_REPO_ID   — e.g. ``JacobPEvans/mlx-benchmarks-viewer``
    GITHUB_SHA      — commit SHA used in the HF commit message

Skips ``.venv``, ``__pycache__``, ``.pytest_cache`` artifacts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi

SKIP_PARTS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "tests"}


def main() -> int:
    try:
        token = os.environ["HF_TOKEN"]
        repo_id = os.environ["SPACE_REPO_ID"]
    except KeyError as exc:
        print(f"missing required env var: {exc}", file=sys.stderr)
        return 2

    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    space_dir = Path(__file__).resolve().parents[1] / "space"
    if not space_dir.is_dir():
        print(f"space directory not found: {space_dir}", file=sys.stderr)
        return 3

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="gradio", exist_ok=True)

    operations: list[CommitOperationAdd] = []
    for path in sorted(space_dir.rglob("*")):
        if path.is_dir():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        rel = path.relative_to(space_dir).as_posix()
        operations.append(CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(path)))

    if not operations:
        print("no files to push from space/", file=sys.stderr)
        return 4

    api.create_commit(
        repo_id=repo_id,
        repo_type="space",
        operations=operations,
        commit_message=f"sync: {sha} from JacobPEvans/mlx-benchmarks",
    )
    print(f"pushed {len(operations)} files to {repo_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
