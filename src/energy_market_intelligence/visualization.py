"""Consistent Plotly figures for pipeline exports and Streamlit pages."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

NORTHSTAR_BLUE = "#1F4E79"
ACCENT_TEAL = "#2A7F8E"
NEGATIVE_RED = "#B84A4A"
GRID_COLOR = "#E5E7EB"


def apply_business_theme(figure: go.Figure, *, y_title: str | None = None) -> go.Figure:
    """Apply restrained, readable styling shared across static and interactive charts."""

    figure.update_layout(
        template="plotly_white",
        font={"family": "Arial", "size": 13, "color": "#243447"},
        title={"x": 0.01, "xanchor": "left", "font": {"size": 19}},
        margin={"l": 65, "r": 30, "t": 70, "b": 60},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        hoverlabel={"namelength": -1},
    )
    figure.update_xaxes(showgrid=False, title=None)
    figure.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title=y_title)
    return figure


def market_share_trend_figure(frame: pd.DataFrame) -> go.Figure:
    """Show Northstar's monthly national market-share trajectory."""

    figure = px.line(
        frame,
        x="date",
        y="northstar_market_share",
        title="Northstar market share trend",
        markers=True,
    )
    figure.update_traces(line={"color": NORTHSTAR_BLUE, "width": 3}, marker={"size": 5})
    figure.update_yaxes(tickformat=".1%")
    return apply_business_theme(figure, y_title="Market share")


def opportunity_matrix_figure(frame: pd.DataFrame) -> go.Figure:
    """Compare regional growth, Northstar share, scale, and opportunity score."""

    chart_data = frame.copy()
    if "opportunity_rank" in chart_data:
        chart_data["display_label"] = chart_data["region_name"].where(
            chart_data["opportunity_rank"] <= 3, ""
        )
    else:
        chart_data["display_label"] = ""
    figure = px.scatter(
        chart_data,
        x="northstar_share",
        y="market_growth",
        size="market_volume",
        color="opportunity_score",
        hover_name="region_name",
        text="display_label",
        color_continuous_scale="Blues",
        size_max=42,
        title="Regional opportunity matrix",
        labels={"opportunity_score": "Opportunity score"},
    )
    figure.update_traces(textposition="top center", textfont={"size": 10})
    figure.update_xaxes(tickformat=".1%")
    figure.update_yaxes(tickformat=".1%")
    return apply_business_theme(figure, y_title="Market growth (YoY)")


def competitor_change_figure(frame: pd.DataFrame) -> go.Figure:
    """Rank annual company-share movement in percentage points."""

    ordered = frame.sort_values("share_change_pp")
    colors = [ACCENT_TEAL if value >= 0 else NEGATIVE_RED for value in ordered["share_change_pp"]]
    figure = go.Figure(
        go.Bar(
            x=ordered["share_change_pp"],
            y=ordered["company_name"],
            orientation="h",
            marker_color=colors,
            text=ordered["share_change_pp"].map(lambda value: f"{value:+.2f} pp"),
            textposition="outside",
            hovertemplate="%{y}<br>Share change: %{x:+.2f} pp<extra></extra>",
        )
    )
    figure.update_layout(title="Company market-share change: latest 12 months vs prior 12")
    return apply_business_theme(figure, y_title=None)


def gross_margin_trend_figure(frame: pd.DataFrame) -> go.Figure:
    """Show Northstar's monthly aggregated gross-margin trend."""

    monthly = frame.groupby("date", as_index=False).agg(
        gross_profit=("gross_profit", "sum"), revenue=("revenue", "sum")
    )
    monthly["gross_margin_pct"] = monthly["gross_profit"] / monthly["revenue"]
    figure = px.line(
        monthly,
        x="date",
        y="gross_margin_pct",
        title="Northstar gross-margin trend",
        markers=True,
    )
    figure.update_traces(line={"color": ACCENT_TEAL, "width": 3}, marker={"size": 5})
    figure.update_yaxes(tickformat=".1%")
    return apply_business_theme(figure, y_title="Gross margin")


def profit_bridge_figure(bridge: pd.DataFrame) -> go.Figure:
    """Render the revenue-change identity as a volume/price/interaction waterfall."""

    values = [
        bridge["volume_effect"].sum(),
        bridge["price_effect"].sum(),
        bridge["interaction_effect"].sum(),
        bridge["total_revenue_change"].sum(),
    ]
    figure = go.Figure(
        go.Waterfall(
            x=["Volume effect", "Price effect", "Interaction", "Revenue change"],
            y=values,
            measure=["relative", "relative", "relative", "total"],
            increasing={"marker": {"color": ACCENT_TEAL}},
            decreasing={"marker": {"color": NEGATIVE_RED}},
            totals={"marker": {"color": NORTHSTAR_BLUE}},
            connector={"line": {"color": "#9CA3AF"}},
            hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(title="Northstar revenue change bridge: latest month vs prior year")
    return apply_business_theme(figure, y_title="Synthetic currency units")


def write_png(figure: go.Figure, path: Path) -> None:
    """Write a consistent portfolio image with an actionable failure message."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        figure.write_image(path, width=1200, height=680, scale=1.5)
    except Exception as exc:  # pragma: no cover - exercised only when renderer is unavailable
        raise RuntimeError(
            "Static chart export failed. Install the project dev dependencies, including Kaleido."
        ) from exc
