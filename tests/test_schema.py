"""Verify schema.json is itself valid and that canonical examples pass."""

from __future__ import annotations

import pytest
from jsonschema import Draft7Validator

from mlx_benchmarks.envelope import (
    EnvelopeValidationError,
    load_schema,
    validate_envelope,
)


def test_schema_is_valid_draft7() -> None:
    Draft7Validator.check_schema(load_schema())


def test_schema_declares_id_and_examples() -> None:
    schema = load_schema()
    assert schema.get("$id"), "schema must declare $id so consumers can pin to a canonical URL"
    assert schema.get("examples"), "schema should ship at least one example"


def test_valid_envelope_passes(valid_envelope: dict) -> None:
    validate_envelope(valid_envelope)


def test_invalid_envelope_fails(invalid_envelope: dict) -> None:
    with pytest.raises(EnvelopeValidationError) as excinfo:
        validate_envelope(invalid_envelope)
    message = str(excinfo.value)
    # Known problems in the fixture: bad schema_version, bad timestamp, bad git_sha, bad trigger, bad suite, short system.
    assert "schema_version" in message or "suite" in message
    # Multiple errors collected, not just the first
    assert len(excinfo.value.errors) >= 2


def test_format_checker_rejects_non_iso_timestamp(valid_envelope: dict) -> None:
    """Targeted test: without format_checker=, jsonschema accepts any string
    for ``format: date-time``. The publisher contract — and the viewer's
    ``pd.to_datetime`` — requires real ISO-8601, so the validator must enforce it."""
    bad = dict(valid_envelope)
    bad["timestamp"] = "not-an-iso-date"
    with pytest.raises(EnvelopeValidationError) as excinfo:
        validate_envelope(bad)
    # Error must be scoped to the timestamp field specifically.
    paths = [list(e.absolute_path) for e in excinfo.value.errors]
    assert ["timestamp"] in paths
