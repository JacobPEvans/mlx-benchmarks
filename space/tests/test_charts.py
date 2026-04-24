"""Chart builders return Plotly figures, never raise, even on empty data."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

SPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPACE_ROOT))

import app  # noqa: E402  — import after sys.path adjustment

SAMPLE_ROWS = [
    {
        "timestamp": "2026-04-24T18:30:00Z",
        "suite": "reasoning",
        "name": "gsm8k_cot_zeroshot",
        "metric": "exact_match_flexible",
        "model": "mlx-community/Qwen3.5-9B-MLX-4bit",
        "value": 0.8,
    },
    {
        "timestamp": "2026-04-24T19:00:00Z",
        "suite": "reasoning",
        "name": "gsm8k_cot_zeroshot",
        "metric": "exact_match_flexible",
        "model": "mlx-community/gemma-4-e4b-it-4bit",
        "value": 0.6,
    },
]


def _sample_df() -> pd.DataFrame:
    df = pd.DataFrame(SAMPLE_ROWS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["model_short"] = df["model"].apply(app.short_model)
    return df


def test_empty_data_returns_annotated_figure() -> None:
    fig = app.bar_chart(app.empty_data(), "reasoning", "gsm8k_cot_zeroshot", "exact_match_flexible")
    assert isinstance(fig, go.Figure)
    # Annotation present when no data
    assert len(fig.layout.annotations) == 1
    assert "No data" in fig.layout.annotations[0].text


def test_bar_chart_renders_with_rows() -> None:
    df = _sample_df()
    fig = app.bar_chart(df, "reasoning", "gsm8k_cot_zeroshot", "exact_match_flexible")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1  # single trace
    # Two models => two bars
    bar = fig.data[0]
    assert len(bar.y) == 2


def test_trend_chart_renders_with_rows() -> None:
    df = _sample_df()
    fig = app.trend_chart(
        df,
        "reasoning",
        "gsm8k_cot_zeroshot",
        "exact_match_flexible",
        models=[app.short_model(m) for m in df["model"].unique()],
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


def test_summary_table_returns_dataframe() -> None:
    df = _sample_df()
    pivot = app.summary_table(df, "reasoning", "exact_match_flexible")
    assert isinstance(pivot, pd.DataFrame)
    assert "Model" in pivot.columns or pivot.empty


def test_short_model_strips_common_prefixes() -> None:
    assert app.short_model("mlx-community/Qwen3.5-9B-MLX-4bit") == "Qwen3.5-9B-MLX-4bit"
    assert app.short_model("openrouter/openai/gpt-5-mini") == "openrouter/gpt-5-mini"
    assert app.short_model("plain-name") == "plain-name"
