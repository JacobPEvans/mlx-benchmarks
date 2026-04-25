"""
MLX Benchmarks Viewer — Gradio Space

Reads all parquet shards from JacobPEvans/mlx-benchmarks and renders
interactive comparison charts. Auto-refreshes data every 10 minutes.

Deploy to HF Spaces (SDK: gradio, Python 3.11+).
"""

import re
import time
from threading import Lock

import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from huggingface_hub import HfFileSystem

DATASET = "datasets/JacobPEvans/mlx-benchmarks"
CACHE_TTL = 600  # seconds
EXPECTED_COLUMNS = ["timestamp", "suite", "name", "metric", "model", "value"]
CSS = """
#title { text-align: center; margin-bottom: 4px; }
#subtitle { text-align: center; color: #666; margin-bottom: 20px; }
"""


# ── Data loading ──────────────────────────────────────────────────────────────

_cache: tuple[float, pd.DataFrame] | None = None
_cache_lock = Lock()


def empty_data() -> pd.DataFrame:
    return pd.DataFrame(columns=[*EXPECTED_COLUMNS, "model_short"])


def load_data() -> pd.DataFrame:
    global _cache
    with _cache_lock:
        if _cache and time.time() - _cache[0] < CACHE_TTL:
            return _cache[1]

        fs = HfFileSystem()
        try:
            paths = sorted(f"hf://{p}" for p in fs.glob(f"{DATASET}/data/*.parquet"))
        except (FileNotFoundError, OSError):
            paths = []

        if not paths:
            df = empty_data()
            _cache = (time.time(), df)
            return df

        df = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["model_short"] = df["model"].apply(short_model)
        _cache = (time.time(), df)
        return df


def short_model(name: str) -> str:
    """Strip common prefixes for axis labels."""
    name = re.sub(r"^mlx-community/", "", name)
    name = re.sub(r"^openrouter/openai/", "openrouter/", name)
    return name


# ── Chart builders ────────────────────────────────────────────────────────────


def bar_chart(df: pd.DataFrame, suite: str, task: str, metric: str) -> go.Figure:
    """Latest-run bar chart: one bar per model, sorted by score."""
    sub = df[(df["suite"] == suite) & (df["name"] == task) & (df["metric"] == metric)].copy()
    if sub.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data for this selection",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font_size=18,
        )
        return fig

    # Keep only the latest run per model
    sub = sub.sort_values("timestamp").groupby("model", as_index=False).last()
    sub["label"] = sub["model_short"]
    sub = sub.sort_values("value", ascending=True)
    value_max = sub["value"].max()
    axis_max = max(1.0, float(value_max) * 1.15) if pd.notna(value_max) else 1.0

    fig = px.bar(
        sub,
        x="value",
        y="label",
        orientation="h",
        text=sub["value"].map("{:.3f}".format),
        color="value",
        color_continuous_scale="Blues",
        labels={"value": metric, "label": "Model"},
        title=f"{task} — {metric}  ({suite})",
    )
    fig.update_traces(textposition="outside")
    fig.update_coloraxes(showscale=False)
    fig.update_layout(
        height=max(350, len(sub) * 44),
        margin={"l": 220, "r": 60, "t": 60, "b": 40},
        yaxis_title="",
        xaxis_range=[0, axis_max],
        font_size=13,
    )
    return fig


def trend_chart(df: pd.DataFrame, suite: str, task: str, metric: str, models: list[str]) -> go.Figure:
    """Score-over-time line chart for selected models."""
    sub = df[
        (df["suite"] == suite)
        & (df["name"] == task)
        & (df["metric"] == metric)
        & (df["model_short"].isin(models))
    ].copy()
    if sub.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data for this selection",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font_size=18,
        )
        return fig

    fig = px.line(
        sub.sort_values("timestamp"),
        x="timestamp",
        y="value",
        color="model_short",
        markers=True,
        labels={"value": metric, "timestamp": "Run time", "model_short": "Model"},
        title=f"{task} — {metric} over time",
    )
    fig.update_layout(height=420, font_size=13, legend_title="")
    return fig


def summary_table(df: pd.DataFrame, suite: str, metric: str) -> pd.DataFrame:
    """Pivot table: models x tasks, latest run only."""
    sub = df[(df["suite"] == suite) & (df["metric"] == metric)].copy()
    if sub.empty:
        return pd.DataFrame({"(no data)": []})

    sub = sub.sort_values("timestamp").groupby(["model", "name"], as_index=False).last()
    pivot = sub.pivot(index="model_short", columns="name", values="value")
    pivot = pivot.round(4).reset_index().rename(columns={"model_short": "Model"})
    return pivot


# ── Gradio UI ─────────────────────────────────────────────────────────────────


