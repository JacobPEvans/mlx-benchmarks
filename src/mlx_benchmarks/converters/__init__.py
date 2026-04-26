"""Converters transform raw tool output into envelope v1."""

from mlx_benchmarks.converters.base import Converter, ConverterContext
from mlx_benchmarks.converters.lm_eval import LmEvalConverter
from mlx_benchmarks.converters.vllm import VllmConverter

__all__ = ["Converter", "ConverterContext", "LmEvalConverter", "VllmConverter", "get_converter"]


def get_converter(kind: str) -> Converter:
    """Return the converter registered for ``kind``.

    Raises :class:`ValueError` for unknown kinds so callers get a clear signal
    instead of silently defaulting.
    """
    registry: dict[str, type[Converter]] = {
        "lm-eval": LmEvalConverter,
        "vllm": VllmConverter,
    }
    try:
        cls = registry[kind]
    except KeyError as exc:
        known = ", ".join(sorted(registry)) or "(none)"
        raise ValueError(f"Unknown converter kind {kind!r}; known kinds: {known}") from exc
    return cls()
