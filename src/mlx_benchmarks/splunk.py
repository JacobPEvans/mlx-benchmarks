"""Optional: ship an envelope summary to a Splunk HTTP Event Collector (HEC).

This is a side-channel to the primary HF-dataset publish flow — it lets a
scheduled eval job land per-result rows in Splunk (``index=ai
sourcetype=model_eval``) so regression alerts can watch score trends. It is
never required to publish; the CLI only calls it when ``--ship-splunk`` is set.

One HEC event is emitted per envelope result, carrying the model under test
(the result's ``model`` tag when present — the promptfoo converter sets it —
else the envelope model), the suite, the metric, and its value as ``score``.
The Splunk saved search keys on ``model`` + ``suite`` + ``score``.

Uses the stdlib ``urllib`` only — no new HTTP dependency.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from mlx_benchmarks.envelope import Envelope

log = logging.getLogger(__name__)

DEFAULT_SOURCETYPE = "model_eval"
DEFAULT_INDEX = "ai"


class SplunkShipError(RuntimeError):
    """Raised when the HEC POST fails (network, auth, non-2xx response)."""


def envelope_to_hec_events(
    envelope: Envelope,
    *,
    sourcetype: str = DEFAULT_SOURCETYPE,
    index: str = DEFAULT_INDEX,
) -> list[dict[str, Any]]:
    """Build the list of HEC event objects for ``envelope`` (one per result).

    Each event's ``event`` payload is flat and self-describing so the Splunk
    search does not need field extraction. Kept pure (no I/O) so it is trivially
    testable and reusable.
    """
    suite = envelope.get("suite")
    default_model = envelope.get("model")
    git_sha = envelope.get("git_sha")
    trigger = envelope.get("trigger")
    timestamp = envelope.get("timestamp")

    events: list[dict[str, Any]] = []
    for result in envelope.get("results", []):
        tags = result.get("tags") or {}
        events.append(
            {
                "sourcetype": sourcetype,
                "index": index,
                "event": {
                    "model": tags.get("model", default_model),
                    "suite": suite,
                    "name": result.get("name"),
                    "metric": result.get("metric"),
                    "score": result.get("value"),
                    "git_sha": git_sha,
                    "trigger": trigger,
                    "timestamp": timestamp,
                },
            }
        )
    return events


def ship_envelope(
    envelope: Envelope,
    *,
    hec_url: str,
    hec_token: str,
    sourcetype: str = DEFAULT_SOURCETYPE,
    index: str = DEFAULT_INDEX,
    timeout: float = 10.0,
) -> int:
    """POST every envelope result to Splunk HEC. Returns the event count sent.

    ``hec_url`` is the full collector endpoint (e.g.
    ``https://splunk.example:8088/services/collector/event``). Raises
    :class:`SplunkShipError` on an empty envelope or any transport/HTTP failure
    so a scheduled job can surface the problem instead of silently dropping
    telemetry.
    """
    events = envelope_to_hec_events(envelope, sourcetype=sourcetype, index=index)
    if not events:
        raise SplunkShipError("envelope has no results[] — nothing to ship to Splunk")

    # HEC accepts newline-delimited JSON event objects in a single request body.
    body = "\n".join(json.dumps(event) for event in events).encode("utf-8")
    request = urllib.request.Request(
        hec_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Splunk {hec_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        raise SplunkShipError(f"Splunk HEC returned HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise SplunkShipError(f"Splunk HEC request failed: {exc.reason}") from exc

    if not 200 <= status < 300:
        raise SplunkShipError(f"Splunk HEC returned unexpected status {status}")
    log.info("shipped %d event(s) to Splunk HEC (sourcetype=%s index=%s)", len(events), sourcetype, index)
    return len(events)
