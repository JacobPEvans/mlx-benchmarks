# MLX LLM serving configs

Reference for every tunable parameter of the `vllm-mlx` serving stack, the
config files each model ships, and what we learn about them over time. The
goal: never again benchmark or serve a model with the wrong config because we
did not know a knob existed or did not check what the model itself declares.

## Why this exists

A model is not "slow" or "unstable" in the abstract — it is slow or unstable
**under a specific serving config**. Two failures this folder is meant to
prevent:

1. Forcing a generic config onto every model instead of the config that model
   was built for (e.g. serving an OptiQ KV-quant model with full-precision KV,
   or a model with MTP heads without `--enable-mtp`).
2. Blaming the model (or the framework) for a result that a missing flag, a
   warm/cold cache, or a default value fully explains.

Workspace rule "config parity first, no bug-blame": prove we are using each
model's proper config before attributing any behavior to the model.

## Contents

- [`serve-parameters.md`](serve-parameters.md) — every `vllm-mlx serve` flag,
  grouped by concern, with defaults and tuning notes.
- [`model-config-files.md`](model-config-files.md) — the files a model ships
  (`config.json`, `kv_config.json`, `generation_config.json`, MTP weights)
  and how `vllm-mlx` consumes them, plus a pre-serve parity checklist.
- [`learnings.md`](learnings.md) — dated log of what we have learned per
  model or parameter. Append here; do not rewrite history.

## How to use before serving or benchmarking a model

1. Read the model's own config files (see `model-config-files.md`). Note any
   `kv_config.json`, `mtp_*` keys, and `generation_config.json` defaults.
2. Map each declared feature to the matching `serve` flag
   (see `serve-parameters.md`). If the model declares KV quant or MTP, the
   serve command MUST enable it, or you are not serving that model.
3. Run the parity checklist. Only then benchmark, and control the prefix
   cache (it dominates repeated-prompt throughput — see `learnings.md`).

## How to extend

- New parameter observed: add it to `serve-parameters.md` with its default and
  what it does. Source it from `vllm-mlx serve --help`, never from memory.
- New model behavior understood: add a dated entry to `learnings.md` with the
  evidence (log line, config key, or measured numbers) that supports it.
- Keep lines at or under 80 characters so the docs lint clean.
