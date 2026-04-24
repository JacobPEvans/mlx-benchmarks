# CLAUDE.md

Agent-facing notes for Claude Code sessions in this repo. For the
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

```
src/mlx_benchmarks/    Python package (envelope, publish, converters, CLI)
scripts/               Small one-shot tools (validator, space deploy, legacy shim)
configs/               TOML per (tool, suite) pair — see configs/LAYOUT.md
harness/framework-eval/ Inline Python suites (agent frameworks)
schema.json            Envelope v1 authoritative contract
examples/              Canonical valid + invalid envelope fixtures
tests/                 Pytest suite with fixtures
space/                 Gradio viewer (deployed to HF Space)
docs/                  architecture.md, schema.md, journal/ (session notes)
.github/workflows/     test, validate-schema, dry-run-publish, codeql,
                       dependency-review, deploy-space, release-please
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
- **Main workflow uses the venv directly**: for the publisher and primary
  evaluation commands, use `.venv/bin/lm_eval`, `.venv/bin/mlx-bench-publish`,
  etc. rather than `uv run` / `uvx`. Exception: `harness/framework-eval/`
  uses `uv run --with ...` because each per-framework script declares its
  own dependencies via PEP 723 inline metadata.
- **Conventional commits**: `release-please` consumes them. `feat:` minor,
  `fix:` patch. Never manually edit `CHANGELOG.md`.
- **Pre-commit must pass**: `.venv/bin/pre-commit run --all-files`. CI
  re-runs ruff + ruff-format + mypy + pytest. Zero tolerance for `# noqa`
  suppressions — fix the underlying issue.

## Common tasks

```bash
# Quality gates (run all before committing)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy src/mlx_benchmarks
.venv/bin/pytest tests space/tests
.venv/bin/python scripts/validate_schema.py

# Publish a run (dry-run first!)
.venv/bin/mlx-bench-publish run-output/<...>/results_*.json \
  --kind lm-eval --suite reasoning --dry-run
.venv/bin/mlx-bench-publish run-output/<...>/results_*.json \
  --kind lm-eval --suite reasoning

# Run lm-eval smoke (adjust model + task)
.venv/bin/lm_eval --model local-chat-completions \
  --model_args "base_url=http://localhost:11434/v1/chat/completions,model=$MODEL,max_length=32768,timeout=3600" \
  --tasks gsm8k_cot_zeroshot --batch_size 1 --num_fewshot 0 --limit 10 \
  --gen_kwargs "max_gen_toks=4096" \
  --apply_chat_template --fewshot_as_multiturn --log_samples \
  --output_path ./run-output
```

## Environment requirements

- macOS on Apple Silicon (inference); CI runs publisher on ubuntu-latest.
- `vllm-mlx` (via `llama-swap`) on `http://localhost:11434/v1`. The
  `base_url` for lm-eval must include the full `/v1/chat/completions`
  path — not just `/v1`.
- Python 3.11+.
- `HF_TOKEN` with write scope on the dataset namespace (for publish) and
  on the space namespace (for deploy, stored as a repo secret).

## Gotchas learned the hard way

- **Model names**: verify against the live catalog
  (`curl http://localhost:11434/v1/models`). Don't trust docs.
- **Never discard completed runs**: publish with `tags.caveat=...` and file
  an issue rather than throwing away benchmark time.
- **Coding benchmarks execute model-generated code** — see
  [`SECURITY.md`](SECURITY.md) before running outside a sandbox.
