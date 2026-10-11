"""Consistent Plotly figures for pipeline exports and Streamlit pages."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from energy_market_intelligence.localization import format_number
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY

TL_AXIS = "mn TL (sabit 2025 fiyatlarıyla)"

# Design tokens. Every colour carries exactly one meaning (see docs/DESIGN.md).
NAVY = "#1F3A5F"  # Şebeke laciverti: prices, headings, primary series
LEAK_RED = "#C8462B"  # Kaçak kırmızısı: deductions, leakage and policy breaches only
GAIN_GREEN = "#2E7D5B"  # Sertifika yeşili: gains from the recommendation, positive outcomes only
SLATE = "#6B7480"  # Trafo grisi: secondary text and neutral series
INK = "#1B2430"  # body text
GRID = "#E3E7EA"  # gridlines and hairlines
NAVY_SOFT = "#8197B4"  # lighter navy for second series and neutral increases
SLATE_SOFT = "#B5BDC6"  # lighter slate for third series

# Font stacks. The web fonts come from Google Fonts in the app; the fallbacks keep PNG exports
# (rendered offline by Kaleido) and slow connections readable.
FONT_BODY = "'Source Sans 3', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
FONT_HEADING = "'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif"
FONT_MONO = "'IBM Plex Mono', Consolas, Menlo, monospace"
TEMPLATE_NAME = "tavra"


def _build_template() -> go.layout.Template:
    """The single Plotly template shared by the Streamlit pages and the PNG exports."""

    axis = {
        "tickfont": {"family": FONT_BODY, "size": 12, "color": SLATE},
        "title": {"font": {"family": FONT_BODY, "size": 13, "color": SLATE}},
        "linecolor": GRID,
        "tickcolor": GRID,
        "automargin": True,
    }
    layout = go.Layout(
        font={"family": FONT_BODY, "size": 14, "color": INK},
        title={
            "x": 0.01,
            "xanchor": "left",
            "font": {"family": FONT_HEADING, "size": 21, "color": NAVY},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[NAVY, SLATE, NAVY_SOFT, SLATE_SOFT, "#3E5C86"],
        margin={"l": 65, "r": 30, "t": 70, "b": 60},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 0,
            "font": {"family": FONT_BODY, "size": 13, "color": INK},
        },
        hoverlabel={
            "namelength": -1,
            "bgcolor": "#FFFFFF",
            "bordercolor": GRID,
            "font": {"family": FONT_MONO, "size": 13, "color": INK},
        },
        separators=",.",  # Turkish: comma for decimals, dot for thousands
        xaxis={**axis, "showgrid": False, "zeroline": False},
        yaxis={
            **axis,
            "showgrid": True,
            "gridcolor": GRID,
            "zeroline": True,
            "zerolinecolor": GRID,
            "showline": False,
        },
        annotationdefaults={"font": {"family": FONT_BODY, "size": 14, "color": INK}},
        colorscale={
            "sequential": [[0, "#E3E9F1"], [1, NAVY]],
            "sequentialminus": [[0, NAVY], [1, "#E3E9F1"]],
            "diverging": [[0, SLATE], [0.5, "#F2F4F5"], [1, NAVY]],
        },
    )
    return go.layout.Template(layout=layout)


pio.templates[TEMPLATE_NAME] = _build_template()
pio.templates.default = TEMPLATE_NAME


def apply_business_theme(
    figure: go.Figure, *, y_title: str | None = None, mono_axis: str | None = "y"
) -> go.Figure:
    """Apply the shared template to a figure and set axis titles.

    ``mono_axis`` names the axis (``"x"`` or ``"y"``) that carries numbers; its tick labels use
    the monospaced data font.
    """

    figure.update_layout(template=TEMPLATE_NAME)
    figure.update_xaxes(title=None)
    figure.update_yaxes(title=y_title)
    if mono_axis in {"x", "y"}:
        mono = {"tickfont": {"family": FONT_MONO, "size": 12, "color": SLATE}}
        (figure.update_xaxes if mono_axis == "x" else figure.update_yaxes)(**mono)
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
    figure.update_traces(line={"color": NAVY, "width": 3}, marker={"size": 5})
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
    figure.update_traces(textposition="top center", textfont={"size": 11})
    figure.update_xaxes(tickformat=".0%")
    figure.update_yaxes(tickformat=".0%")
    apply_business_theme(figure, y_title="Pazar büyümesi (son 12 ay / önceki 12 ay)")
    figure.update_xaxes(title="Şirketin pazar payı (son 12 ay)")
    return figure


def competitor_change_figure(frame: pd.DataFrame) -> go.Figure:
    """Rank annual company-share movement in percentage points."""

    ordered = frame.sort_values("share_change_pp")
    colors = [NAVY if value >= 0 else SLATE for value in ordered["share_change_pp"]]
    figure = go.Figure(
        go.Bar(
            x=ordered["share_change_pp"],
            y=ordered["company_name"],
            orientation="h",
            marker_color=colors,
            textfont={"family": FONT_MONO, "size": 13},
            text=ordered["share_change_pp"].map(
                lambda value: f"{format_number(value, 2, signed=True)} puan"
            ),
            textposition="outside",
            hovertemplate="%{y}<br>Pay değişimi: %{x:+.2f} puan<extra></extra>",
        )
    )
    figure.update_layout(title="Şirketlerin pazar payı değişimi: son 12 ay / önceki 12 ay")
    apply_business_theme(figure, y_title=None, mono_axis="x")
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
    figure.update_traces(line={"color": NAVY, "width": 3}, marker={"size": 5})
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
            increasing={"marker": {"color": NAVY_SOFT}},
            decreasing={"marker": {"color": SLATE}},
            totals={"marker": {"color": NAVY}},
            textfont={"family": FONT_MONO, "size": 13},
            connector={"line": {"color": SLATE_SOFT}},
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
        export = go.Figure(figure)
        export.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
        export.write_image(path, width=1200, height=680, scale=1.5)
    except Exception as exc:  # pragma: no cover - exercised only when renderer is unavailable
        raise RuntimeError(
            "Static chart export failed. Install the project dev dependencies, including Kaleido."
        ) from exc
