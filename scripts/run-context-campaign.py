#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

VALID_STATUSES = frozenset(
    {"success", "failed", "capacity_gated", "unsupported", "aborted", "not_applicable"}
)


@dataclass(frozen=True)
class CampaignCell:
    campaign_id: str
    profile_id: str
    model: str
    configured_window: int
    target_tokens: int
    output_tokens: int
    prompt_tolerance_tokens: int
    repeats: int
    concurrency: int
    base_url: str
    environment_class: str

    @property
    def cell_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @property
    def status(self) -> str:
        return (
            "not_applicable"
            if self.target_tokens + self.output_tokens > self.configured_window
            else "success"
        )


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _positive_ints(values: object, field: str) -> list[int]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} must be a non-empty array")
    return [_positive_int(value, field) for value in values]


def _profile_id(profile: dict[str, Any]) -> str:
    explicit = profile.get("id")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit:
            raise ValueError("profile.id must be a non-empty string")
        return explicit
    model = profile.get("model")
    if not isinstance(model, str) or not model:
        raise ValueError("profile.model must be a non-empty string")
    return model.rsplit("/", 1)[-1]


def _profile_windows(profile: dict[str, Any], configured_windows: list[int]) -> list[int]:
    limit = _positive_int(profile.get("window_limit_tokens"), "profile.window_limit_tokens")
    return [window for window in configured_windows if window <= limit]


def load_cells(manifest: dict[str, Any]) -> list[CampaignCell]:
    campaign_id = manifest.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id:
        raise ValueError("campaign_id must be a non-empty string")
    defaults = manifest.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be an object")
    targets = _positive_ints(defaults.get("targets"), "defaults.targets")
    configured_windows = _positive_ints(defaults.get("configured_windows"), "defaults.configured_windows")
    output_tokens = _positive_int(defaults.get("output_tokens", 512), "defaults.output_tokens")
    prompt_tolerance_tokens = _positive_int(
        defaults.get("prompt_tolerance_tokens", 64), "defaults.prompt_tolerance_tokens"
    )
    repeats = _positive_int(defaults.get("repeats", 4), "defaults.repeats")
    concurrency = _positive_int(defaults.get("concurrency", 1), "defaults.concurrency")
    base_url = manifest.get("base_url", "http://127.0.0.1:11434/v1")
    if not isinstance(base_url, str) or not base_url:
        raise ValueError("base_url must be a non-empty string")
    environment_class = manifest.get("environment_class", "isolated")
    if environment_class not in {"isolated", "under-load"}:
        raise ValueError("environment_class must be isolated or under-load")
    profiles = manifest.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("profiles must be a non-empty array")

    cells: list[CampaignCell] = []
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("each profile must be an object")
        profile_id, model = _profile_id(profile), profile.get("model")
        if not isinstance(model, str) or not model:
            raise ValueError("profile.model must be a non-empty string")
        if profile.get("enabled", True) is not True:
            continue
        windows = _profile_windows(profile, configured_windows)
        for window in windows:
            for target in targets:
                cells.append(
                    CampaignCell(
                        campaign_id=campaign_id,
                        profile_id=profile_id,
                        model=model,
                        configured_window=window,
                        target_tokens=target,
                        output_tokens=output_tokens,
                        prompt_tolerance_tokens=prompt_tolerance_tokens,
                        repeats=repeats,
                        concurrency=concurrency,
                        base_url=base_url,
                        environment_class=environment_class,
                    )
                )
    return cells


def served_models(base_url: str) -> set[str]:
    url = base_url.rstrip("/") + "/models"
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read())
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read live model inventory from {url}: {exc}") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise RuntimeError(f"live model inventory from {url} has no data array")
    return {item["id"] for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)}


def cell_dir(output_root: Path, cell: CampaignCell) -> Path:
    return output_root / cell.campaign_id / cell.profile_id / cell.cell_id


def probe_command(cell: CampaignCell, raw_output: Path) -> list[str]:
    return [
        "uv",
        "run",
        "harness/throughput/run.py",
        "--base-url",
        cell.base_url,
        "--model",
        cell.model,
        "--context-tokens",
        str(cell.target_tokens),
        "--expected-prompt-tokens",
        str(cell.target_tokens),
        "--prompt-tolerance-tokens",
        str(cell.prompt_tolerance_tokens),
        "--window-limit-tokens",
        str(cell.configured_window),
        "--campaign-id",
        cell.campaign_id,
        "--cell-id",
        cell.cell_id,
        "--profile",
        cell.profile_id,
        "--max-tokens",
        str(cell.output_tokens),
        "--repeats",
        str(cell.repeats),
        "--concurrency",
        str(cell.concurrency),
        "--output",
        str(raw_output),
    ]