def build_ui():
    df = load_data()

    suites = sorted(df["suite"].dropna().unique().tolist()) if not df.empty else ["reasoning"]
    tasks = sorted(df["name"].dropna().unique().tolist()) if not df.empty else []
    metrics = sorted(df["metric"].dropna().unique().tolist()) if not df.empty else []
    models = sorted(df["model"].dropna().unique().tolist()) if not df.empty else []
    model_labels = [short_model(m) for m in models]

    default_suite = "reasoning" if "reasoning" in suites else (suites[0] if suites else "reasoning")
    default_metric = (
        "exact_match_flexible" if "exact_match_flexible" in metrics else (metrics[0] if metrics else None)
    )

    def filtered_tasks(suite):
        d = load_data()
        t = sorted(d[d["suite"] == suite]["name"].dropna().unique().tolist()) if not d.empty else []
        return gr.Dropdown(choices=t, value=t[0] if t else None)

    def filtered_metrics(suite):
        d = load_data()
        m = sorted(d[d["suite"] == suite]["metric"].dropna().unique().tolist()) if not d.empty else []
        return gr.Dropdown(
            choices=m, value="exact_match_flexible" if "exact_match_flexible" in m else (m[0] if m else None)
        )

    def update_bar(suite, task, metric):
        return bar_chart(load_data(), suite, task, metric)

    def update_trend(suite, task, metric, selected_models):
        return trend_chart(load_data(), suite, task, metric, selected_models or model_labels)

    def update_table(suite, metric):
        return summary_table(load_data(), suite, metric)

    def refresh():
        global _cache
        with _cache_lock:
            _cache = None
        d = load_data()
        new_suites = sorted(d["suite"].dropna().unique().tolist()) if not d.empty else ["reasoning"]
        new_tasks = sorted(d["name"].dropna().unique().tolist()) if not d.empty else []
        new_metrics = sorted(d["metric"].dropna().unique().tolist()) if not d.empty else []
        new_models = sorted(d["model"].dropna().unique().tolist()) if not d.empty else []
        new_model_labels = [short_model(m) for m in new_models]
        return (
            gr.Dropdown(choices=new_suites, value=new_suites[0] if new_suites else None),
            gr.Dropdown(choices=new_tasks, value=new_tasks[0] if new_tasks else None),
            gr.Dropdown(choices=new_metrics, value=new_metrics[0] if new_metrics else None),
            gr.CheckboxGroup(choices=new_model_labels, value=new_model_labels[:6]),
            f"Loaded {len(d)} rows from {len(d['model'].unique()) if not d.empty else 0} models",
        )

    with gr.Blocks(title="MLX Benchmarks") as demo:
        gr.Markdown("# MLX Benchmarks Viewer", elem_id="title")
        gr.Markdown(
            "Compare local MLX models and cloud endpoints across coding and reasoning benchmarks.  \n"
            "Data: [JacobPEvans/mlx-benchmarks](https://huggingface.co/datasets/JacobPEvans/mlx-benchmarks)",
            elem_id="subtitle",
        )

        with gr.Row():
            suite_dd = gr.Dropdown(choices=suites, value=default_suite, label="Suite")
            task_dd = gr.Dropdown(choices=tasks, value=tasks[0] if tasks else None, label="Task")
            metric_dd = gr.Dropdown(choices=metrics, value=default_metric, label="Metric")
            refresh_btn = gr.Button("↻ Refresh data", scale=0)

        status = gr.Markdown(
            f"Loaded {len(df)} rows from {df['model'].nunique() if not df.empty else 0} models."
        )

        with gr.Tabs():
            with gr.Tab("Bar chart — latest run"):
                bar_plot = gr.Plot(
                    value=bar_chart(df, default_suite, tasks[0] if tasks else "", default_metric)
                )

            with gr.Tab("Trend — over time"):
                model_select = gr.CheckboxGroup(
                    choices=model_labels,
                    value=model_labels[:6],
                    label="Models to show",
                )
                trend_plot = gr.Plot()

            with gr.Tab("Summary table"):
                table_out = gr.DataFrame(
                    value=summary_table(df, default_suite, default_metric),
                    interactive=False,
                )

        # Wire up events
        suite_dd.change(filtered_tasks, [suite_dd], [task_dd])
        suite_dd.change(filtered_metrics, [suite_dd], [metric_dd])

        for inp in [suite_dd, task_dd, metric_dd]:
            inp.change(update_bar, [suite_dd, task_dd, metric_dd], [bar_plot])
            inp.change(update_table, [suite_dd, metric_dd], [table_out])

        for inp in [suite_dd, task_dd, metric_dd, model_select]:
            inp.change(update_trend, [suite_dd, task_dd, metric_dd, model_select], [trend_plot])

        refresh_btn.click(
            refresh,
            outputs=[suite_dd, task_dd, metric_dd, model_select, status],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(css=CSS)
