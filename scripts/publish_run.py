#!/usr/bin/env python3
"""Back-compat shim — forwards to ``mlx-bench-publish``.

New code should call ``mlx_benchmarks.cli:main`` directly (it is registered
as the ``mlx-bench-publish`` console script). This shim is retained so the
CLAUDE.md / README / historical runbooks that reference
``scripts/publish_run.py`` keep working.
"""

from __future__ import annotations

import sys

from mlx_benchmarks.cli import main

if __name__ == "__main__":
    sys.exit(main())
