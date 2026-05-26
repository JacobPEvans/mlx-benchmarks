# API Reference — `src/mlx_benchmarks`

This page covers the public surface of the four core modules.
For the envelope schema contract see [`schema.json`](../schema.json) and [`docs/schema.md`](schema.md).

---

## `mlx_benchmarks.envelope`

Types and runtime validation for the envelope v1 contract.

### TypedDicts

#### `System`

Runtime metadata about the machine that ran the benchmark.
All fields are optional in the TypedDict but `os`, `chip`, and `memory_gb` are
required by the JSON schema — `detect_system()` always populates them.

| Field | Type | Notes |
|-------|------|-------|
| `os` | `str` | e.g. `"macOS 26.4.1"` |
| `chip` | `str` | e.g. `"Apple M4 Max"` |
| `memory_gb` | `int` | Total RAM in GB |
| `kernel` | `str` | Kernel release string |
| `python_version` | `str` | e.g. `"3.11.9"` |
| `mlx_version` | `str` | |
| `mlx_lm_version` | `str` | |
| `lm_eval_version` | `str` | |
| `vllm_mlx_version` | `str` | |
| `runner` | `str` | CI runner label, if any |

#### `Result`

One measurement inside an envelope.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Task name, e.g. `"gsm8k_cot_zeroshot"` |
| `metric` | `str` | Metric key, e.g. `"exact_match_flexible"` |
| `value` | `float` | Numeric result |
| `unit` | `str` | `"ratio"`, `"tok/s"`, `"ms"`, ... |
| `tags` | `dict[str, str]` | Free-form key/value annotations |
| `raw` | `dict` | Raw tool output for this task |
| `duration_seconds` | `float` | Wall-clock seconds |
| `prompt_tokens_per_second` | `float` | |
| `decode_tokens_per_second` | `float` | |
| `total_tokens_per_second` | `float` | |
| `first_token_latency_ms` | `float` | Time to first token |
| `peak_rss_mb` | `float` | Peak resident set size |

#### `Envelope`

The top-level container published to the HuggingFace dataset.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | `str` | yes | Always `"1"` |
| `timestamp` | `str` | yes | ISO-8601 UTC |
| `git_sha` | `str` | yes | Short SHA of the commit that triggered the run |
| `trigger` | `str` | yes | `"local"`, `"ci"`, `"manual"` |
| `suite` | `str` | yes | Benchmark suite name |
| `model` | `str` | yes | HuggingFace model path |
| `system` | `System` | yes | Runtime metadata |
| `results` | `list[Result]` | yes | One entry per measurement |
| `pr_number` | `int` | | Pull request number if triggered by PR |
| `model_revision` | `str` | | Git ref for the model |
| `quantization` | `str` | | e.g. `"4bit"` |
| `skipped` | `list[str]` | | Tasks skipped due to errors |
| `seed` | `int` | | RNG seed used |
| `gen_kwargs` | `GenKwargs` | | Generation parameters |
| `memory_snapshots` | `list` | | Peak-memory checkpoints |
| `errors` | `list` | | Non-fatal errors from the run |

#### `GenKwargs`

Optional generation parameters stored in the envelope.

| Field | Type |
|-------|------|
| `max_gen_toks` | `int` |
| `temperature` | `float` |
| `top_p` | `float` |
| `top_k` | `int` |

### Exception

#### `EnvelopeValidationError`

```python
class EnvelopeValidationError(ValueError):
    errors: list[jsonschema.ValidationError]
```

Raised by `validate_envelope()` when the envelope violates `schema.json`.
Collects **all** violations rather than stopping at the first, so publishers
receive a complete list to fix in one pass.

### Functions

#### `validate_envelope(envelope)`

```python
def validate_envelope(envelope: Envelope | dict[str, Any]) -> None
```

Raise `EnvelopeValidationError` if the envelope is invalid.
Use this before calling `publish()` to get clear, aggregated error messages.

#### `iter_validation_errors(envelope)`

```python
def iter_validation_errors(envelope: Envelope | dict[str, Any]) -> Iterable[jsonschema.ValidationError]
```

Yield schema errors without raising -- useful for best-effort downgrade
to the `errors[]` field when partial envelopes are acceptable.

---

## `mlx_benchmarks.publish`

Serializes an envelope to Parquet and uploads it to the HuggingFace dataset.

### Constants

| Name | Default |
|------|---------|
| `DEFAULT_REPO_ID` | `"JacobPEvans/mlx-benchmarks"` |
| `DEFAULT_REPO_TYPE` | `"dataset"` |

### Exception

#### `PublishError`

```python
class PublishError(RuntimeError): ...
```

Raised for publisher-layer failures: auth errors, upload failures,
empty result sets.

### Functions

#### `publish(envelope, *, repo_id, repo_type, dry_run, token, validate)`

```python
def publish(
    envelope: Envelope,
    *,
    repo_id: str = DEFAULT_REPO_ID,
    repo_type: str = DEFAULT_REPO_TYPE,
    dry_run: bool = False,
    token: str | None = None,
    validate: bool = True,
) -> str
```

Validate, serialize, and upload the envelope to the HF dataset.
Returns the remote path where the shard was stored.

- When `dry_run=True` no network I/O occurs; the path is still returned.
- Reads `HF_TOKEN` from the environment unless `token` is provided explicitly.
- Set `validate=False` only if you have already called `validate_envelope()`.

#### `envelope_to_rows(envelope)`

