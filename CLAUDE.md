# CLAUDE.md

This file documents key context for Claude Code sessions in this repo.

## Project overview

Benchmark harness for MLX-quantized and locally-hosted LLMs on Apple Silicon.
Orchestration, configs, and schema live here; results publish to
[JacobPEvans/mlx-benchmarks](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
on HuggingFace.

## Repository structure

```
configs/        # TOML config per (tool, suite) pair
harness/        # Inline eval scripts (framework-eval, etc.)
schema.json     # Envelope v1 spec — authoritative contract
.github/workflows/validate-schema.yml  # CI: lint schema + parse TOML configs
```

## Key conventions

- **Envelope schema**: every result set is wrapped in the v1 envelope (`schema.json`). Do not break backwards compatibility without bumping `schema_version`.
- **Minimal glue**: keep orchestration code thin. Prefer wiring upstream tools directly over reimplementing their logic.
- **Unique filenames**: HF dataset commits use `data/run-<timestamp>-<sha>-<suite>-<model_slug>.parquet` — use a filesystem-safe slug and never overwrite existing shards.
- **Dependency management**: `uv` + `pyproject.toml`. Run `uv sync` after pulling.

## Common tasks

```bash
# Validate schema and TOML configs
gh workflow run validate-schema.yml

# Run lm-eval coding suite (example)
lm_eval --model local-chat-completions \
  --model_args "base_url=http://localhost:11434/v1/chat/completions,model=$MODEL" \
  --tasks humaneval,mbpp --output_path ./run-output

# Sync dependencies
uv sync
```

## Environment requirements

- macOS on Apple Silicon
- Running `vllm-mlx` OpenAI-compatible inference server
- `HF_TOKEN` env var with write scope on the dataset namespace
