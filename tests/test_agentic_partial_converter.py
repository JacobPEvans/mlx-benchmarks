from __future__ import annotations

from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import validate_envelope
from mlx_benchmarks.system import detect_system


def test_agentic_partial_converter_recovers_completed_units(agentic_sample: dict) -> None:
    raw = [
        {"kind": "cell", **agentic_sample["cells"][0]},
        {"kind": "multiturn", **agentic_sample["multiturn"][0]},
    ]
    envelope = get_converter("agentic-partial").build_envelope(
        raw,
        ConverterContext(
            suite="tool-calling",
            model="mlx-community/Qwen3.8-27B-4bit",
            git_sha="deadbeef",
            timestamp_override="2026-08-24T18:29:03Z",
            system=detect_system(),
        ),
    )
    validate_envelope(envelope)
    assert all(result["tags"]["recovered_partial"] == "true" for result in envelope["results"])
