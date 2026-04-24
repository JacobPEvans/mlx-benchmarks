<!-- Thanks for opening a PR. Keep it focused — one concept per PR. -->

## Summary

<!-- 1-3 bullets: what changes, and why. Leave the "how" for the diff. -->

-
-

## Test plan

<!-- Checklist of what you verified locally. CI will re-run these too. -->

- [ ] `.venv/bin/ruff check .`
- [ ] `.venv/bin/ruff format --check .`
- [ ] `.venv/bin/mypy src/mlx_benchmarks`
- [ ] `.venv/bin/pytest tests space/tests`
- [ ] `.venv/bin/python scripts/validate_schema.py`
- [ ] (if publisher changes) `mlx-bench-publish ... --dry-run` on a real result

## Related

<!-- Closes #NNN / refs #NNN / HF dataset shard link if applicable -->
