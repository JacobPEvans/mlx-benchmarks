"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def lm_eval_sample() -> dict[str, Any]:
    return json.loads((FIXTURES / "lm_eval_results_sample.json").read_text())


@pytest.fixture
def framework_eval_sample() -> dict[str, Any]:
    return json.loads((FIXTURES / "framework_eval_sample.json").read_text())


@pytest.fixture
def valid_envelope() -> dict[str, Any]:
    return json.loads((EXAMPLES / "envelope.valid.json").read_text())


@pytest.fixture
def invalid_envelope() -> dict[str, Any]:
    return json.loads((EXAMPLES / "envelope.invalid.json").read_text())
