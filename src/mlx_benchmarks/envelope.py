"""Envelope v1 types and schema validation.

The envelope is the authoritative contract between benchmark runners and
downstream consumers (the HuggingFace dataset, the Gradio viewer, any future
analysis pipeline). This module provides typed views of the envelope and a
runtime validator backed by ``schema.json``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, TypedDict

import jsonschema
from jsonschema import Draft7Validator


class System(TypedDict, total=False):
    os: str
    chip: str
    memory_gb: int
    vllm_mlx_version: str
    runner: str
    python_version: str
    mlx_version: str
    mlx_lm_version: str
    lm_eval_version: str
    kernel: str


class Result(TypedDict, total=False):
    name: str
    metric: str
    value: float
    unit: str
    tags: dict[str, str]
    raw: Any
    duration_seconds: float


class GenKwargs(TypedDict, total=False):
    max_gen_toks: int
    temperature: float
    top_p: float
    top_k: int


class Envelope(TypedDict, total=False):
    schema_version: str
    timestamp: str
    git_sha: str
    trigger: str
    pr_number: int | None
    suite: str
    model: str
    model_revision: str
    quantization: str
    skipped: bool
    seed: int
    gen_kwargs: GenKwargs
    system: System
    results: list[Result]
    memory_snapshots: list[dict[str, Any]]
    errors: list[str]


class EnvelopeValidationError(ValueError):
    """Raised when an envelope fails schema validation."""

    def __init__(self, errors: list[jsonschema.ValidationError]) -> None:
        self.errors = errors
        messages = "\n".join(
            f"  - {e.message} (at ${'.'.join(str(p) for p in e.absolute_path)})" for e in errors
        )
        super().__init__(f"Envelope failed schema validation:\n{messages}")


def _find_schema_path() -> Path:
    """Resolve schema.json whether running from source tree or installed wheel.

    Two supported layouts:

    1. **Installed wheel** (``pip install mlx-benchmarks``): the build copies
       ``schema.json`` into the package directory via
       ``[tool.hatch.build.targets.wheel.force-include]``. ``importlib.resources``
       locates it reliably inside site-packages.
    2. **Source tree** (editable install or running from the repo directly):
       the schema lives at the repo root; walk upward from this file.

    We try (1) first so installed-package behavior is the fast path; fall back
    to (2) for development. Failure is noisy — a missing schema means the
    publisher cannot validate envelopes.
    """
    try:
        pkg_file = resources.files("mlx_benchmarks") / "schema.json"
        if pkg_file.is_file():
            return Path(str(pkg_file))
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "schema.json"
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "Could not locate schema.json — expected alongside the installed "
        "mlx_benchmarks package (force-include) or at repository root."
    )


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Load and cache ``schema.json``."""
    with _find_schema_path().open() as f:
        loaded: dict[str, Any] = json.load(f)
        return loaded


@lru_cache(maxsize=1)
def _validator() -> Draft7Validator:
    """Cached validator with format checking enabled.

    Without ``format_checker=``, jsonschema silently accepts any string for
    ``format: date-time`` / URI / regex / etc. The envelope schema relies on
    ISO-8601 timestamps; downstream consumers (the viewer's
    ``pd.to_datetime`` call) assume that contract holds.
    """
    schema = load_schema()
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, format_checker=Draft7Validator.FORMAT_CHECKER)


def validate_envelope(envelope: Envelope | dict[str, Any]) -> None:
    """Raise :class:`EnvelopeValidationError` if the envelope is invalid.

    Collects every validation error rather than failing on the first —
    gives publishers a complete picture to fix in one pass.
    """
    errors: list[jsonschema.ValidationError] = sorted(
        _validator().iter_errors(envelope), key=lambda e: list(e.absolute_path)
    )
    if errors:
        raise EnvelopeValidationError(errors)


def iter_validation_errors(envelope: Envelope | dict[str, Any]) -> Iterable[jsonschema.ValidationError]:
    """Yield schema errors without raising — useful for best-effort downgrade to ``errors[]``."""
    yield from _validator().iter_errors(envelope)
