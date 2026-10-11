"""Consistent Plotly figures for pipeline exports and Streamlit pages."""

from __future__ import annotations

import datetime
import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from energy_market_intelligence.localization import format_number, format_pct
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


def _nice_step(span: float, target_ticks: int = 5) -> float:
    raw = span / max(target_ticks, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiple in (1, 2, 5, 10):
        if raw <= multiple * magnitude:
            return multiple * magnitude
    return 10 * magnitude


def percent_axis(figure: go.Figure, axis: str = "y") -> go.Figure:
    """Label a share axis the Turkish way (``%10``, ``%12,5``) instead of d3's ``10%``.

    Plotly's d3 formats always put the percent sign after the number, so the ticks are set
    explicitly from the plotted data. Call it after the traces are final.
    """

    values: list[float] = []
    for trace in figure.data:
        data = getattr(trace, axis, None)
        if data is None:
            continue
        values.extend(float(v) for v in data if v is not None and math.isfinite(float(v)))
    if not values:
        return figure
    low, high = min(values), max(values)
    if any(trace.type == "bar" for trace in figure.data):
        low, high = min(low, 0.0), max(high, 0.0)  # bars start at zero; lines keep their range
    if high == low:
        high = low + 0.01
    step = _nice_step(high - low)
    first = math.floor(low / step + 1e-9)
    last = math.ceil(high / step - 1e-9)
    ticks = [round(index * step, 10) for index in range(first, last + 1)]
    shown = 0 if round(step * 100, 6).is_integer() else 1
    labels = [format_pct(value, shown) for value in ticks]
    update = {"tickmode": "array", "tickvals": ticks, "ticktext": labels}
    if axis == "y":
        figure.update_yaxes(**update)
    else:
        figure.update_xaxes(**update)
    return figure


def _axis_kind(figure: go.Figure, axis: str) -> str | None:
    """``"date"``, ``"number"`` or ``None`` (categories or mixed) for the plotted data."""

    kinds = set()
    for trace in figure.data:
        data = getattr(trace, axis, None)
        if data is None or len(data) == 0:
            continue
        series = pd.Series(list(data))
        if pd.api.types.is_datetime64_any_dtype(series) or all(
            isinstance(value, pd.Timestamp | datetime.date) for value in series
        ):
            kinds.add("date")
        elif pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            kinds.add("number")
        else:
            kinds.add(None)
    return kinds.pop() if len(kinds) == 1 else None


def turkish_axes(figure: go.Figure) -> go.Figure:
    """Give unformatted axes Turkish ticks: months as ``01/2025``, thousands as ``4.000``.

    Axes that already carry a ``tickformat`` or explicit tick labels are left as they are.
    """

    formats = {"date": "%m/%Y", "number": ",~f"}
    for axis, each in (("x", figure.for_each_xaxis), ("y", figure.for_each_yaxis)):
        kind = _axis_kind(figure, axis)
        if kind is None:
            continue

        def apply(layout_axis, fmt=formats[kind]) -> None:
            if not layout_axis.tickformat and layout_axis.tickvals is None:
                layout_axis.tickformat = fmt

        each(apply)
    return figure


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
    percent_axis(figure, "y")
    figure.update_traces(hovertemplate="%{x|%m/%Y}: %{y:.1%}<extra></extra>")
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
    percent_axis(figure, "x")
    percent_axis(figure, "y")
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
    percent_axis(figure, "y")
    figure.update_traces(hovertemplate="%{x|%m/%Y}: %{y:.1%}<extra></extra>")
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
        export = turkish_axes(go.Figure(figure))
        export.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
        export.write_image(path, width=1200, height=680, scale=1.5)
    except Exception as exc:  # pragma: no cover - exercised only when renderer is unavailable
        raise RuntimeError(
            "Static chart export failed. Install the project dev dependencies, including Kaleido."
        ) from exc
