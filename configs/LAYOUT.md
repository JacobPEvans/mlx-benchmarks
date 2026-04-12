# configs/ layout

One TOML file per `(upstream-tool, suite)` pair. Configs are consumed by the
sweep orchestration (see the top-level [README](../README.md)) and should
contain **only** the parameters the upstream tool itself takes. No custom
wrapper logic.

## Layout

```text
configs/
├── README.md               # this file
├── lm-eval/
│   ├── coding.toml         # tasks: humaneval, mbpp
│   ├── reasoning.toml      # tasks: gsm8k, hellaswag, arc_easy, arc_challenge
│   ├── knowledge.toml      # tasks: mmlu, ifeval
│   └── math-hard.toml      # tasks: minerva_math500
├── mlxbench/
│   ├── throughput.toml
│   └── ttft.toml
├── vllm/
│   └── benchmark_serving.toml
└── lighteval/
    └── broad-coverage.toml
```

Subdirectories are created lazily \u2014 add one when you wire up the first suite
for a given tool.

## TOML shape

Keep configs declarative and tool-native. Example (`lm-eval/coding.toml`):

```toml
# Passed to lm-eval via uvx --with 'lm-eval[api]==0.4.11' lm_eval
model = "local-chat-completions"
tasks = ["humaneval", "mbpp"]
batch_size = 1
num_fewshot = 0
apply_chat_template = true
fewshot_as_multiturn = true

[model_args]
base_url = "http://localhost:11434/v1"
# model is injected per-sweep; leave out here
max_length = 32768
timeout = 3600
```

The sweep runner is responsible for injecting per-invocation values (`model`,
run metadata, output paths) and for converting tool output into the envelope
schema defined in [`schema.json`](../schema.json).

## Adding a new config

1. Identify which upstream tool covers the measurement you want.
2. Add a TOML file under the matching subdirectory.
3. Keep options tool-native \u2014 if you need a wrapper shim, that's a signal
   the wrong tool is being used.
4. Run a single-model smoke sweep locally, verify the envelope output
   validates against `schema.json`, and push the resulting Parquet to the
   HF dataset via the append pattern.
5. Open a PR with the new config plus a one-line row in the top-level README
   upstream-tools table if the tool isn't already listed.
