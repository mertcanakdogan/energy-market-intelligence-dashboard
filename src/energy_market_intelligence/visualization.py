"""Consistent Plotly figures for pipeline exports and Streamlit pages."""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from energy_market_intelligence.localization import format_number
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY

TRY_AXIS = "TRY m (constant 2025 prices)"

# Design tokens. Every colour carries exactly one meaning (see DESIGN.md).
NAVY = "#1F3A5F"  # Grid navy: prices, headings, primary series
LEAK_RED = "#C8462B"  # Leak red: deductions, leakage and policy breaches only
GAIN_GREEN = "#2E7D5B"  # Certificate green: gains from the recommendation, positive outcomes only
SLATE = "#6B7480"  # Transformer grey: secondary text and neutral series
INK = "#1B2430"  # body text
GRID = "#E3E7EA"  # gridlines and hairlines
NAVY_SOFT = "#8197B4"  # lighter navy for second series and neutral increases
SLATE_SOFT = "#B5BDC6"  # lighter slate for third series

# Font stacks. The web fonts come from Google Fonts in the app; PNG exports (rendered by Kaleido)
# use them when they are installed on the machine (see DEPLOY.md), else the fallbacks.
FONT_BODY = "'Source Sans 3', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
FONT_HEADING = "'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif"
FONT_MONO = "'IBM Plex Mono', Consolas, Menlo, monospace"
TEMPLATE_NAME = "tavra"
TEMPLATE_TOP = 104  # top margin: the title plus a legend row under it


