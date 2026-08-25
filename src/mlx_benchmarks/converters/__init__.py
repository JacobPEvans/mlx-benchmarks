"""Converters transform raw tool output into envelope v1."""

from mlx_benchmarks.converters.agentic import AgenticConverter
from mlx_benchmarks.converters.agentic_partial import AgenticPartialConverter
from mlx_benchmarks.converters.base import Converter, ConverterContext
from mlx_benchmarks.converters.bench_serve import BenchServeConverter
from mlx_benchmarks.converters.factual import FactualConverter
from mlx_benchmarks.converters.lm_eval import LmEvalConverter
from mlx_benchmarks.converters.promptstack import PromptstackConverter
from mlx_benchmarks.converters.throughput_probe import ThroughputProbeConverter
from mlx_benchmarks.converters.vllm import VllmConverter

__all__ = [
    "AgenticConverter",
    "AgenticPartialConverter",
    "BenchServeConverter",
    "Converter",
    "ConverterContext",
    "FactualConverter",
    "LmEvalConverter",
    "PromptstackConverter",
    "ThroughputProbeConverter",
    "VllmConverter",
    "get_converter",
]


def get_converter(kind: str) -> Converter:
    """Return the converter registered for ``kind``.

    Raises :class:`ValueError` for unknown kinds so callers get a clear signal
    instead of silently defaulting.
    """
    registry: dict[str, type[Converter]] = {
        "agentic": AgenticConverter,
        "agentic-partial": AgenticPartialConverter,
        "bench-serve": BenchServeConverter,
        "factual": FactualConverter,
        "lm-eval": LmEvalConverter,
        "promptstack": PromptstackConverter,
        "throughput-probe": ThroughputProbeConverter,
        "vllm": VllmConverter,
    }
    try:
        cls = registry[kind]
    except KeyError as exc:
        known = ", ".join(sorted(registry)) or "(none)"
        raise ValueError(f"Unknown converter kind {kind!r}; known kinds: {known}") from exc
    return cls()
