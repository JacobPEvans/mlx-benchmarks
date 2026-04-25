---
title: MLX Benchmarks Viewer
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "6.13.0"
app_file: app.py
python_version: "3.11"
pinned: true
license: apache-2.0
short_description: Interactive viewer for the MLX Benchmarks dataset
tags:
  - benchmarks
  - mlx
  - apple-silicon
  - lm-eval
  - visualization
models:
  - mlx-community/Qwen3.5-9B-MLX-4bit
datasets:
  - JacobPEvans/mlx-benchmarks
---

# MLX Benchmarks Viewer

Interactive Gradio viewer for the
[`JacobPEvans/mlx-benchmarks`](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)
dataset — a collection of benchmark runs of MLX-quantized and locally-hosted
LLMs on Apple Silicon, all serialized under the envelope v1 schema.

## Installation

Requires Python 3.11+.

```sh
cd space
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Launch the viewer locally:

```sh
python app.py
```

Gradio prints a local URL (default `http://127.0.0.1:7860`). The app pulls all
`data/*.parquet` shards from the HF dataset, caches them for 10 minutes, and
offers three tabs:

- **Bar chart — latest run** — one bar per model for a given (suite, task, metric)
- **Trend — over time** — score trajectory per model across runs
- **Summary table** — pivot of models x tasks for the selected (suite, metric)

Hit **Refresh data** to invalidate the cache manually.

## Deployment

This Space is synced automatically from the
[JacobPEvans/mlx-benchmarks](https://github.com/JacobPEvans/mlx-benchmarks)
GitHub repository via the `deploy-space.yml` workflow on every `main` push
that touches `space/`.

## Contributing

Issues and PRs live in the upstream
[GitHub repo](https://github.com/JacobPEvans/mlx-benchmarks). See the
repository `CONTRIBUTING.md` for the full developer workflow.

## API

The viewer is a Gradio UI — it has no stable programmatic API. To query the
underlying data yourself, read the HF dataset directly:

```python
import pandas as pd
from huggingface_hub import HfFileSystem

fs = HfFileSystem()
paths = fs.glob("datasets/JacobPEvans/mlx-benchmarks/data/*.parquet")
df = pd.concat([pd.read_parquet(f"hf://{p}") for p in paths], ignore_index=True)
```

## License

Apache-2.0. See [LICENSE](https://github.com/JacobPEvans/mlx-benchmarks/blob/main/LICENSE).

## Source

Full source, tests, and developer docs:
<https://github.com/JacobPEvans/mlx-benchmarks>
