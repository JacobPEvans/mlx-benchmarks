# Architecture

High-level data flow, from "I kick off a benchmark" to "I see a chart".

```text
 ┌───────────────────────────┐      ┌─────────────────────────────┐
 │  Local Apple-Silicon box  │      │        GitHub Actions       │
 │                           │      │                             │
 │  vllm-mlx (llama-swap)    │      │  test / lint / mypy / CodeQL│
 │     ↑ /v1/chat/...        │      │  dry-run-publish (fixture)  │
 │     │                     │      │  deploy-space (on main)     │
 │  lm_eval / vllm / ...     │      │  release-please (on main)   │
 │     │ results_*.json      │      └──────────────┬──────────────┘
 │     ▼                     │                     │ HF_TOKEN
 │  mlx-bench-publish        │                     ▼
 │   ├─ detect_system()      │      ┌─────────────────────────────┐
 │   ├─ Converter→Envelope   │      │     HuggingFace Hub          │
 │   ├─ validate_envelope()  │      │                             │
 │   ├─ rows_to_parquet()    │─────►│  dataset: mlx-benchmarks    │
 │   └─ HfApi.create_commit()│      │     data/run-*.parquet      │
 │                           │      │                             │
 └───────────────────────────┘      │  space:  mlx-benchmarks-    │
                                    │          viewer  (Gradio)   │
                                    └──────────────┬──────────────┘
                                                   │ read-only
                                                   ▼
                                           ┌───────────────┐
                                           │ Viewer users  │
                                           │   (browser)   │
                                           └───────────────┘
```

## Components

### Inference layer

`vllm-mlx` served via `llama-swap` on port 11434. OpenAI-compatible; every
tool in this repo talks to it via `http://localhost:11434/v1/chat/completions`.
Model switching is handled by `mlx-switch` / `sync-mlx-models` outside this
repo.

### Evaluation layer

Everything under `configs/` (TOML per suite) plus inline scripts in
`harness/framework-eval/`. TOML configs are consumed directly by the upstream
tool (`lm_eval --config`, etc.). No config-to-arg translation layer lives
here; the TOML is the runbook.

### Publisher (`src/mlx_benchmarks/`)

Pure-Python, no Apple-Silicon dependencies. Converts raw tool output into
the envelope v1 shape, validates it against `schema.json`, serializes to
Parquet, and uploads via `HfApi.create_commit` with a deterministic
content-addressed filename pattern:

```
data/run-<ISO-timestamp>-<git_sha>-<suite>-<model_slug>.parquet
```

This guarantees idempotent re-publishes and no overwrites. The envelope
validator is invoked inside `publish()` — you cannot accidentally ship a
non-compliant shard.

### Viewer (`space/`)

Gradio app that reads every `data/*.parquet` shard via `HfFileSystem`,
caches for 10 minutes, and renders three tabs (bar / trend / pivot).
Deployed to HF Spaces by `.github/workflows/deploy-space.yml` on `main`
pushes that touch `space/`.

### CI

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `test.yml` | PR, push to main | ruff + mypy + pytest (3.11 + 3.12 matrix) |
| `validate-schema.yml` | PR touching schema/configs | schema Draft-07 check + TOML parse |
| `dry-run-publish.yml` | PR | end-to-end publisher round-trip on fixture |
| `dependency-review.yml` | PR | Block PRs introducing high-severity advisories |
| `deploy-space.yml` | main push to `space/**` | Sync viewer to HF Space |
| `release-please.yml` | main push | Conventional-commits-driven releases |

CodeQL Python + Actions scanning is provided by GitHub's
**default CodeQL setup** (repo Security settings), not by a workflow file in
this repo. A previous attempt to add a custom `codeql.yml` workflow conflicted
with the default setup ("CodeQL analyses from advanced configurations cannot
be processed when the default setup is enabled") and was removed.

## Reproducibility contract

A published shard records the full context needed to replay:

- `git_sha` — state of this repo at run time.
- `system.*` — OS, chip, memory, plus (optional) `python_version`,
  `mlx_version`, `mlx_lm_version`, `lm_eval_version`, `kernel`.
- `gen_kwargs` — generation hyperparameters passed to the inference API.
- `seed` — when the run was seeded.
- `model_revision` / `quantization` — model-side metadata when reported.

The CLI fills these in automatically; never hand-curate unless you know why.

## Non-goals

- Running benchmarks in CI. MLX requires macOS on Apple Silicon; GitHub's
  macOS runners do not offer the hardware cheaply enough. CI tests the
  **publisher**, not the benchmarks themselves.
- A custom benchmark harness. If a measurement is possible via an existing
  upstream tool, wire the tool — do not reimplement.
- Overwriting history. Published shards are immutable; a new run becomes a
  new shard.
