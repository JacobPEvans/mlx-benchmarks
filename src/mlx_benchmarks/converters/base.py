"""Converter protocol: raw tool output -> envelope v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from mlx_benchmarks.envelope import Envelope


@dataclass(slots=True)
class ConverterContext:
    """Inputs a converter needs beyond the raw tool output itself."""

    suite: str
    model: str
    git_sha: str
    trigger: str = "local"
    pr_number: int | None = None
    timestamp_override: str | None = None
    system: dict[str, Any] | None = None
    extra_tags: dict[str, str] = field(default_factory=dict)


class Converter(Protocol):
    """Implementations turn a parsed raw result into a valid :class:`Envelope`."""

    kind: str

    def build_envelope(
        self, raw: dict[str, Any], ctx: ConverterContext
    ) -> Envelope:  # pragma: no cover - protocol
        ...
