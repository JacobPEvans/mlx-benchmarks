# mlx-benchmarks — AI Agent Documentation

Agent-facing notes for AI coding sessions in this repo. For the
human-facing overview, install instructions, and contribution guide see
[`README.md`](README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and
[`docs/architecture.md`](docs/architecture.md).

## Project overview

Benchmark harness for MLX-quantized and locally-hosted LLMs on Apple Silicon.
Orchestration configs and the envelope v1 schema live here; results publish
to the [`JacobPEvans/mlx-benchmarks`](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
HF dataset, visualized at the
[`mlx-benchmarks-viewer`](https://huggingface.co/spaces/JacobPEvans/mlx-benchmarks-viewer)
HF Space.

## Repository shape (short)

```text
src/mlx_benchmarks/    Python package (envelope, publish, converters, CLI)
scripts/               validate_schema.py (schema + TOML config validator)
configs/               TOML runbook per (tool, suite) pair — see configs/LAYOUT.md
schema.json            Envelope v1 authoritative contract
examples/              Canonical valid + invalid envelope fixtures
tests/                 Pytest suite with fixtures
space/                 Gradio viewer (deployed to HF Space)
docs/                  architecture.md, schema.md, journal/ (session notes)
.github/workflows/     ci-gate (test + lint + scan + dry-run-publish +
                       schema-validate via paths-filter), release-please
                       (wraps JacobPEvans/.github reusable), deploy-space
                       (CodeQL is via GitHub's default setup, not a workflow)
```

## Key conventions (non-negotiable)

- **Envelope contract**: every published result validates against
  `schema.json` inside `publish()`. Do not bypass with `validate=False` in
  real runs. Breaking changes require a `$id` bump + `schema_version`
  increment.
- **Unique filenames**: `data/run-<ts>-<git_sha>-<suite>-<slug>.parquet`.
  Never overwrite. Use `target_path(envelope)` to compute.
- **System detection**: always use `detect_system()`. Never hardcode system
  metadata.
- **Publisher runs from the venv**: `.venv/bin/mlx-bench-publish` and the
  quality gates run from `.venv/bin/*` (not `uv run` / `uvx`). The evaluation
  tools themselves (lm-eval, vllm `benchmark_serving`) are NOT dependencies of
  this repo — run them via the serving stack's `mlx-eval` / `mlx-bench`
  wrappers; this repo only parses their JSON output.
- **Conventional commits**: `release-please` consumes them. `feat:` minor,
  `fix:` patch. Never manually edit `CHANGELOG.md`.
- **Pre-commit must pass**: `.venv/bin/pre-commit run --all-files`. CI
  re-runs ruff + ruff-format + pyright + pytest. Zero tolerance for `# noqa`
  suppressions — fix the underlying issue.

## Common tasks

```bash
# Quality gates (run all before committing)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pyright src/mlx_benchmarks
.venv/bin/pytest tests space/tests
.venv/bin/python scripts/validate_schema.py

# Publish a run (dry-run first!)
.venv/bin/mlx-bench-publish run-output/<...>/results_*.json \
  --kind lm-eval --suite reasoning --dry-run
.venv/bin/mlx-bench-publish run-output/<...>/results_*.json \
  --kind lm-eval --suite reasoning

# Run an lm-eval smoke (lm-eval is external — via the mlx-eval wrapper or your
# own install; this repo only publishes its output). num_concurrent>1 is the
# biggest speedup for long suites.
lm_eval --model local-chat-completions \
  --model_args "base_url=http://localhost:11434/v1/chat/completions,model=$MODEL,num_concurrent=4,max_length=32768,timeout=3600" \
  --tasks gsm8k --limit 10 \
  --apply_chat_template --fewshot_as_multiturn --log_samples \
  --output_path ./run-output
```

## Environment requirements

- macOS on Apple Silicon (inference); CI runs publisher on ubuntu-latest.
- `vllm-mlx` (via `llama-swap`) on `http://localhost:11434/v1`. The
  `base_url` for lm-eval must include the full `/v1/chat/completions`
  path — not just `/v1`.
- Python 3.13+.
- `HF_TOKEN` with write scope on the dataset namespace (for publish) and
  on the space namespace (for deploy, stored as a repo secret).

## Gotchas learned the hard way

- **Model names**: verify against the live catalog
  (`curl http://localhost:11434/v1/models`). Don't trust docs.
- **Never discard completed runs**: publish with `tags.caveat=...` and file
  an issue rather than throwing away benchmark time.
- **Coding benchmarks execute model-generated code** — see
  [`SECURITY.md`](SECURITY.md) before running outside a sandbox.