```python
def envelope_to_rows(envelope: Envelope) -> list[dict[str, Any]]
```

Explode `envelope['results']` into one flat row per measurement.
Normalizes optional fields and tag-derived columns so PyArrow sees a
consistent schema across all shards.

#### `rows_to_parquet(rows)`

```python
def rows_to_parquet(rows: list[dict[str, Any]]) -> bytes
```

Convert flat rows to Parquet bytes. Raises `PublishError` if `rows` is empty.

#### `target_path(envelope, payload)`

```python
def target_path(envelope: Envelope, payload: bytes | None = None) -> str
```

Return the deterministic HF dataset path for this envelope.
Format: `data/run-<ts_slug>-<git_sha>-<suite>-<model_slug>-<payload_hash>.parquet`

The 8-char SHA-256 `payload_hash` content-addresses the shard and guarantees
no collisions even for retried runs.

#### `slugify(model)`

```python
def slugify(model: str) -> str
```

Filesystem-safe slug for a model identifier.
`"mlx-community/Qwen3.5-9B-MLX-4bit"` -> `"mlx-community-qwen3-5-9b-mlx-4bit"`

---

## `mlx_benchmarks.converters`

Transforms raw tool output into envelope v1.

### Protocol

#### `Converter`

```python
class Converter(Protocol):
    kind: str

    def build_envelope(
        self, raw: dict[str, Any], ctx: ConverterContext
    ) -> Envelope: ...
```

Any object with a `kind` string attribute and a `build_envelope()` method
satisfies this protocol. The two built-in converters are `LmEvalConverter`
(kind `"lm-eval"`) and `VllmConverter` (kind `"vllm"`).

### Dataclass

#### `ConverterContext`

```python
@dataclass(slots=True)
class ConverterContext:
    suite: str
    model: str
    git_sha: str
    trigger: str = "local"
    pr_number: int | None = None
    timestamp_override: str | None = None
    system: dict[str, Any] | None = None
    extra_tags: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None
```

Inputs a converter needs beyond the raw tool output itself.

- `system` -- if `None`, the converter calls `detect_system()` automatically.
- `source_path` -- path to the raw results file on disk; lets converters locate
  sibling artefacts (e.g. `samples_*.jsonl`) without extra arguments.

### Classes

#### `LmEvalConverter`

```python
class LmEvalConverter:
    kind = "lm-eval"

    def __init__(self, tokenizer_loader: TokenizerLoader | None = None) -> None
    def build_envelope(self, raw: dict[str, Any], ctx: ConverterContext) -> Envelope
```

Converts an lm-eval `results.json` dict into an envelope v1.
When `tokenizer_loader` is provided, computes per-task throughput metrics
(`prompt_tokens_per_second`, `decode_tokens_per_second`, `total_tokens_per_second`)
from the sibling `samples_*.jsonl` files. Degrades gracefully if the tokenizer
or samples file is unavailable.

#### `VllmConverter`

```python
class VllmConverter:
    kind = "vllm"

    def build_envelope(self, raw: dict[str, Any], ctx: ConverterContext) -> Envelope
```

Converts a `vllm benchmark_serving` JSON output dict into an envelope v1.
Extracts throughput (output tok/s, total tok/s, request/s) and latency
(TTFT, ITL, TPOT percentiles) metrics.

### Functions

#### `get_converter(kind)`

```python
def get_converter(kind: str) -> Converter
```

Return the converter registered for `kind`.
Raises `ValueError` for unknown kinds.

```python
from mlx_benchmarks.converters import get_converter

converter = get_converter("lm-eval")   # LmEvalConverter
converter = get_converter("vllm")      # VllmConverter
```

---

## `mlx_benchmarks.system`

Runtime detection of the `system` envelope fields.

### Functions

#### `detect_system()`

```python
@lru_cache(maxsize=1)
def detect_system() -> dict[str, Any]
```

Build a `system` dict reflecting the machine running the benchmark.
The result is cached for the lifetime of the process.

The schema-required fields `os`, `chip`, and `memory_gb` are always present --
detectors fall back to `"unknown"` or `0` rather than omitting them.
All other fields (`python_version`, `kernel`, package versions, `runner`) are
best-effort and only included when successfully detected.

```python
from mlx_benchmarks.system import detect_system

system = detect_system()
# {
#   "os": "macOS 26.4.1",
#   "chip": "Apple M4 Max",
#   "memory_gb": 128,
#   "kernel": "25.0.0",
#   "python_version": "3.11.9",
#   "mlx_version": "0.24.1",
#   "mlx_lm_version": "0.22.0",
# }
```

---

## Usage example

End-to-end: convert an lm-eval result, attach system info, validate, and
publish.

```python
import json
from mlx_benchmarks.converters import get_converter
from mlx_benchmarks.converters.base import ConverterContext
from mlx_benchmarks.publish import publish
from mlx_benchmarks.system import detect_system

with open("results_lm_eval.json") as f:
    raw = json.load(f)

ctx = ConverterContext(
    suite="reasoning",
    model="mlx-community/Qwen3.5-9B-MLX-4bit",
    git_sha="aaa3ff3",
    trigger="local",
    system=detect_system(),
)

envelope = get_converter("lm-eval").build_envelope(raw, ctx)

# Dry-run to verify the path without uploading:
path = publish(envelope, dry_run=True)
print(path)

# Real publish (requires HF_TOKEN in environment):
publish(envelope)
```
