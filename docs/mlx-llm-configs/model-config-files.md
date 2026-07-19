# Model config files and the parity checklist

What a model ships in its repo, how `vllm-mlx` consumes it, and the checklist
to run before serving or benchmarking so the serve command matches what the
model was built for.

## Files a model may ship

- `config.json` — architecture and quantization. Watch for:
  - `quantization` / `quantization_config` — weight quant (bits, group_size,
    per-tensor overrides).
  - `mtp_file`, `mtp_tensor_count`, `mtp_policy`, `mtp_num_hidden_layers` — the
    model has Multi-Token Prediction heads for speculative decoding. Presence
    means the model is designed to run with `--enable-mtp`.
- `kv_config.json` — per-layer KV cache quantization plan (layer_idx, bits,
  group_size). Presence means the model is a KV-quant build; serving without
  KV quant is serving a different, heavier model than intended.
- `generation_config.json` — the author's recommended sampling defaults
  (temperature, top_p, top_k, repetition_penalty, presence_penalty). Match the
  serve `--default-*` flags to these rather than imposing house values.
- MTP weights — the actual speculative-decoding tensors. May be a top-level
  `mtp.safetensors` or referenced by `mtp_file` at a subpath. Must be present
  in the served snapshot/revision, or MTP silently does not load.
- Multimodal configs (`preprocessor_config.json`, `processor_config.json`) —
  the model is vision-capable; the loader may report it as a VLM.

## Worked example: OptiQ vs plain 4-bit (Qwen3.6-35B-A3B)

`mlx-community/Qwen3.6-35B-A3B-OptiQ-4bit` ships:

- `config.json`: `mtp_file`, `mtp_tensor_count = 37`,
  `mtp_policy = optiq-int4-prequantized-gs64`, `mtp_num_hidden_layers = 1`.
- `kv_config.json`: per-layer KV quant, layers at 4-bit and 8-bit, group_size
  64 (e.g. layer 3 → 4-bit, layer 7 → 8-bit, ...).
- `generation_config.json`: temperature 0.7, top_k 20, top_p 0.8,
  repetition_penalty 1.0, presence_penalty 1.5.

So OptiQ is defined by two features: MTP speculative decoding and mixed 4/8-bit
KV-cache quantization. To serve it as intended the command needs, at minimum:

- `--enable-mtp` (plus `--mtp-num-draft-tokens`) — and the served revision must
  actually contain the MTP weights.
- `--kv-cache-quantization` with bits/group-size consistent with
  `kv_config.json`.
- `--default-*` sampling aligned to `generation_config.json`.
- `--max-kv-size >= 32768` (reasoning model — avoid evicting the think block).

`mlx-community/Qwen3.6-35B-A3B-4bit` (plain) ships only `quantization` keys —
no `kv_config.json`, no `mtp_*`. Served with plain flags it is roughly correct.
This asymmetry matters: comparing plain-vanilla (served right) against OptiQ
(served without its features) is not a model comparison, it is a config
mismatch. See `learnings.md` (2026-07-19).

## Pre-serve parity checklist

Run this before benchmarking any model or trusting a serving config.

1. List the snapshot files actually on disk for the exact revision you serve.
   Confirm any `mtp.safetensors` / MTP weights referenced by `config.json` are
   present. A missing-MTP warning in the serve log means MTP did not load.
2. If `config.json` has `mtp_*` keys → the serve command must pass
   `--enable-mtp`. If not, you are leaving the model's speculative decoding off.
3. If `kv_config.json` exists → the serve command must enable KV quant
   (`--kv-cache-quantization` and matching bits/group-size). If not, you are
   serving full-precision KV, not the KV-quant model.
4. Compare `generation_config.json` to the serve `--default-*` flags and any
   proxy/router param injection. Note divergences; they change output
   behavior and sometimes throughput.
5. For reasoning models, confirm `--reasoning-parser` is set and
   `--max-kv-size` is large enough (>= 32768) to hold the think block.
6. Confirm the serve log's startup lines reflect all of the above (KV quant
   enabled, MTP injected, reasoning parser enabled). Do not assume a flag took
   effect — verify it in the log.

## How to inspect a model's files

On the serving host, for a cached HF model:

```bash
snap=$(ls -d "$HF_HOME"/hub/models--ORG--NAME/snapshots/*/ | head -1)
ls "$snap"                        # what shipped in this revision
cat "$snap/kv_config.json"        # KV-quant plan, if present
python3 -c 'import json; c=json.load(open("'"$snap"'config.json"));
print({k: c[k] for k in c if "mtp" in k or "quant" in k})'
cat "$snap/generation_config.json"
```

Replace `ORG--NAME` with the model repo (e.g.
`mlx-community--Qwen3.6-35B-A3B-OptiQ-4bit`) and confirm you inspect the same
revision the server actually loads.
