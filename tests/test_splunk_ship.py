"""Cover the Splunk HEC side-channel without touching the network."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest

from mlx_benchmarks import splunk
from mlx_benchmarks.splunk import (
    SplunkShipError,
    envelope_to_hec_events,
    ship_envelope,
)


def _envelope() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "timestamp": "2026-05-01T12:00:00Z",
        "git_sha": "deadbeef",
        "trigger": "schedule",
        "suite": "capability-comparison",
        "model": "flagship-sweep",
        "system": {},
        "results": [
            {
                "name": "baseline-gpt-oss-120b",
                "metric": "mean_score",
                "value": 0.5,
                "unit": "ratio",
                "tags": {"model": "baseline-gpt-oss-120b", "n_tests": "2"},
            },
            {
                "name": "candidate-qwen3-235b",
                "metric": "mean_score",
                "value": 0.9,
                "unit": "ratio",
                "tags": {"model": "candidate-qwen3-235b", "n_tests": "2"},
            },
        ],
    }


def test_events_use_model_tag_and_value_as_score() -> None:
    events = envelope_to_hec_events(_envelope())
    assert len(events) == 2
    first = events[0]
    assert first["sourcetype"] == "model_eval"
    assert first["index"] == "ai"
    ev = first["event"]
    assert ev["model"] == "baseline-gpt-oss-120b"
    assert ev["suite"] == "capability-comparison"
    assert ev["score"] == 0.5
    assert ev["metric"] == "mean_score"
    assert ev["git_sha"] == "deadbeef"


def test_events_fall_back_to_envelope_model_without_tag() -> None:
    envelope = _envelope()
    envelope["results"][0]["tags"] = {}
    events = envelope_to_hec_events(envelope)
    assert events[0]["event"]["model"] == "flagship-sweep"


def test_ship_envelope_posts_all_events(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    @contextmanager
    def fake_urlopen(request: Any, timeout: float = 0):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["headers"] = request.headers
        response = MagicMock()
        response.status = 200
        yield response

    monkeypatch.setattr(splunk.urllib.request, "urlopen", fake_urlopen)

    count = ship_envelope(
        _envelope(),
        hec_url="https://splunk.example:8088/services/collector/event",
        hec_token="token-abc",
    )

    assert count == 2
    assert captured["url"].endswith("/services/collector/event")
    # Authorization header carries the Splunk token scheme.
    assert captured["headers"]["Authorization"] == "Splunk token-abc"
    # Body is newline-delimited JSON, one event per result.
    lines = captured["body"].decode().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"]["model"] == "baseline-gpt-oss-120b"


def test_ship_envelope_rejects_empty_results() -> None:
    envelope = _envelope()
    envelope["results"] = []
    with pytest.raises(SplunkShipError, match="nothing to ship"):
        ship_envelope(envelope, hec_url="https://x/y", hec_token="t")


def test_ship_envelope_wraps_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    def raise_http(request: Any, timeout: float = 0):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(splunk.urllib.request, "urlopen", raise_http)

    with pytest.raises(SplunkShipError, match="HTTP 403"):
        ship_envelope(_envelope(), hec_url="https://x/y", hec_token="t")
