# configs/ layout

One TOML file per `(upstream-tool, suite)` pair. Configs are consumed by the
sweep orchestration (see the top-level [README](../README.md)) and should
contain **only** the parameters the upstream tool itself takes. No custom
wrapper logic.

## Layout (as shipped)

```text
configs/
├── LAYOUT.md                 # this file
├── lm-eval/
│   ├── coding.toml           # humaneval_instruct_qwen3, mbpp_instruct_qwen3
│   ├── reasoning.toml        # gsm8k_cot_zeroshot, arc_challenge
│   └── qwen3-tasks/          # think-stripping overlay for Qwen3.x models
└── vllm/
    └── benchmark_serving.toml # suite: throughput (vllm runs on an external host; no local install)
```

Planned but not yet implemented (file a
[benchmark request](../.github/ISSUE_TEMPLATE/benchmark-request.yml) if you
want to move any of these forward):

- `lm-eval/knowledge.toml` — mmlu / ifeval
- `lm-eval/math-hard.toml` — minerva math500
- `lighteval/*` — broader task coverage
- `mlxbench/*` — native vllm-mlx throughput harness

Add a subdirectory when you wire up the first suite for a given tool — do
not pre-create empty dirs.

## Non-TOML suite: framework-eval

The `framework-eval` suite does NOT live under `configs/`. It lives at
[`../harness/framework-eval/`](../harness/framework-eval/) as per-framework
Python scripts (`eval_openai_tool_calling.py`, `eval_qwen_agent.py`,
`eval_smolagents.py`, `eval_google_adk.py`). Each framework exposes a
different API shape, so a declarative TOML wrapper would be harder to
maintain than inline Python. See the harness directory's README for
details.

## TOML shape

Keep configs declarative and tool-native. Example (`lm-eval/coding.toml`):

```toml
# Passed to lm_eval (installed into .venv via uv sync)
model = "local-chat-completions"
tasks = ["humaneval", "mbpp"]
batch_size = 1
num_fewshot = 0
apply_chat_template = true
fewshot_as_multiturn = true

[model_args]
base_url = "http://localhost:11434/v1/chat/completions"
# model is injected per-sweep; leave out here
max_length = 32768
timeout = 3600
```

The sweep runner is responsible for injecting per-invocation values (`model`,
run metadata, output paths) and for converting tool output into the envelope
schema defined in [`schema.json`](../schema.json).

## Local vs cloud execution

**Default: local models only.** Local models share the vllm-mlx inference
backend via llama-swap and must run sequentially (only one model loaded at a
time).

**Cloud models can run in parallel** — they go through the Bifrost gateway at
`http://localhost:30080/v1/chat/completions` and do not touch the local
inference stack. Only include cloud models in a sweep when the word `cloud` or
`full` is explicitly requested. When cloud models are included, launch them
as concurrent background processes to avoid serializing on network I/O.

### Standard cloud comparison models (always include in `full` sweeps)

| Bifrost model ID | Resolves to | Notes |
| --- | --- | --- |
| `gemini/gemini-3-flash-preview` | Gemini 3 Flash | Fast Google model |
| `openai/gpt-5.4-mini` | GPT-5.4 Mini | Latest OpenAI quick model — verify name against catalog before use |
| `openrouter/auto` | Best available | OpenRouter auto-selects optimal model for the prompt |
| `openrouter/openrouter/free` | Best free model | OpenRouter free-tier routing (double-prefix required through Bifrost) |

**Important**: Always verify model names against the live catalog before use — names change faster
than documentation. Run `curl -s http://localhost:30080/v1/models | grep -o '"id":"[^"]*"'` to confirm.

OpenAI models via the bare `openai/` prefix use the `OPENAI_API_KEY` from Doppler project
`ai-ci-automation`. As of 2026-04-19 that key has exhausted quota — use `openrouter/openai/gpt-5.4-mini`
as the fallback path, which routes through `OPENROUTER_API_KEY` instead.

## Adding a new config

1. Identify which upstream tool covers the measurement you want.
2. Add a TOML file under the matching subdirectory.
3. Keep options tool-native — if you need a wrapper shim, that's a signal
   the wrong tool is being used.
4. Run a single-model smoke sweep locally, verify the envelope output
   validates against `schema.json`, and push the resulting Parquet to the
   HF dataset via the append pattern.
5. Open a PR with the new config plus a one-line row in the top-level README
   upstream-tools table if the tool isn't already listed.
