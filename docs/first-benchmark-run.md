# First Benchmark Run: Step-by-Step Walkthrough

A practical guide to running your first MLX benchmark, from model setup through publishing results to the HF Space.

## Prerequisites

Before starting, ensure you have:

1. **macOS on Apple Silicon** (M1 or later) — the inference stack requires it.
2. **Python 3.11+** installed on your system.
3. **HuggingFace token** with write scope on the [`JacobPEvans/mlx-benchmarks`](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks) dataset (for publishing).
   - Generate one at <https://huggingface.co/settings/tokens> with "Write" permission.
4. A working **vllm-mlx + llama-swap inference stack** on `http://localhost:11434/v1` (typically set up via `nix-ai`).

## Step 1: Set Up the Repository

Clone and install mlx-benchmarks:

```bash
git clone https://github.com/JacobPEvans/mlx-benchmarks.git
cd mlx-benchmarks

# Install with uv (recommended)
uv sync
# Or with plain pip into a venv
python -m venv .venv && source .venv/bin/activate
pip install -e ".[viewer]"

# Install pre-commit hooks (optional but encouraged)
.venv/bin/pre-commit install

# Export your HF token (write scope required for publishing)
export HF_TOKEN=hf_your_write_token_here
```

Verify the installation:

```bash
.venv/bin/mlx-bench-publish --help
```

## Step 2: Verify Your Inference Stack

Before running a benchmark, confirm your model endpoint is up and responding:

```bash
# List available models
curl http://localhost:11434/v1/models

# Test a single request
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-community/Qwen3.5-9B-MLX-4bit",
    "messages": [{"role": "user", "content": "Say hello."}],
    "max_tokens": 32
  }'
```

If the endpoint is down or the model fails to load, troubleshoot your serving stack (vllm-mlx, llama-swap, memory usage) before proceeding.

## Step 3: Run lm-eval with a Small Limit

Start with `--limit 5` to verify the full pipeline without committing to a long run.

```bash
BASE="http://localhost:11434/v1/chat/completions"
MODEL="mlx-community/Qwen3.5-9B-MLX-4bit"

.venv/bin/lm_eval --model local-chat-completions \
  --model_args "base_url=$BASE,model=$MODEL,max_length=32768,timeout=3600" \
  --tasks gsm8k_cot_zeroshot \
  --batch_size 1 --num_fewshot 0 --limit 5 \
  --gen_kwargs "max_gen_toks=4096" \
  --apply_chat_template --fewshot_as_multiturn --log_samples \
  --output_path ./run-output
```

This runs only 5 samples (instead of the full task) and should finish in minutes. Output lands at
`./run-output/<model-slug>/results_*.json`.

**What is `max_gen_toks=4096`?** It caps the number of tokens the model may generate per sample. For math tasks like GSM8K, 4096 is generous; for short classification tasks you could lower it. Going too low causes truncated answers and wrong answers.

## Step 4: Inspect the Raw Results

After lm-eval completes, examine what the converter will receive:

```bash
python3 -c "
import json, glob
f = glob.glob('run-output/mlx-community--Qwen3.5-9B-MLX-4bit/results_*.json')[0]
data = json.load(open(f))
print('model:', data.get('model_name'))
print('tasks:', list(data.get('results', {}).keys()))
print('config keys:', list(data.get('config', {}).keys()))
"
```

Look for:
- `model_name` — your model ID
- `results` — per-task metrics (accuracy, exact_match, etc.)
- `config` — model_args and hyperparameters you used

## Step 5: Dry-Run Publish (Validate Only, No Upload)

Convert the raw lm-eval output to an mlx-benchmarks envelope and validate it against `schema.json`
without touching the network:

```bash
FILE="./run-output/mlx-community--Qwen3.5-9B-MLX-4bit/results_gsm8k_cot_zeroshot_*.json"

.venv/bin/mlx-bench-publish $FILE \
  --kind lm-eval \
  --suite reasoning \
  --dry-run
```

Expected output:

```
[INFO] built envelope with N results for model=mlx-community/Qwen3.5-9B-MLX-4bit suite=reasoning
[INFO] planned -> data/run-<timestamp>-<git_sha>-reasoning-mlx-community--qwen3.5-9b-mlx-4bit.parquet
```

If validation fails with "additionalProperties: false", inspect the error message and check
`docs/schema.md` for the allowed envelope fields.

## Step 6: Publish to HuggingFace