def publisher_command(cell: CampaignCell, raw_output: Path) -> list[str]:
    return [
        "uv",
        "run",
        "mlx-bench-publish",
        str(raw_output),
        "--kind",
        "throughput-probe",
        "--suite",
        "throughput",
        "--model",
        cell.model,
        "--env-class",
        cell.environment_class,
        "--concurrency",
        str(cell.concurrency),
        "--tag",
        f"campaign_id={cell.campaign_id}",
        "--tag",
        f"cell_id={cell.cell_id}",
        "--tag",
        f"configured_window_tokens={cell.configured_window}",
        "--tag",
        f"requested_prompt_tokens={cell.target_tokens}",
        "--tag",
        f"reserved_output_tokens={cell.output_tokens}",
        "--dry-run",
    ]


def write_status(path: Path, cell: CampaignCell, status: str, **extra: object) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid cell status: {status}")
    path.write_text(json.dumps({"status": status, "cell": asdict(cell), **extra}, indent=2) + "\n")


def run_cell(
    repo_root: Path,
    output_root: Path,
    cell: CampaignCell,
    dry_run: bool,
    live_models: set[str] | None,
) -> str:
    directory = cell_dir(output_root, cell)
    raw_output = directory / "throughput.json"
    if cell.status == "not_applicable":
        if not dry_run:
            directory.mkdir(parents=True, exist_ok=True)
            write_status(
                directory / "cell.json",
                cell,
                cell.status,
                reason="requested prompt plus reserved output exceeds configured window",
            )
        print(
            f"{cell.cell_id} not_applicable: {cell.target_tokens}+{cell.output_tokens}>{cell.configured_window}"
        )
        return cell.status

    if live_models is not None and cell.model not in live_models:
        directory.mkdir(parents=True, exist_ok=True)
        write_status(
            directory / "cell.json",
            cell,
            "unsupported",
            reason="model is not present in the live endpoint inventory",
        )
        print(f"{cell.cell_id} unsupported: {cell.model} is absent from live inventory")
        return "unsupported"

    commands = [probe_command(cell, raw_output), publisher_command(cell, raw_output)]
    if dry_run:
        print(f"{cell.cell_id} planned: {json.dumps(asdict(cell), sort_keys=True)}")
        for command in commands:
            print("  " + " ".join(command))
        return "success"

    directory.mkdir(parents=True, exist_ok=True)
    write_status(directory / "cell.json", cell, "aborted", phase="starting")
    probe = subprocess.run(commands[0], cwd=repo_root, check=False)
    if probe.returncode or not raw_output.is_file():
        write_status(directory / "cell.json", cell, "failed", phase="probe", returncode=probe.returncode)
        return "failed"
    try:
        raw = json.loads(raw_output.read_text())
    except json.JSONDecodeError:
        write_status(directory / "cell.json", cell, "failed", phase="probe", reason="invalid raw JSON")
        return "failed"
    if raw.get("aborted"):
        write_status(directory / "cell.json", cell, "aborted", phase="probe", reason=raw["aborted"])
        return "aborted"
    publisher = subprocess.run(commands[1], cwd=repo_root, check=False)
    status = "success" if publisher.returncode == 0 else "failed"
    write_status(
        directory / "cell.json", cell, status, phase="publisher_dry_run", returncode=publisher.returncode
    )
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a non-publishing JSON-manifest context throughput campaign."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="print cells and commands; write nothing")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text())
        if not isinstance(manifest, dict):
            raise ValueError("manifest root must be an object")
        output_root = Path(manifest.get("output_root", "~/bench-runs")).expanduser()
        cells = load_cells(manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    repo_root = Path(__file__).resolve().parents[1]
    live_models = None if args.dry_run else served_models(next(iter(cells)).base_url) if cells else set()
    statuses = [run_cell(repo_root, output_root, cell, args.dry_run, live_models) for cell in cells]
    return 0 if all(status in {"success", "not_applicable"} for status in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
