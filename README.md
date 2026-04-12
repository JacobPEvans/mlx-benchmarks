# mlx-benchmarks

Benchmark harness for **MLX-quantized** and other **locally-hosted LLMs** on
Apple Silicon. Orchestration, configs, and schema live here; results are
published to the companion HuggingFace dataset.

- **Results**: [huggingface.co/datasets/JacobPEvans/mlx-benchmarks](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
- **Schema**: [`schema.json`](schema.json) (envelope v1)

## Philosophy

Wire upstream evaluation tools directly. No custom benchmark harness code
beyond the thinnest possible orchestration layer and result-envelope
conversion. If an upstream tool covers a measurement, use it.

Upstream tools integrated:

| Tool | Suites | Purpose |
| --- | --- | --- |
| [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) | `coding`, `reasoning`, `knowledge`, `math-hard` | Standard LLM evals (humaneval, mbpp, gsm8k, hellaswag, arc, mmlu, ifeval, minerva math) |
| [linusvwe/MLXBench](https://github.com/linusvwe/MLXBench) | `throughput`, `ttft` | Native vllm-mlx throughput and time-to-first-token |
| [vllm `benchmark_serving`](https://docs.vllm.ai/en/latest/performance/benchmarks.html) | `throughput` (second opinion) | Cross-check against vllm-upstream's own harness |
| [huggingface/lighteval](https://github.com/huggingface/lighteval) | `coding` (livecodebench), extended tasks | Broader task coverage where lm-eval lags |

## Repository layout

```text
.
├── README.md                 # this file
├── LICENSE                   # Apache 2.0
├── schema.json               # envelope v1 spec (authoritative)
├── cspell.json               # project domain dictionary
├── .gitignore
├── configs/                  # one TOML per (tool, suite) pair
│   ├── LAYOUT.md
│   ├── lm-eval/
│   ├── mlxbench/
│   ├── vllm/
│   └── lighteval/
└── .github/
    └── workflows/
        └── validate-schema.yml   # lint schema.json + sample envelopes
```

Configs are added incrementally as each upstream tool is wired up. Start with
whichever suite you want to measure first; see [`configs/LAYOUT.md`](configs/LAYOUT.md)
for the pattern.

## Installation

Requires macOS (Apple Silicon) with `uv` (from [Astral](https://github.com/astral-sh/uv))
and a running `vllm-mlx` OpenAI-compatible inference server on the local
machine.

```bash
# Clone this repo
git clone https://github.com/JacobPEvans/mlx-benchmarks.git
cd mlx-benchmarks

# Install uv if you don't have it already (otherwise skip)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Export a HuggingFace token with `write` scope on the dataset namespace
# (create at https://huggingface.co/settings/tokens)
export HF_TOKEN="hf_..."

# Start a local vllm-mlx server in a separate shell
# See https://github.com/blaizzy/mlx-vllm for server setup
```

No dependencies beyond what individual upstream tools pull in via `uvx`.

## Usage

A "sweep" is: for each selected `(suite, model)` pair, run the matching
upstream tool with its config, capture the output, map it to the envelope
schema, serialize to a single-run Parquet, and append to the HF dataset via
unique-filename commit.

Generic shape (exact form depends on the tool):

```bash
# Example: run lm-eval coding suite against a local vllm-mlx endpoint
uvx --with 'lm-eval[api]==0.4.11' lm_eval \
    --model local-chat-completions \
    --model_args "base_url=http://localhost:11434/v1,model=$MODEL" \
    --tasks humaneval,mbpp \
    --output_path ./run-output
```

Then convert `./run-output/*.json` to envelope format and push:

```python
from huggingface_hub import HfApi, CommitOperationAdd
import io, pyarrow.parquet as pq
# ... construct a pyarrow.Table from the flattened envelope rows ...
buf = io.BytesIO()
pq.write_table(table, buf)
HfApi().create_commit(
    repo_id="JacobPEvans/mlx-benchmarks",
    repo_type="dataset",
    operations=[CommitOperationAdd(
        path_in_repo=f"data/run-{timestamp}-{git_sha}-{suite}-{model_slug}.parquet",
        path_or_fileobj=buf.getvalue(),
    )],
    commit_message=f"feat: add {suite} run for {model}",
)
```

Each `create_commit` writes a **unique filename**, so historical shards are
never overwritten. `load_dataset()` on the HF side concatenates all
`data/*.parquet` files into the `train` split automatically.

## API

The **envelope** is the contract between generators and the HF dataset. See
[`schema.json`](schema.json) for the authoritative v1 definition. High-level
shape:

```json
{
  "schema_version": "1",
  "timestamp": "2026-04-11T20:25:06Z",
  "git_sha": "abc1234",
  "trigger": "local",
  "suite": "throughput",
  "model": "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
  "system": {"os": "macOS 26.4", "chip": "Apple M4 Max", "memory_gb": 128},
  "results": [
    {"name": "short-50", "metric": "throughput", "value": 38.4, "unit": "tok/s"}
  ],
  "errors": []
}
```

On the HF dataset side, envelopes are exploded into flat scalar rows (one per
`results[]` entry). See the
[dataset card](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks) for
the full column reference. Reading example:

```python
from datasets import load_dataset
ds = load_dataset("JacobPEvans/mlx-benchmarks")
print(ds["train"][0])
```

## Contributing

One PR per incremental improvement. Keep custom code minimal — if you find
yourself writing more than ~50 lines of orchestration glue to integrate a new
upstream tool, step back and see whether the tool already handles what
you're trying to add.

## License

Apache 2.0. See [`LICENSE`](LICENSE).