Once the dry-run passes, publish for real by removing the `--dry-run` flag:

```bash
FILE="./run-output/mlx-community--Qwen3.5-9B-MLX-4bit/results_gsm8k_cot_zeroshot_*.json"

.venv/bin/mlx-bench-publish $FILE \
  --kind lm-eval \
  --suite reasoning
```

Expected output:

```
[INFO] published -> data/run-<timestamp>-<git_sha>-reasoning-mlx-community--qwen3.5-9b-mlx-4bit.parquet
```

The shard is now live on the [HuggingFace dataset](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks).
Filenames are content-addressed (include timestamp and git SHA), so re-publishing the same
envelope writes a new shard rather than overwriting.

## Step 7: View Results in the HF Space

Open the live Space:

<https://huggingface.co/spaces/JacobPEvans/mlx-benchmarks-viewer>

The viewer auto-refreshes every few minutes. If your result does not appear immediately, wait
2–3 minutes and refresh. Filter by **Model**, **Suite** (e.g. `reasoning`), and **Metric**
(e.g. `exact_match_flexible` for GSM8K).

To run the viewer locally:

```bash
cd space
pip install -r requirements.txt
python app.py
# open http://localhost:7860
```

## Common Pitfalls

### Model not found on the inference endpoint

**Symptom:** `curl http://localhost:11434/v1/models` does not list your model, or lm-eval gets 404s.

**Fix:**
1. Confirm the inference server is running: `curl http://localhost:11434/v1/models`
2. Check that llama-swap has the model loaded (model ID must match exactly — case-sensitive).
3. If using `llama-swap`, switch to the model before running benchmarks.

### lm-eval hangs or times out

**Symptom:** The run freezes after a few samples, or you see timeout errors.

**Fix:**
1. Use `--limit 2` to isolate whether the issue is model latency or OOM.
2. Check memory pressure — if the Mac is swapping, the model is too large for your RAM.
3. Tail the vllm-mlx process logs for errors or warnings.
4. See `docs/quick-reset.md` to reclaim memory without rebooting.

### `base_url` must end in `/v1/chat/completions`

**Symptom:** lm-eval connects but returns empty responses or errors on every sample.

**Fix:** Pass the full completions path, not the base:

```bash
# Wrong
--model_args "base_url=http://localhost:11434/v1,..."

# Correct
--model_args "base_url=http://localhost:11434/v1/chat/completions,..."
```

### Envelope validation fails with "additionalProperties: false"

**Symptom:** `mlx-bench-publish` rejects the envelope with a schema validation error.

**Fix:**
1. Check the error for the unknown field name.
2. Verify the field is spelled correctly and listed in `docs/schema.md`.
3. Re-run with `--log-format json` to see the full envelope being validated.

### HF token missing or wrong scope

**Symptom:** Publishing fails with 401 (Unauthorized) or 403 (Forbidden).

**Fix:**
1. Verify the token is set: `echo $HF_TOKEN`
2. Generate a new token at <https://huggingface.co/settings/tokens> with **Write** permission.
3. Re-export and retry: `export HF_TOKEN=hf_your_new_token_here`

Never commit your token to git — only export it in your shell or a `.envrc.local` (gitignored).

### Model not in catalog

**Symptom:** `mlx-bench-publish` fails with "model not in allowed catalog" or similar.

**Fix:** The model field is free-form string; check that you are passing `--model` or that the
converter is pulling it correctly from the lm-eval results JSON. See `docs/schema.md` for the
`model` field constraints.

### Results do not appear in the HF Space viewer

**Symptom:** Publish succeeded but the shard is missing from the viewer after 5+ minutes.

**Fix:**
1. Confirm the shard exists on the [HF dataset Files tab](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks).
2. Hard-refresh the Space (Cmd+Shift+R on macOS), wait 2–3 minutes, and try again.
3. Check the Space [Logs tab](https://huggingface.co/spaces/JacobPEvans/mlx-benchmarks-viewer?tab=logs) for viewer errors.

## Next Steps

- **Run a full suite:** Remove `--limit` to benchmark the entire task (may take hours).
- **Benchmark other models:** Repeat Steps 2–7 with a different model ID.
- **Try other suites:** See `configs/LAYOUT.md` for available suites (`coding`, `throughput`, etc.).
- **Read more:** `docs/schema.md` (envelope spec), `docs/faq.md` (ops troubleshooting), `CONTRIBUTING.md` (developer workflow).
