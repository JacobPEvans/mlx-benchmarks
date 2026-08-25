from __future__ import annotations

from typing import Any

from mlx_benchmarks.converters.agentic import AgenticConverter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.envelope import Envelope


class AgenticPartialConverter:
    kind = "agentic-partial"

    def build_envelope(self, raw: Any, ctx: ConverterContext) -> Envelope:
        entries = raw if isinstance(raw, list) else []
        recovered = {
            "cells": [entry for entry in entries if isinstance(entry, dict) and entry.get("kind") == "cell"],
            "multiturn": [
                entry for entry in entries if isinstance(entry, dict) and entry.get("kind") == "multiturn"
            ],
        }
        envelope = AgenticConverter().build_envelope(recovered, ctx)
        for result in envelope["results"]:
            tags = result.get("tags")
            if tags is not None:
                tags["recovered_partial"] = "true"
        return envelope
