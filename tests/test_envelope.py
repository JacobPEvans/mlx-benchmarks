"""Unit tests for the envelope validation API (mlx_benchmarks.envelope).

These exercise the public validation surface against a minimal, hand-built
envelope — complementary to test_schema.py, which validates schema.json itself
and the shipped example fixtures.
"""

from __future__ import annotations

from typing import Any

import pytest

from mlx_benchmarks.envelope import (
    EnvelopeValidationError,
    iter_validation_errors,
    load_schema,
    validate_envelope,
)


def _minimal_envelope() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "timestamp": "2026-07-16T00:00:00Z",
        "git_sha": "abc1234",
        "trigger": "local",
        "suite": "tool-calling",
        "model": "mlx-community/Test-4bit",
        "system": {"os": "macOS 26.0", "chip": "Apple M4 Max", "memory_gb": 128},
        "results": [{"name": "t", "metric": "score", "value": 1.0, "unit": "ratio"}],
    }


def test_minimal_envelope_validates() -> None:
    validate_envelope(_minimal_envelope())  # no raise


def test_missing_required_field_raises() -> None:
    env = _minimal_envelope()
    del env["results"]
    with pytest.raises(EnvelopeValidationError):
        validate_envelope(env)


def test_unknown_top_level_key_rejected() -> None:
    # additionalProperties: false at the top level guards against silent typos.
    env = _minimal_envelope()
    env["surprise"] = 1
    with pytest.raises(EnvelopeValidationError) as excinfo:
        validate_envelope(env)
    assert any("surprise" in e.message for e in excinfo.value.errors)


def test_result_value_must_be_number() -> None:
    env = _minimal_envelope()
    env["results"][0]["value"] = "high"
    with pytest.raises(EnvelopeValidationError) as excinfo:
        validate_envelope(env)
    paths = [list(e.absolute_path) for e in excinfo.value.errors]
    assert ["results", 0, "value"] in paths


def test_error_message_names_the_bad_field() -> None:
    env = _minimal_envelope()
    env["trigger"] = "nope"
    with pytest.raises(EnvelopeValidationError) as excinfo:
        validate_envelope(env)
    assert "trigger" in str(excinfo.value)


def test_iter_validation_errors_does_not_raise() -> None:
    env = _minimal_envelope()
    env["trigger"] = "nope"
    errors = list(iter_validation_errors(env))
    assert errors  # yields the enum violation instead of raising
    assert all(hasattr(e, "message") for e in errors)


def test_valid_envelope_has_no_iter_errors() -> None:
    assert list(iter_validation_errors(_minimal_envelope())) == []


def test_load_schema_is_cached() -> None:
    assert load_schema() is load_schema()