def _build_template() -> go.layout.Template:
    """The single Plotly template shared by the Streamlit pages and the PNG exports."""

    axis = {
        "tickfont": {"family": FONT_BODY, "size": 13, "color": SLATE},
        "title": {"font": {"family": FONT_BODY, "size": 14, "color": SLATE}},
        "linecolor": GRID,
        "tickcolor": GRID,
        "automargin": True,
    }
    layout = go.Layout(
        font={"family": FONT_BODY, "size": 14, "color": INK},
        # Title pinned to the top of the canvas, legend pinned under it: the gap between them
        # holds even when the export falls back to a wider system font.
        title={
            "x": 0.01,
            "xanchor": "left",
            "yref": "container",
            "y": 1,
            "yanchor": "top",
            "pad": {"t": 22},
            "font": {"family": FONT_HEADING, "size": 22, "weight": 700, "color": NAVY},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[NAVY, SLATE, NAVY_SOFT, SLATE_SOFT, "#3E5C86"],
        margin={"l": 65, "r": 30, "t": TEMPLATE_TOP, "b": 60},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.03,
            "x": 0,
            "font": {"family": FONT_BODY, "size": 13, "color": INK},
        },
        hoverlabel={
            "namelength": -1,
            "bgcolor": "#FFFFFF",
            "bordercolor": GRID,
            "font": {"family": FONT_MONO, "size": 13, "color": INK},
        },
        separators=".,",  # English: dot for decimals, comma for thousands
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


def format_axes(figure: go.Figure) -> go.Figure:
    """Give unformatted axes readable ticks: months as ``Jan 2025``, thousands as ``4,000``.

    Axes that already carry a ``tickformat`` or explicit tick labels are left as they are.
    """

    formats = {"date": "%b %Y", "number": ",~f"}
    for axis, each in (("x", figure.for_each_xaxis), ("y", figure.for_each_yaxis)):
        kind = _axis_kind(figure, axis)
        if kind is None:
            continue

        def apply(layout_axis, fmt=formats[kind]) -> None:
            if not layout_axis.tickformat and layout_axis.tickvals is None:
                layout_axis.tickformat = fmt

        each(apply)
    return figure


def has_legend(figure: go.Figure) -> bool:
    """Whether Plotly will draw a legend for ``figure`` (the template reserves room for one)."""

    if figure.layout.showlegend is False:
        return False
    shown = [trace for trace in figure.data if trace.showlegend is not False]
    if figure.layout.showlegend is True:
        return bool(shown)
    return len(shown) > 1 or any(trace.showlegend is True for trace in shown)


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
        mono = {"tickfont": {"family": FONT_MONO, "size": 13, "color": SLATE}}
        (figure.update_xaxes if mono_axis == "x" else figure.update_yaxes)(**mono)
    return figure


def market_share_trend_figure(frame: pd.DataFrame) -> go.Figure:
    """Show the focus company's monthly national market-share trajectory."""

    figure = px.line(
        frame,
        x="date",
        y="focus_market_share",
        title=f"{FOCUS_COMPANY}: monthly market share",
        markers=True,
    )
    figure.update_traces(line={"color": NAVY, "width": 3}, marker={"size": 5})
    figure.update_yaxes(tickformat=".1%")
    figure.update_traces(hovertemplate="%{x|%b %Y}: %{y:.1%}<extra></extra>")
    return apply_business_theme(figure, y_title="Market share (axis does not start at zero)")


def opportunity_matrix_figure(frame: pd.DataFrame) -> go.Figure:
    """Compare provincial growth, focus-company share, scale, and opportunity score."""

    chart_data = frame.copy()
    if "opportunity_rank" in chart_data:
        chart_data["display_label"] = chart_data["region_name"].where(
            chart_data["opportunity_rank"] <= 5, ""
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
        title="Province opportunity matrix (bubble size = market volume)",
        labels={
            "opportunity_score": "Opportunity score",
            "focus_share": "Company market share",
            "market_growth": "Market growth (yearly)",
            "market_volume": "Market volume (MWh)",
            "region_name": "Province",
        },
    )
    figure.update_traces(
        textposition="top center",
        textfont={"size": 13, "color": INK},
        marker={"line": {"color": "#FFFFFF", "width": 1}},
    )
    # Start the scale at a mid navy: the palest bubbles must still stand out from the page.
    figure.update_layout(
        coloraxis={
            "colorscale": [[0, NAVY_SOFT], [1, NAVY]],
            "colorbar": {
                "title": {
                    "text": "Opportunity<br>score",
                    "font": {"family": FONT_BODY, "size": 13, "color": SLATE},
                },
                "tickfont": {"family": FONT_MONO, "size": 13, "color": SLATE},
                "thickness": 14,
            },
        }
    )
    figure.update_xaxes(tickformat=".0%")
    figure.update_yaxes(tickformat=".0%")
    apply_business_theme(figure, y_title="Market growth (last 12 months vs the 12 before)")
    figure.update_xaxes(title="Company market share (last 12 months)")
    return figure


def competitor_change_figure(frame: pd.DataFrame) -> go.Figure:
    """Rank annual company-share movement in percentage points."""

    ordered = frame.sort_values("share_change_pp")
    # The focus company in navy, the competitors in grey; the bar direction carries the sign.
    colors = [NAVY if name == FOCUS_COMPANY else SLATE_SOFT for name in ordered["company_name"]]
    figure = go.Figure(
        go.Bar(
            x=ordered["share_change_pp"],
            y=ordered["company_name"],
            orientation="h",
            marker_color=colors,
            textfont={"family": FONT_MONO, "size": 13},
            text=ordered["share_change_pp"].map(
                lambda value: f"{format_number(value, 2, signed=True)} pp"
            ),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>Share change: %{x:+.2f} pp<extra></extra>",
        )
    )
    figure.update_layout(title="Change in market share by company: last 12 months vs the 12 before")
    apply_business_theme(figure, y_title=None, mono_axis="x")
    # Headroom on both sides so the outside labels never touch the company names or the edge.
    reach = float(ordered["share_change_pp"].abs().max()) * 1.45
    figure.update_xaxes(title="Change in market share (percentage points)", range=[-reach, reach])
    figure.update_yaxes(
        ticklabelstandoff=8, tickfont={"family": FONT_BODY, "size": 13, "color": INK}
    )
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
        title=f"{FOCUS_COMPANY}: monthly gross margin",
        markers=True,
    )
    figure.update_traces(line={"color": NAVY, "width": 3}, marker={"size": 5})
    figure.update_yaxes(tickformat=".1%")
    figure.update_traces(hovertemplate="%{x|%b %Y}: %{y:.1%}<extra></extra>")
    return apply_business_theme(figure, y_title="Gross margin (axis does not start at zero)")


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
            x=["Volume effect", "Price effect", "Interaction", "Revenue change"],
            y=values,
            measure=["relative", "relative", "relative", "total"],
            text=[format_number(value, 1, signed=True) for value in values],
            textposition="outside",
            increasing={"marker": {"color": NAVY_SOFT}},
            decreasing={"marker": {"color": SLATE}},
            totals={"marker": {"color": NAVY}},
            textfont={"family": FONT_MONO, "size": 13},
            connector={"line": {"color": SLATE_SOFT}},
            hovertemplate="%{x}: TRY %{y:,.1f}m<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"{FOCUS_COMPANY}: revenue bridge (latest month vs the same month a year earlier)"
    )
    return apply_business_theme(figure, y_title=TRY_AXIS)


def write_png(figure: go.Figure, path: Path) -> None:
    """Write a consistent portfolio image with an actionable failure message."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        export = format_axes(go.Figure(figure))
        export.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
        if not has_legend(export) and export.layout.margin.t in (None, TEMPLATE_TOP):
            export.update_layout(margin={"t": 72})  # the template's room for a legend stays empty
        # Charts with few rows set their own height; the rest use the standard 1200 x 680.
        export.write_image(path, width=1200, height=export.layout.height or 680, scale=1.5)
    except Exception as exc:  # pragma: no cover - exercised only when renderer is unavailable
        raise RuntimeError(
            "Static chart export failed. Install the project dev dependencies, including Kaleido."
        ) from exc
