# configs/ layout

One TOML file per `(upstream-tool, suite)` pair. These are **runbooks**: they
record the task list and tool-native options for a suite. No file here is read
by in-repo code — they document *what to run* so a run is reproducible.

## Layout (as shipped)

```text
configs/
├── LAYOUT.md                 # this file
├── lm-eval/
│   ├── reasoning.toml        # arc_challenge_chat (quick) / gsm8k (canonical)
│   ├── coding.toml           # humaneval, mbpp
│   ├── math-hard.toml        # minerva_math500
│   └── qwen3-tasks/          # optional <think>-stripping overlay (see below)
└── vllm/
    └── benchmark_serving.toml # vllm throughput cross-check; no local install
```

## Where the run command lives (single source of truth)

The canonical way to run these suites is the thin `uvx` wrappers in the serving
stack (nix-ai `modules/mlx/packages.nix`), **not** a script in this repo:

- `mlx-eval <tasks…>` — lm-eval against the live vllm-mlx server. It owns the
  connection args: `base_url`, `max_length=32768`, `num_concurrent`
  (`MLX_EVAL_CONCURRENT`, default 4), `--apply_chat_template`. Do **not**
  re-specify those as authoritative here — the `[model_args]` blocks below
  mirror them only so the runbook reads standalone.
- `mlx-bench` / `mlx-bench-raw` — vllm-mlx / raw `mlx_lm.benchmark` throughput.
- `mlx-wait` — health-gate the server before a run.

This repo owns only the step *after* a run: convert the tool's JSON to envelope
v1 and publish it (`mlx-bench-publish`). See the top-level
[README](../README.md) → "Run + publish a benchmark".

## qwen3-tasks overlay (optional)

`configs/lm-eval/qwen3-tasks/` provides `humaneval`/`mbpp` variants that strip
`<think>…</think>` blocks before code extraction — only needed when a model
emits raw reasoning in its completion. Current residents (Instruct / harmony
models served through vllm-mlx) return the final answer directly, so the plain
`humaneval`/`mbpp` tasks in `coding.toml` are the default. Use the overlay via
`--include_path configs/lm-eval/qwen3-tasks` only if a model's raw `<think>`
output leaks into scored text.

## TOML shape

Keep configs declarative and tool-native. The runner injects per-invocation
values (`model`, output paths); the converter maps the tool's JSON to
[`schema.json`](../schema.json).

## Local vs cloud execution

**Default: local models only** — they share the vllm-mlx backend via llama-swap
and run sequentially (one model resident at a time on the MacBook; the Studio
keeps a resident pair). Cloud comparison models go through the Bifrost gateway
(`http://localhost:30080/v1/chat/completions`) and only belong in a sweep when
`cloud`/`full` is explicitly requested. Always verify model names against the
live catalog first:
`curl -s http://localhost:30080/v1/models | grep -o '"id":"[^"]*"'`.

## Adding a new config

1. Identify which upstream tool covers the measurement.
2. Add a TOML under the matching subdirectory; keep options tool-native — a
   wrapper shim is a signal the wrong tool is being used.
3. Smoke it against one model, confirm the envelope validates against
   `schema.json`, publish the Parquet to the HF dataset.
4. Open a PR adding a row to the README upstream-tools table if new.
