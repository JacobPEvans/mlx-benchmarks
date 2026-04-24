"""``mlx-bench-publish`` command-line entry point.

Typical use::

    mlx-bench-publish run-output/mymodel/results_*.json \\
        --kind lm-eval --suite reasoning

``--dry-run`` prints the planned upload without touching the network.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import EnvelopeValidationError
from mlx_benchmarks.logging_config import configure_logging
from mlx_benchmarks.publish import PublishError, current_git_sha, publish
from mlx_benchmarks.system import detect_system

log = logging.getLogger("mlx_benchmarks.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mlx-bench-publish",
        description="Convert a raw benchmark result to envelope v1 and publish to the HF dataset.",
    )
    parser.add_argument(
        "results_json", type=Path, help="Path to the raw tool output (e.g. lm-eval results_*.json)"
    )
    parser.add_argument(
        "--kind",
        default="lm-eval",
        choices=["lm-eval"],
        help="Source format of results_json (only lm-eval is currently supported)",
    )
    parser.add_argument("--suite", required=True, help="Envelope suite (must be in schema enum)")
    parser.add_argument("--model", help="Override model ID (default: extract from results_json)")
    parser.add_argument("--git-sha", help="Override git SHA recorded in envelope (default: git rev-parse)")
    parser.add_argument(
        "--trigger",
        default="local",
        choices=["local", "schedule", "pr", "workflow_dispatch"],
        help="Envelope trigger field",
    )
    parser.add_argument("--pr-number", type=int, help="Pull request number when trigger=pr")
    parser.add_argument("--timestamp", help="Override envelope timestamp (ISO 8601 UTC, rarely needed)")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Attach a tag to every result (repeat flag for multiple)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate + plan only; do not upload")
    parser.add_argument("--no-validate", action="store_true", help="Skip schema validation (not recommended)")
    parser.add_argument("--log-format", default="text", choices=["text", "json"])
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "--repo-id", default=None, help="Override HF dataset repo (default: JacobPEvans/mlx-benchmarks)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(level=args.log_level, fmt=args.log_format)

    try:
        raw: dict[str, Any] = json.loads(args.results_json.read_text())
    except OSError as exc:
        log.error("cannot read %s: %s", args.results_json, exc)
        return 2
    except json.JSONDecodeError as exc:
        log.error("%s is not valid JSON: %s", args.results_json, exc)
        return 2

    model = args.model or _extract_model(raw)
    git_sha = args.git_sha or current_git_sha()
    extra_tags = dict(_parse_kv_pairs(args.tag))
    system = detect_system()

    ctx = ConverterContext(
        suite=args.suite,
        model=model,
        git_sha=git_sha,
        trigger=args.trigger,
        pr_number=args.pr_number,
        timestamp_override=args.timestamp,
        system=system,
        extra_tags=extra_tags,
    )

    converter = get_converter(args.kind)
    envelope = converter.build_envelope(raw, ctx)
    log.info(
        "built envelope with %d results for model=%s suite=%s",
        len(envelope.get("results", [])),
        model,
        args.suite,
    )

    try:
        publish_kwargs: dict[str, Any] = {
            "dry_run": args.dry_run,
            "validate": not args.no_validate,
        }
        if args.repo_id:
            publish_kwargs["repo_id"] = args.repo_id
        path = publish(envelope, **publish_kwargs)
    except EnvelopeValidationError as exc:
        log.error("%s", exc)
        return 3
    except PublishError as exc:
        log.error("publish failed: %s", exc)
        return 4

    log.info("%s -> %s", "planned" if args.dry_run else "published", path)
    return 0


def _extract_model(raw: dict[str, Any]) -> str:
    cfg = raw.get("config") or {}
    model_args = cfg.get("model_args") or {}
    for candidate in (raw.get("model_name"), model_args.get("model"), raw.get("model")):
        if isinstance(candidate, str) and candidate:
            return candidate
    return "unknown"


def _parse_kv_pairs(raw_pairs: list[str]) -> Iterator[tuple[str, str]]:
    for pair in raw_pairs:
        if "=" not in pair:
            raise SystemExit(f"invalid --tag {pair!r}; expected KEY=VALUE")
        key, _, value = pair.partition("=")
        if not key:
            raise SystemExit(f"invalid --tag {pair!r}; empty key")
        yield key, value


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
