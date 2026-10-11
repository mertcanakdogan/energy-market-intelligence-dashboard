"""Consistent Plotly figures for pipeline exports and Streamlit pages."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from energy_market_intelligence.localization import format_number
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY

TL_AXIS = "mn TL (sabit 2025 fiyatlarıyla)"
BRAND_BLUE = "#1F4E79"
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
        separators=",.",  # Turkish: comma for decimals, dot for thousands
    )
    figure.update_xaxes(showgrid=False, title=None)
    figure.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title=y_title)
    return figure


def market_share_trend_figure(frame: pd.DataFrame) -> go.Figure:
    """Show the focus company's monthly national market-share trajectory."""

    figure = px.line(
        frame,
        x="date",
        y="focus_market_share",
        title=f"{FOCUS_COMPANY}: aylık pazar payı",
        markers=True,
    )
    figure.update_traces(line={"color": BRAND_BLUE, "width": 3}, marker={"size": 5})
    figure.update_yaxes(tickformat=".1%")
    figure.update_traces(hovertemplate="%{x|%b %Y}: %{y:.1%}<extra></extra>")
    return apply_business_theme(figure, y_title="Pazar payı")


def opportunity_matrix_figure(frame: pd.DataFrame) -> go.Figure:
    """Compare regional growth, focus-company share, scale, and opportunity score."""

    chart_data = frame.copy()
    if "opportunity_rank" in chart_data:
        chart_data["display_label"] = chart_data["region_name"].where(
            chart_data["opportunity_rank"] <= 3, ""
        )
    else:
        chart_data["display_label"] = ""
    figure = px.scatter(
        chart_data,
        x="focus_share",
        y="market_growth",
        size="market_volume",
        color="opportunity_score",
        hover_name="region_name",
        text="display_label",
        color_continuous_scale="Blues",
        size_max=42,
        title="Bölgesel fırsat matrisi (balon büyüklüğü = pazar hacmi)",
        labels={
            "opportunity_score": "Fırsat skoru",
            "focus_share": "Şirketin pazar payı",
            "market_growth": "Pazar büyümesi (yıllık)",
            "market_volume": "Pazar hacmi (MWh)",
            "region_name": "Bölge",
        },
    )
    figure.update_traces(textposition="top center", textfont={"size": 10})
    figure.update_xaxes(tickformat=".0%")
    figure.update_yaxes(tickformat=".0%")
    apply_business_theme(figure, y_title="Pazar büyümesi (son 12 ay / önceki 12 ay)")
    figure.update_xaxes(title="Şirketin pazar payı (son 12 ay)")
    return figure


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
            text=ordered["share_change_pp"].map(
                lambda value: f"{format_number(value, 2, signed=True)} puan"
            ),
            textposition="outside",
            hovertemplate="%{y}<br>Pay değişimi: %{x:+.2f} puan<extra></extra>",
        )
    )
    figure.update_layout(title="Şirketlerin pazar payı değişimi: son 12 ay / önceki 12 ay")
    apply_business_theme(figure, y_title=None)
    figure.update_xaxes(title="Pazar payı değişimi (yüzde puan)")
    return figure


def gross_margin_trend_figure(frame: pd.DataFrame) -> go.Figure:
    """Show the focus company's monthly aggregated gross-margin trend."""

    monthly = frame.groupby("date", as_index=False).agg(
        gross_profit=("gross_profit", "sum"), revenue=("revenue", "sum")
    )
    monthly["gross_margin_pct"] = monthly["gross_profit"] / monthly["revenue"]
    figure = px.line(
        monthly,
        x="date",
        y="gross_margin_pct",
        title=f"{FOCUS_COMPANY}: aylık brüt marj",
        markers=True,
    )
    figure.update_traces(line={"color": ACCENT_TEAL, "width": 3}, marker={"size": 5})
    figure.update_yaxes(tickformat=".1%")
    figure.update_traces(hovertemplate="%{x|%b %Y}: %{y:.1%}<extra></extra>")
    return apply_business_theme(figure, y_title="Brüt marj")


def profit_bridge_figure(bridge: pd.DataFrame) -> go.Figure:
    """Render the revenue-change identity as a volume/price/interaction waterfall."""

    values = [
        bridge["volume_effect"].sum() / 1e6,
        bridge["price_effect"].sum() / 1e6,
        bridge["interaction_effect"].sum() / 1e6,
        bridge["total_revenue_change"].sum() / 1e6,
    ]
    figure = go.Figure(
        go.Waterfall(
            x=["Hacim etkisi", "Fiyat etkisi", "Etkileşim", "Ciro değişimi"],
            y=values,
            measure=["relative", "relative", "relative", "total"],
            text=[format_number(value, 1, signed=True) for value in values],
            textposition="outside",
            increasing={"marker": {"color": ACCENT_TEAL}},
            decreasing={"marker": {"color": NEGATIVE_RED}},
            totals={"marker": {"color": BRAND_BLUE}},
            connector={"line": {"color": "#9CA3AF"}},
            hovertemplate="%{x}: %{y:,.1f} mn TL<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"{FOCUS_COMPANY}: ciro değişim köprüsü (son ay / önceki yılın aynı ayı)"
    )
    return apply_business_theme(figure, y_title=TL_AXIS)


def write_png(figure: go.Figure, path: Path) -> None:
    """Write a consistent portfolio image with an actionable failure message."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        figure.write_image(path, width=1200, height=680, scale=1.5)
    except Exception as exc:  # pragma: no cover - exercised only when renderer is unavailable
        raise RuntimeError(
            "Static chart export failed. Install the project dev dependencies, including Kaleido."
        ) from exc
