# Context campaign protocol

`scripts/run-context-campaign.py` measures context sensitivity without making
a benchmark manifest a second model catalog. The manifest is an ephemeral,
generated input: `scripts/generate-context-inventory.py` intersects evaluated
serving-window limits with the endpoint's live `/v1/models` response.

The runner owns only the protocol defaults selected for this campaign:
32k, 64k, 128k, and 192k prompt targets; a 512-token output reservation; and
the pair/repetition plan. The generated inventory owns model identity,
enabled status, profile identity, and `window_limit_tokens`.

```json
{
  "campaign_id": "context-20260828-a",
  "output_root": "~/bench-runs",
  "defaults": {
    "targets": [32000, 64000, 128000, 192000],
    "configured_windows": [32768, 65536, 131072, 196608],
    "output_tokens": 512,
    "repeats": 4,
    "concurrency": 1
  },
  "profiles": [
    {
      "model": "<physical-model-id-from-evaluated-config>",
      "window_limit_tokens": 131072
    }
  ]
}
```

Profile `id` is optional and defaults to the physical model basename. Disabled
profiles are omitted by the generator (or marked `"enabled": false`). A cell
whose configured window cannot admit prompt target plus reservation is recorded
as `not_applicable`; an absent live model is `unsupported`. Neither produces a
synthetic speed value.

Generate an inventory, then run a dry plan before acquiring an exclusive
benchmark lease. `windows.json` is the evaluated physical-model-id to
context-window map; it is not maintained in this repository.

```sh
uv run scripts/generate-context-inventory.py \
  --windows-json /path/to/evaluated-windows.json \
  --proxy-config /path/to/generated-proxy-config.json \
  --campaign-id context-20260828-a \
  --output /tmp/context-campaign.json
```

```sh
uv run scripts/run-context-campaign.py /path/to/generated-inventory.json --dry-run
```

The non-dry run queries the live inventory once, writes only below
`output_root`, invokes the established throughput probe, and invokes the
publisher in `--dry-run` mode. The probe rejects a cell when the server does
not report the expected prompt token count (within the declared tolerance), or
when actual prompt plus the reserved output exceeds the selected window.

When `--proxy-config` is supplied, the generator parses each worker's current
`--max-tokens` admission cap and takes the lower of that cap and the evaluated
catalog window. This is deliberate: a catalog window is not a live capacity
claim. The manifest preserves both dimensions so a blocked 32k cell is
diagnostic rather than an invented benchmark failure.

## What every successful row means

The envelope records these dimensions independently:

| Dimension | Source | Meaning |
| --- | --- | --- |
| configured window | evaluated inventory | Admission limit selected for this cell. |
| requested prompt | campaign target | Predeclared comparable target. |
| actual prompt | server usage | Value used to accept or reject the cell. |
| output reservation | campaign protocol | Capacity held back for a normal completion. |
| model/catalog/proxy/worker maxima | generated inventory when available | Distinct limits; never substitute one for another. |

The raw result also preserves cache-busting, completion finish reasons, and
the campaign/cell identity. A long prompt that ends before the required normal
completion is useful for prefill and TTFT evidence, but not a comparable decode
throughput claim.

## Publication and interpretation

Only `success` cells with valid adjacent pairs can affect a ranking or maturity.
The other statuses (`failed`, `capacity_gated`, `unsupported`, `aborted`, and
`not_applicable`) remain durable diagnostics. Preserve historical evidence as
separate immutable rows; do not regenerate, relabel, or overwrite it when a
new campaign runs.

This protocol establishes isolated evidence only. Under-load evidence is a
separate campaign with the production service left live.
