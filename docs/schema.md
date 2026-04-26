# Envelope schema (v1)

Canonical JSON Schema: [`schema.json`](../schema.json). This file is a prose
walk-through. When the two disagree, `schema.json` wins — please open a PR.

## Required top-level fields

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | `"1"` | Bump only on breaking changes. |
| `timestamp` | ISO 8601 UTC | `YYYY-MM-DDTHH:MM:SSZ`; use start-of-run, not end. |
| `git_sha` | 7–64 hex | SHA of **this repo** at run time, not the model. |
| `trigger` | `local \| schedule \| pr \| workflow_dispatch` | How the run was kicked off. |
| `suite` | enum | Must be in the closed set below. |
| `model` | string | HF model ID (e.g. `mlx-community/Qwen3.5-9B-MLX-4bit`). |
| `system` | object | See below. `os`, `chip`, `memory_gb` required. |
| `results` | array | Per-measurement rows. Empty array is not invalid but `publish()` refuses it at serialization time. |

Closed suite set: `throughput`, `ttft`, `tool-calling`, `code-accuracy`,
`framework-eval`, `capability-comparison`, `coding`, `reasoning`,
`knowledge`, `evalplus`, `math-hard`. Adding a suite means editing
`schema.json` and filing a schema update PR.

## Optional top-level fields

| Field | Type | Added when |
| --- | --- | --- |
| `pr_number` | integer \| null | `trigger == "pr"` |
| `model_revision` | string | Model provides HF revision or commit SHA. |
| `quantization` | string | Runtime reports it (e.g. `mlx-4bit`, `mxfp4`). |
| `skipped` | boolean | Suite intentionally skipped (CI without hardware). |
| `seed` | integer | Seeded generation. |
| `gen_kwargs` | object | `max_gen_toks` / `temperature` / `top_p` / `top_k`. |
| `memory_snapshots` | array | Future work — RSS / swap per phase. |
| `errors` | array of string | Non-fatal warnings recorded during the run. |

## `system` object

Required: `os`, `chip`, `memory_gb`.

Optional (all populated automatically by `detect_system()`):
`python_version`, `mlx_version`, `mlx_lm_version`, `lm_eval_version`,
`kernel`, `runner` (for GitHub Actions), `vllm_mlx_version`.

## `results[]` items

| Field | Type | Notes |
| --- | --- | --- |
| `name` | string (required) | Task or measurement ID (`gsm8k_cot_zeroshot`, `tok_per_sec_512`). |
| `metric` | string (required) | Display metric name (`exact_match_flexible`, `pass_at_1`, `throughput`). |
| `value` | number (required) | The measurement. |
| `unit` | string (required) | `ratio`, `tok/s`, `ms`, etc. |
| `duration_seconds` | number | Wall-clock for this measurement (first-class replacement for `tags.total_eval_time_s`). |
| `tags` | object\[string\] | Free-form string key-value metadata. |
| `raw` | any | Original untransformed tool output (optional archive). |

## Validation

Every envelope is validated inside `mlx_benchmarks.publish.publish()` —
bypass only by passing `validate=False` (strongly discouraged). The
validator collects *all* errors before raising, so a single run-through
surfaces everything wrong instead of one-at-a-time iteration.

Locally:

```python
from mlx_benchmarks.envelope import validate_envelope

# Raises EnvelopeValidationError with every problem
validate_envelope(my_envelope)
```

## Versioning

- Adding an optional field: non-breaking, no version bump.
- Adding an enum value to `suite`: non-breaking (downstream just ignores
  unknown suites in current viewers), but please file as a `feat:` PR.
- Removing or renaming a field, changing a type, tightening validation,
  changing the filename pattern: breaking. Bump `schema_version` to `"2"`
  and update `$id` accordingly.

Current `$id`: `https://github.com/JacobPEvans/mlx-benchmarks/schema/v1.json`.
