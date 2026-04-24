# mlx-benchmarks

[![test](https://github.com/JacobPEvans/mlx-benchmarks/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/JacobPEvans/mlx-benchmarks/actions/workflows/test.yml)
[![validate-schema](https://github.com/JacobPEvans/mlx-benchmarks/actions/workflows/validate-schema.yml/badge.svg?branch=main)](https://github.com/JacobPEvans/mlx-benchmarks/actions/workflows/validate-schema.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![HF Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20dataset-JacobPEvans%2Fmlx--benchmarks-yellow)](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
[![HF Space](https://img.shields.io/badge/%F0%9F%A4%97%20space-viewer-yellow)](https://huggingface.co/spaces/JacobPEvans/mlx-benchmarks-viewer)

A reproducible benchmark harness for **MLX-quantized** and **locally-hosted**
LLMs on Apple Silicon. One envelope schema, one HuggingFace dataset, one
interactive viewer — across every upstream evaluation tool.

**Why not just use lm-eval directly?** You can. This repo wraps lm-eval (and
other harnesses) with:

- A **single versioned result contract** (`schema.json`) so every shard is
  comparable across tools, models, and dates.
- A **publish pipeline** (`mlx-bench-publish`) that validates envelopes
  against the schema and uploads to the
  [HF dataset](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
  with content-addressed filenames.
- A **Gradio viewer** (in [`space/`](space/)) auto-deployed to an
  [HF Space](https://huggingface.co/spaces/JacobPEvans/mlx-benchmarks-viewer)
  on every `main` push.

Read results as a pandas DataFrame with no tooling beyond `huggingface_hub` +
`pyarrow`.

## Upstream tools wired in

| Tool | Suite(s) | Purpose |
| --- | --- | --- |
| [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) | `coding`, `reasoning` | Standard LLM evals (humaneval, mbpp, gsm8k, arc, ...) |
| [vllm `benchmark_serving`](https://docs.vllm.ai/en/latest/performance/benchmarks.html) | `throughput` | Cross-check throughput against vllm upstream (install with `[vllm]` extra) |
| OpenAI tool-calling baseline, [Qwen-Agent](https://github.com/QwenLM/Qwen-Agent), [smolagents](https://github.com/huggingface/smolagents), [Google ADK](https://github.com/google/adk-python) | `framework-eval` | Per-framework agent harness (`harness/framework-eval/`) |

Planned but not wired yet: lighteval (broader tasks), MLXBench (native throughput).
The `configs/LAYOUT.md` is the single source of truth for what is currently
implemented vs aspirational.

## Repository layout

```text
.
├── README.md                 <- this file
├── CLAUDE.md                 <- agent-facing project notes
├── CONTRIBUTING.md           <- dev workflow
├── SECURITY.md               <- HF token handling, unsafe-code warning
├── LICENSE                   <- Apache-2.0
├── schema.json               <- envelope v1 (authoritative)
├── examples/                 <- known-good + known-bad envelope fixtures
├── pyproject.toml            <- package + lint/type/test config
├── src/mlx_benchmarks/       <- Python package (publisher, converters)
│   ├── cli.py                <-   mlx-bench-publish entry point
│   ├── envelope.py           <-   typed envelope + jsonschema validator
│   ├── publish.py            <-   parquet + HF upload (unique filenames)
│   ├── system.py             <-   runtime detection of os/chip/memory/versions
│   ├── logging_config.py     <-   text + JSON-lines logging
│   └── converters/lm_eval.py <-   lm-eval results.json -> envelope
├── tests/                    <- package tests + fixtures
├── configs/                  <- one TOML per (tool, suite) pair
│   ├── LAYOUT.md
│   ├── lm-eval/{coding.toml, reasoning.toml, qwen3-tasks/}
│   └── vllm/benchmark_serving.toml
├── harness/                  <- inline-Python suites (non-TOML)
│   └── framework-eval/       <-   agent framework evaluations
├── scripts/                  <- one-shot tooling (validator, space deploy, legacy shim)
├── space/                    <- Gradio viewer (deployed to HF Space)
│   ├── app.py
│   ├── requirements.txt
│   ├── README.md             <-   HF Spaces front-matter
│   └── tests/
├── docs/                     <- architecture notes + run journals
│   ├── architecture.md
│   ├── schema.md
│   └── journal/
└── .github/workflows/        <- test, validate-schema, dry-run-publish,
                                  deploy-space, codeql, dependency-review,
                                  release-please
```

## Installation

Requires macOS on Apple Silicon (for inference) and Python 3.11+. A running
`vllm-mlx` OpenAI-compatible inference server on `http://localhost:11434/v1`
is assumed by the lm-eval configs.

```sh
git clone https://github.com/JacobPEvans/mlx-benchmarks.git
cd mlx-benchmarks

# Plain uv (recommended)
uv sync
# ...or plain pip into a venv
python -m venv .venv && source .venv/bin/activate && pip install -e ".[viewer]"

# Token with write scope on the HF dataset, required for publishing
export HF_TOKEN="hf_..."

# Install pre-commit hooks (optional but encouraged)
.venv/bin/pre-commit install
```

For Nix users: `direnv allow` activates the included `flake.nix` dev shell.

## Usage

### Run a benchmark and publish

```sh
# 1. Run lm-eval against your local vllm-mlx endpoint
.venv/bin/lm_eval --model local-chat-completions \
  --model_args "base_url=http://localhost:11434/v1/chat/completions,model=mlx-community/Qwen3.5-9B-MLX-4bit,max_length=32768,timeout=3600" \
  --tasks gsm8k_cot_zeroshot \
  --batch_size 1 --num_fewshot 0 --limit 10 \
  --gen_kwargs "max_gen_toks=4096" \
  --apply_chat_template --fewshot_as_multiturn --log_samples \
  --output_path ./run-output

# 2. Dry-run conversion (validates envelope against schema, no upload)
.venv/bin/mlx-bench-publish ./run-output/<model-dir>/results_*.json \
  --kind lm-eval --suite reasoning --dry-run

# 3. Publish to the HF dataset
.venv/bin/mlx-bench-publish ./run-output/<model-dir>/results_*.json \
  --kind lm-eval --suite reasoning
```

Filenames are deterministic — `data/run-<timestamp>-<git_sha>-<suite>-<model_slug>.parquet` —
so historical shards are never overwritten.

### View results

Open the live HF Space:
<https://huggingface.co/spaces/JacobPEvans/mlx-benchmarks-viewer>

Or run the viewer locally:

```sh
cd space
pip install -r requirements.txt
python app.py
```

## API

### The envelope

See [`schema.json`](schema.json) — it is the authoritative, versioned contract
backing every published shard. A minimal valid envelope:

```json
{
  "schema_version": "1",
  "timestamp": "2026-04-24T18:30:00Z",
  "git_sha": "aaa3ff3",
  "trigger": "local",
  "suite": "reasoning",
  "model": "mlx-community/Qwen3.5-9B-MLX-4bit",
  "system": {"os": "macOS 26.4.1", "chip": "Apple M4 Max", "memory_gb": 128},
  "results": [
    {"name": "gsm8k_cot_zeroshot", "metric": "exact_match_flexible",
     "value": 0.8, "unit": "ratio"}
  ]
}
```

Optional v1 fields (non-breaking additions): `seed`, `gen_kwargs`,
`model_revision`, `quantization`, and on the `system` object:
`python_version`, `mlx_version`, `mlx_lm_version`, `lm_eval_version`,
`kernel`. The CLI auto-detects all of these at publish time —
no hand-curation required.

See [`docs/schema.md`](docs/schema.md) for a prose walk-through of every field.

### The publisher

```python
from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.publish import publish
from mlx_benchmarks.system import detect_system

ctx = ConverterContext(
    suite="reasoning",
    model="mlx-community/Qwen3.5-9B-MLX-4bit",
    git_sha="aaa3ff3",
    system=detect_system(),
)
envelope = get_converter("lm-eval").build_envelope(raw_results, ctx)
publish(envelope, dry_run=False)  # validates + uploads
```

### Reading the dataset

```python
from datasets import load_dataset
ds = load_dataset("JacobPEvans/mlx-benchmarks")
print(ds["train"][0])
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full developer workflow.
Keep orchestration glue thin — if integrating a new upstream tool requires
more than ~50 lines of Python, re-read the tool's docs before writing code.

## Security

HF tokens, the `--confirm_run_unsafe_code` lm-eval flag, and the disclosure
policy are covered in [`SECURITY.md`](SECURITY.md).

## License

Apache 2.0. See [`LICENSE`](LICENSE).
