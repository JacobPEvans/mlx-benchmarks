"""Console logging setup for the CLI."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    """Minimal JSON-lines formatter (no external dep needed)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key in payload or key.startswith("_"):
                continue
            if key in {
                "args",
                "msg",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "name",
            }:
                continue
            try:
                json.dumps(value)
            except TypeError:
                value = repr(value)
            payload[key] = value
        return json.dumps(payload)


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    """Install a stdlib handler; idempotent across re-entries (e.g., tests)."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Remove handlers owned by us on re-run so test runners don't double-log.
    for existing in [h for h in root.handlers if getattr(h, "_mlx_benchmarks", False)]:
        root.removeHandler(existing)

    handler: logging.Handler = logging.StreamHandler(sys.stderr)
    handler._mlx_benchmarks = True  # type: ignore[attr-defined]
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
