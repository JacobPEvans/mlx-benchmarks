# framework-eval harness

Per-framework evaluation scripts for the `framework-eval` suite defined in
the [envelope schema](../../schema.json). Each script runs a fixed prompt
against a local vllm-mlx OpenAI-compatible endpoint using a specific agent
framework and reports timing + tool-use correctness.

Unlike `lm-eval` which is driven by declarative TOML configs under
[`configs/lm-eval/`](../../configs/lm-eval/), framework-eval uses inline
Python scripts — each framework exposes a different API shape and the
cleanest way to compare them is to call each one natively.

## Frameworks

| Framework | Script | Upstream |
| --- | --- | --- |
| OpenAI tool-calling (baseline) | [`eval_openai_tool_calling.py`](eval_openai_tool_calling.py) | raw `openai` client — no framework |
| Qwen-Agent | [`eval_qwen_agent.py`](eval_qwen_agent.py) | [QwenLM/Qwen-Agent](https://github.com/QwenLM/Qwen-Agent) |
| smolagents | [`eval_smolagents.py`](eval_smolagents.py) | [huggingface/smolagents](https://github.com/huggingface/smolagents) |
| Google ADK | [`eval_google_adk.py`](eval_google_adk.py) | [google/adk-python](https://github.com/google/adk-python) |

All four use the same fixed fixture and measure the same success criteria,
so scores are directly comparable across frameworks.

## Installation

Each script declares its dependencies via PEP 723 inline metadata (`# ///
script` header). `uv run --with` adds explicit minimum versions on top.
No `pyproject.toml` changes needed. The only prerequisites are:

```bash
# uv (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# vllm-mlx running locally on port 11434 (OpenAI-compatible endpoint)
# See https://github.com/blaizzy/mlx-vllm for server setup

# Env vars consumed by the scripts
export MLX_API_URL="http://127.0.0.1:11434/v1"
export MLX_DEFAULT_MODEL="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
```

## Usage

Run a single framework:

```bash
uv run --with 'openai>=1.0.0' eval_openai_tool_calling.py
uv run --with 'qwen-agent>=0.0.14' --with 'soundfile>=0.13.0' eval_qwen_agent.py
uv run --with 'smolagents>=1.0.0' eval_smolagents.py
uv run --with 'google-adk>=0.5.0' eval_google_adk.py
```

Or run all four back-to-back (writes to stdout — no file output yet):

```bash
./run_all.sh
```

Each run prints a JSON object to stdout with `framework`, `answer`, `latency`
(seconds), and — where the framework exposes them — `tool_calls`, `tokens`,
and `steps`. See each script's `__main__` block for the exact output shape.

## API

Current status: **scripts print JSON to stdout**. A framework-eval
converter that maps that output onto envelope v1 is planned but not yet
implemented — follow-up work is tracked as a
[benchmark request](../../.github/ISSUE_TEMPLATE/benchmark-request.yml).

The target envelope schema lives at [`../../schema.json`](../../schema.json).
A framework-eval row maps to the envelope shape as follows:

```json
{
  "schema_version": "1",
  "suite": "framework-eval",
  "model": "$MLX_DEFAULT_MODEL",
  "results": [
    {"name": "langgraph",  "metric": "score",   "value": 1.0,  "unit": "bool"},
    {"name": "langgraph",  "metric": "latency", "value": 12.3, "unit": "sec"},
    {"name": "qwen-agent", "metric": "score",   "value": 1.0,  "unit": "bool"}
  ],
  "errors": []
}
```

One envelope per `(model, framework)` per run, with result entries for
score, latency, and (where the framework exposes them) input/output token
counts.

## Contributing

Add a new framework by:

1. Copying one of the existing `eval_*.py` scripts as a template.
2. Rewriting the `run_agent()` function to use the new framework's API.
3. Keeping the fixture (`/tmp/eval-test.txt`) and success criteria identical
   so scores stay comparable.
4. Adding a row to the table in this README and a line to `run_all.sh`.
5. Adding any new dependencies as `uv run --with` flags rather than editing
   the top-level pyproject.toml.

## License

Apache 2.0 — see [`../../LICENSE`](../../LICENSE).
