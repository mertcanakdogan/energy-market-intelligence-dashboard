"""Plotly figures for the pricing case study (pipeline PNG exports and Streamlit pages)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from energy_market_intelligence.localization import (
    MINUS,
    VALUE_LABELS,
    format_number,
    format_pct,
    format_try,
    order_segments,
)
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY, GeneratorConfig
from energy_market_intelligence.visualization import (
    FONT_BODY,
    FONT_DATA,
    FONT_HEADING,
    GAIN_GREEN,
    GRID,
    INK,
    LEAK_RED,
    NAVY,
    NAVY_SOFT,
    SLATE,
    SLATE_SOFT,
    TRY_AXIS,
    apply_business_theme,
)

# Line items of the price waterfall. The labels read like the lines of an electricity bill and
# are shared by the charts, the "price breakdown" block on the home page and the tables.
LIST_LABEL = "List price"
INVOICE_LABEL = "Invoice price"
NET_LABEL = "Pocket price"
DEDUCTION_LABELS = {
    "on_invoice_discount": "On-invoice discount",
    "off_invoice_rebate": "Off-invoice rebate",
    "payment_term_cost": "Payment-term cost",
    "freight_service_cost": "Service and freight",
}
WATERFALL_STEPS = (
    (LIST_LABEL, "list_price", "absolute"),
    (DEDUCTION_LABELS["on_invoice_discount"], "on_invoice_discount", "relative"),
    (INVOICE_LABEL, "invoice_price", "total"),
    (DEDUCTION_LABELS["off_invoice_rebate"], "off_invoice_rebate", "relative"),
    (DEDUCTION_LABELS["payment_term_cost"], "payment_term_cost", "relative"),
    (DEDUCTION_LABELS["freight_service_cost"], "freight_service_cost", "relative"),
    (NET_LABEL, "pocket_price", "total"),
)
PORTFOLIO = "Whole portfolio"
AMOUNT_COLUMNS = {
    "list_price": "list_revenue",
    "on_invoice_discount": "on_invoice_discount_amount",
    "invoice_price": "invoice_revenue",
    "off_invoice_rebate": "off_invoice_rebate_amount",
    "payment_term_cost": "payment_term_cost_amount",
    "freight_service_cost": "freight_service_cost_amount",
    "pocket_price": "pocket_revenue",
}


def segment_waterfall_table(waterfall: pd.DataFrame) -> pd.DataFrame:
    """Volume-weighted per-MWh waterfall by customer segment from ``vw_price_waterfall``."""

    totals = waterfall.groupby("customer_segment_name", as_index=False)[
        ["volume_mwh", *AMOUNT_COLUMNS.values()]
    ].sum()
    for unit_column, amount_column in AMOUNT_COLUMNS.items():
        totals[unit_column] = totals[amount_column] / totals["volume_mwh"]
    ordered = order_segments(totals).reset_index(drop=True)
    return ordered[["customer_segment_name", "volume_mwh", *AMOUNT_COLUMNS]]


@dataclass(frozen=True)
class BillLine:
    """One line of the itemised price (TRY/MWh) with its share of the list price."""

    label: str
    amount: float
    share_of_list: float
    kind: str  # "list", "deduction" or "net"


@dataclass(frozen=True)
class Bill:
    """The "price breakdown": list price down to the net (pocket) price per MWh."""

    scope: str
    lines: tuple[BillLine, ...]
    leakage_rate: float  # 1 - net / list: the share of the list price that never arrives


def portfolio_bill(waterfall: pd.DataFrame, segment: str | None = None) -> Bill:
    """Volume-weighted bill for the whole portfolio or a single customer segment."""

    selected = waterfall
    if segment is not None:
        selected = waterfall[waterfall["customer_segment_name"] == segment]
    if selected.empty:
        raise ValueError(f"No price waterfall rows for segment: {segment}")
    totals = selected[["volume_mwh", *AMOUNT_COLUMNS.values()]].sum()
    per_mwh = {
        name: float(totals[column] / totals["volume_mwh"])
        for name, column in AMOUNT_COLUMNS.items()
    }
    list_price = per_mwh["list_price"]
    lines = [BillLine(LIST_LABEL, list_price, 1.0, "list")]
    lines += [
        BillLine(label, per_mwh[name], per_mwh[name] / list_price, "deduction")
        for name, label in DEDUCTION_LABELS.items()
    ]
    net = per_mwh["pocket_price"]
    lines.append(BillLine(NET_LABEL, net, net / list_price, "net"))
    return Bill(segment or PORTFOLIO, tuple(lines), float(1 - net / list_price))


def bill_waterfall_figure(bill: Bill) -> go.Figure:
    """Horizontal waterfall that mirrors the bill lines one to one (TRY/MWh)."""

    labels = [line.label for line in bill.lines]
    values = [-line.amount if line.kind == "deduction" else line.amount for line in bill.lines]
    measure = ["absolute" if line.kind == "list" else "relative" for line in bill.lines]
    measure[-1] = "total"
    values[-1] = 0.0  # Plotly derives the total bar from the running sum
    text = [
        f"{MINUS}{format_number(line.amount, 0)}"
        if line.kind == "deduction"
        else format_number(line.amount, 0)
        for line in bill.lines
    ]
    figure = go.Figure(
        go.Waterfall(
            orientation="h",
            y=labels,
            x=values,
            measure=measure,
            text=text,
            textposition="outside",
            cliponaxis=False,  # the list-price label sits past the axis end on narrow screens
            textfont={"family": FONT_DATA, "size": 13, "color": INK},
            decreasing={"marker": {"color": LEAK_RED}},
            increasing={"marker": {"color": NAVY}},
            totals={"marker": {"color": NAVY}},
            connector={"line": {"color": SLATE_SOFT, "width": 1}},
            hovertemplate="%{y}: %{text} TRY/MWh<extra></extra>",
            showlegend=False,
        )
    )
    list_price, net = bill.lines[0].amount, bill.lines[-1].amount
    apply_business_theme(figure, mono_axis="x")
    figure.update_layout(margin={"l": 8, "r": 56, "t": 12, "b": 48}, height=380)
    figure.update_yaxes(
        autorange="reversed",
        showgrid=False,
        zeroline=False,
        ticksuffix="  ",
        tickfont={"family": FONT_BODY, "size": 13, "color": INK},
    )
    figure.update_xaxes(
        range=[net * 0.94, list_price * 1.06],
        showgrid=True,
        gridcolor=GRID,
        title="TRY/MWh (axis does not start at zero)",
        tickformat=",d",
        nticks=4,
        tickangle=0,
    )
    return figure


def _rounded_levels(levels: list[float]) -> list[float]:
    """Waterfall levels rounded to whole TRY so that every subtotal adds up on the chart."""

    rounded = [float(round(level)) for level in levels]
    running = rounded[0]
    for index, (_label, _field, measure) in enumerate(WATERFALL_STEPS):
        if measure == "relative":
            running -= rounded[index]
        elif measure == "total":
            rounded[index] = running
    return rounded


def price_waterfall_figure(waterfall: pd.DataFrame) -> go.Figure:
    """List-to-pocket price waterfall (per MWh) for each customer segment (PNG export)."""

    table = segment_waterfall_table(waterfall)
    segments = table["customer_segment_name"].tolist()
    figure = make_subplots(
        rows=1,
        cols=len(segments),
        subplot_titles=segments,
        shared_yaxes=True,
        horizontal_spacing=0.04,
    )
    for column, row in enumerate(table.itertuples(index=False), start=1):
        levels = _rounded_levels([getattr(row, field) for _label, field, _m in WATERFALL_STEPS])
        # Plotly derives "total" bars from the running sum, so their own y is 0.
        values = [
            0.0 if measure == "total" else (level if measure == "absolute" else -level)
            for (_label, _field, measure), level in zip(WATERFALL_STEPS, levels, strict=True)
        ]
        text = [
            (MINUS if measure == "relative" else "") + format_number(level, 0)
            for (_label, _field, measure), level in zip(WATERFALL_STEPS, levels, strict=True)
        ]
        figure.add_trace(
            go.Waterfall(
                x=[label for label, _field, _measure in WATERFALL_STEPS],
                y=values,
                measure=[measure for _label, _field, measure in WATERFALL_STEPS],
                text=text,
                textposition="outside",
                constraintext="none",  # totals keep the same label size as the deductions
                cliponaxis=False,
                increasing={"marker": {"color": NAVY}},
                decreasing={"marker": {"color": LEAK_RED}},
                totals={"marker": {"color": NAVY}},
                textfont={"family": FONT_DATA, "size": 13, "color": INK},
                connector={"line": {"color": SLATE_SOFT}},
                hoverinfo="x+text",
                showlegend=False,
            ),
            row=1,
            col=column,
        )
    figure.update_layout(title="From list price to pocket price (TRY/MWh, 2025)")
    apply_business_theme(figure)
    figure.update_annotations(
        font={"family": FONT_HEADING, "size": 18, "weight": 400, "color": NAVY}
    )
    figure.update_xaxes(tickangle=-40, tickfont={"family": FONT_BODY, "size": 13, "color": INK})
    figure.update_yaxes(
        range=[float(table["pocket_price"].min()) * 0.9, float(table["list_price"].max()) * 1.05],
        tickformat=",d",
    )
    figure.update_yaxes(title="TRY/MWh (axis does not start at zero)", col=1)
    return figure


def _bridge_panels(summary: pd.DataFrame) -> list[tuple[str, list[tuple[str, float]], float]]:
    """Title, effects (TRY m) and total of the revenue and gross-profit bridges."""

    row = summary.iloc[0]
    return [
        (
            "Net revenue change",
            [
                ("Volume", row["volume_effect"] / 1e6),
                ("Mix", row["mix_effect"] / 1e6),
                ("Price", row["price_effect"] / 1e6),
            ],
            row["total_revenue_change"] / 1e6,
        ),
        (
            "Gross profit change",
            [
                ("Volume", row["gp_volume_effect"] / 1e6),
                ("Mix", row["gp_mix_effect"] / 1e6),
                ("Price", row["gp_price_effect"] / 1e6),
                ("Unit cost", row["gp_cost_effect"] / 1e6),
            ],
            row["total_gp_change"] / 1e6,
        ),
    ]


def _bridge_trace(
    effects: list[tuple[str, float]], total: float, *, horizontal: bool = False
) -> go.Waterfall:
    values = [value for _, value in effects] + [total]
    labels = [label for label, _ in effects] + ["Total"]
    return go.Waterfall(
        orientation="h" if horizontal else "v",
        x=values if horizontal else labels,
        y=labels if horizontal else values,
        measure=["relative"] * len(effects) + ["total"],
        text=[format_number(value, 1, signed=True) for value in values],
        textposition="outside",
        constraintext="none",
        cliponaxis=False,
        increasing={"marker": {"color": NAVY_SOFT}},
        decreasing={"marker": {"color": SLATE}},
        totals={"marker": {"color": NAVY}},
        textfont={"family": FONT_DATA, "size": 13, "color": INK},
        connector={"line": {"color": SLATE_SOFT}},
        hovertemplate=("%{y}: TRY %{x:,.1f}m" if horizontal else "%{x}: TRY %{y:,.1f}m")
        + "<extra></extra>",
        showlegend=False,
    )


def _bridge_range(summary: pd.DataFrame) -> list[float]:
    """One y range for both bridges, so equal amounts have equal bar lengths."""

    levels = [0.0]
    for _title, effects, _total in _bridge_panels(summary):
        running = 0.0
        for _label, value in effects:
            running += value
            levels.append(running)
    low, high = min(levels), max(levels)
    pad = (high - low) * 0.14
    return [min(low - pad, 0.0), high + pad]


def pvm_bridge_panel_figures(summary: pd.DataFrame) -> list[go.Figure]:
    """The revenue and gross-profit bridges as two horizontal waterfalls for the app.

    Horizontal like the price breakdown: every label has its own row, so none collide on a
    phone, and the two charts stack there.
    """

    figures = []
    low, high = _bridge_range(summary)
    # Room for the labels outside the bars: falls carry theirs on the left, next to the names.
    pad_low, pad_high = (high - low) * 0.3, (high - low) * 0.12
    for title, effects, total in _bridge_panels(summary):
        figure = go.Figure(_bridge_trace(effects, total, horizontal=True))
        figure.update_layout(title=title, height=330)
        apply_business_theme(figure, mono_axis="x")
        figure.update_xaxes(
            title=TRY_AXIS,
            range=[low - pad_low, high + pad_high],
            showgrid=True,
            gridcolor=GRID,
            zeroline=True,
            zerolinecolor=SLATE_SOFT,
        )
        figure.update_yaxes(
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            ticksuffix="  ",
            tickfont={"family": FONT_BODY, "size": 13, "color": INK},
        )
        figures.append(figure)
    return figures


def pvm_bridge_figure(summary: pd.DataFrame) -> go.Figure:
    """Price-volume-mix bridge of net revenue and gross profit, 2025 vs 2024 (PNG export)."""

    panels = _bridge_panels(summary)
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=[title for title, _effects, _total in panels],
        shared_yaxes=True,
        horizontal_spacing=0.06,
    )
    y_range = _bridge_range(summary)
    for column, (_title, effects, total) in enumerate(panels, start=1):
        figure.add_trace(_bridge_trace(effects, total), row=1, col=column)
    figure.update_layout(title=f"{FOCUS_COMPANY}: price-volume-mix bridge (2025 vs 2024)")
    apply_business_theme(figure)
    figure.update_annotations(
        font={"family": FONT_HEADING, "size": 18, "weight": 400, "color": NAVY}
    )
    figure.update_xaxes(tickfont={"family": FONT_BODY, "size": 13, "color": INK})
    figure.update_yaxes(range=y_range)
    figure.update_yaxes(title=TRY_AXIS, col=1)
    return figure


def _interval_trace(
    x: pd.Series, y: pd.Series, low: pd.Series, high: pd.Series, name: str
) -> go.Scatter:
    return go.Scatter(
        x=x,
        y=y,
        mode="markers",
        name=name,
        marker={"color": NAVY, "size": 11},
        error_x={
            "type": "data",
            "symmetric": False,
            "array": high - x,
            "arrayminus": x - low,
            "color": NAVY,
            "thickness": 2.5,
        },
    )


def _truth_trace(x: pd.Series, y: pd.Series) -> go.Scatter:
    """The known true value: a hollow diamond, larger than the estimate dot, so both show."""

    return go.Scatter(
        x=x,
        y=y,
        mode="markers",
        name="True value (data generator)",
        marker={
            "color": "rgba(255,255,255,0)",
            "size": 18,
            "symbol": "diamond",
            "line": {"color": INK, "width": 2},
        },
    )


def _estimate_on_top(figure: go.Figure) -> None:
    """Draw the true value under the estimate, but keep the estimate first in the legend."""

    figure.data = tuple(reversed(figure.data))
    figure.update_layout(legend={"traceorder": "reversed"})


def _category_axis(figure: go.Figure, **selector) -> None:
    """Category names are words: ink body face, clear of the plotted marks."""

    figure.update_yaxes(
        showgrid=False,
        ticklabelstandoff=10,
        tickfont={"family": FONT_BODY, "size": 14, "color": INK},
        **selector,
    )


def elasticity_recovery_figure(table: pd.DataFrame) -> go.Figure:
    """Estimated elasticity with 95% CI next to the known true value, per segment."""

    table = order_segments(table).iloc[::-1]  # first segment at the top of the chart
    figure = go.Figure()
    figure.add_trace(
        _interval_trace(
            table["elasticity"],
            table["customer_segment_name"],
            table["ci_low"],
            table["ci_high"],
            "Estimate (95% confidence interval)",
        )
    )
    figure.add_trace(_truth_trace(table["true_elasticity"], table["customer_segment_name"]))
    _estimate_on_top(figure)
    figure.add_vline(x=-1, line_dash="dot", line_color=SLATE)
    # Name the two sides of -1 instead of the jargon "unit elasticity".
    for text, anchor, shift in (
        ("← more sensitive", "right", -6),
        ("less sensitive →", "left", 6),
    ):
        figure.add_annotation(
            x=-1,
            y=0,
            xref="x",
            yref="paper",
            yanchor="bottom",
            xanchor=anchor,
            xshift=shift,
            yshift=4,
            text=text,
            showarrow=False,
            font={"family": FONT_BODY, "size": 13, "color": SLATE},
        )
    figure.update_layout(title="Price elasticity: estimate and known true value", height=420)
    apply_business_theme(figure, mono_axis="x")
    _category_axis(figure)
    figure.update_yaxes(range=[-1.0, len(table) - 0.5])
    low = float(min(table["ci_low"].min(), table["true_elasticity"].min(), -1.0))
    high = float(max(table["ci_high"].max(), table["true_elasticity"].max(), -1.0))
    pad = (high - low) * 0.12
    high = max(high, -1.0 + (high - low) * 0.3)  # room for the label right of -1
    figure.update_xaxes(
        title="Price elasticity: % change in volume when the pocket price rises 1%",
        showgrid=True,
        gridcolor=GRID,
        tickformat=".1f",
        range=[low - pad, high + pad],
    )
    return figure


def month_dates(month_id: pd.Series) -> pd.Series:
    """Month numbers of the synthetic data (1 = January 2023) as first-of-month dates."""

    start = pd.Timestamp(GeneratorConfig().start_month)
    return pd.Series(
        [start + pd.DateOffset(months=int(month) - 1) for month in month_id], index=month_id.index
    )


def _promotion_band(window: tuple[int, int]) -> tuple[pd.Timestamp, pd.Timestamp]:
    first, last = month_dates(pd.Series(window)).tolist()
    return first - pd.Timedelta(days=15), last + pd.Timedelta(days=15)


def _trend_traces(trend: pd.DataFrame) -> list[go.Scatter]:
    dates = month_dates(trend["month_id"])
    return [
        go.Scatter(
            x=dates,
            y=trend[name],
            mode="lines+markers",
            name=label,
            line={"color": color, "width": 2.5},
            marker={"size": 4},
            hovertemplate="%{x|%b %Y}: %{y:.1f}<extra></extra>",
        )
        for name, label, color in (
            ("control", "Control provinces", SLATE),
            ("treated", "Promotion provinces", NAVY),
        )
    ]


def _estimate_frame(estimates: pd.DataFrame) -> pd.DataFrame:
    labels = estimates["method"].map(
        {"naive": VALUE_LABELS["naive"], "price_adjusted": VALUE_LABELS["price_adjusted"]}
    )
    return pd.DataFrame(
        {
            "label": labels,
            "uplift": estimates["uplift"] * 100,
            "low": estimates["ci_low"] * 100,
            "high": estimates["ci_high"] * 100,
            "truth": estimates["true_uplift"] * 100,
        }
    )


def _estimate_range(frame: pd.DataFrame) -> list[float]:
    """From zero, so the size of each estimate and of the truth compare honestly."""

    return [0.0, float(max(frame["high"].max(), frame["truth"].max())) * 1.12]


def _trend_range(trend: pd.DataFrame) -> list[float]:
    """Headroom above the highest month, so the band label never sits on a line."""

    values = trend[["control", "treated"]]
    low, high = float(values.min().min()), float(values.max().max())
    return [low - (high - low) * 0.06, high + (high - low) * 0.22]


def _promotion_vrect(figure: go.Figure, window: tuple[int, int], **position) -> None:
    start, end = _promotion_band(window)
    figure.add_vrect(
        x0=start,
        x1=end,
        fillcolor=SLATE_SOFT,
        opacity=0.3,
        line_width=0,
        layer="below",
        annotation_text="Promotion",
        annotation_position="top left",
        annotation_font={"family": FONT_BODY, "size": 13, "color": SLATE},
        **position,
    )


def promo_trend_figure(trend: pd.DataFrame, window: tuple[int, int]) -> go.Figure:
    """Monthly volume index of the promotion and control provinces, with the promotion band."""

    figure = go.Figure(_trend_traces(trend))
    _promotion_vrect(figure, window)
    figure.update_layout(title="Volume index (before the promotion = 100)", height=420)
    apply_business_theme(figure, y_title="Index (axis does not start at zero)")
    return figure.update_yaxes(range=_trend_range(trend))


def promo_estimate_figure(estimates: pd.DataFrame) -> go.Figure:
    """Estimated promotion effect per method, with its 95% CI, against the true effect."""

    frame = _estimate_frame(estimates)
    figure = go.Figure(
        [
            _interval_trace(
                frame["uplift"],
                frame["label"],
                frame["low"],
                frame["high"],
                "Estimate (95% confidence interval)",
            ),
            _truth_trace(frame["truth"], frame["label"]),
        ]
    )
    _estimate_on_top(figure)
    figure.update_layout(title="Estimated promotion effect and true value", height=320)
    apply_business_theme(figure, mono_axis="x")
    _category_axis(figure)
    figure.update_xaxes(
        title="Extra volume from the promotion (%)",
        range=_estimate_range(frame),
        showgrid=True,
        gridcolor=GRID,
    )
    return figure


def promo_did_figure(
    estimates: pd.DataFrame, trend: pd.DataFrame, window: tuple[int, int]
) -> go.Figure:
    """Volume index and DiD estimates against the true uplift, side by side (PNG export)."""

    titles = (
        "Volume index (before the promotion = 100)",
        "Estimated promotion effect and true value",
    )
    figure = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.55, 0.45],
        subplot_titles=titles,
        horizontal_spacing=0.2,  # room for the method names between the panels
    )
    for trace in _trend_traces(trend):
        figure.add_trace(trace, row=1, col=1)
    _promotion_vrect(figure, window, row=1, col=1)
    frame = _estimate_frame(estimates)
    figure.add_trace(
        _interval_trace(
            frame["uplift"],
            frame["label"],
            frame["low"],
            frame["high"],
            "Estimate (95% confidence interval)",
        ),
        row=1,
        col=2,
    )
    figure.add_trace(_truth_trace(frame["truth"], frame["label"]), row=1, col=2)
    figure.update_layout(title="Promotion effect: difference-in-differences (DiD) method")
    apply_business_theme(figure)
    for title in titles:
        figure.update_annotations(
            font={"family": FONT_HEADING, "size": 18, "weight": 400, "color": NAVY},
            selector={"text": title},
        )
    # The subplot titles sit where the legend would go, so the legend moves under the plots.
    figure.update_layout(
        legend={"orientation": "h", "yanchor": "top", "y": -0.16, "x": 0},
        margin={"l": 65, "r": 30, "t": 104, "b": 110},
    )
    figure.update_yaxes(
        title="Index (axis does not start at zero)", range=_trend_range(trend), row=1, col=1
    )
    _category_axis(figure, row=1, col=2)
    figure.update_xaxes(
        title="Extra volume from the promotion (%)",
        range=_estimate_range(frame),
        showgrid=True,
        gridcolor=GRID,
        tickfont={"family": FONT_DATA, "size": 13, "color": SLATE},
        row=1,
        col=2,
    )
    return figure


def price_recommendation_figure(table: pd.DataFrame) -> go.Figure:
    """Expected 12-month gross-profit change by segment with the elasticity-CI range.

    Each bar carries its segment and price step as a label above it, so the bars keep the full
    width of the chart on a phone.
    """

    ordered = table.sort_values("expected_gross_profit_change").reset_index(drop=True)
    expected = ordered["expected_gross_profit_change"] / 1e6
    low = ordered["gross_profit_change_low"] / 1e6
    high = ordered["gross_profit_change_high"] / 1e6
    positions = list(range(len(ordered)))
    figure = go.Figure(
        go.Bar(
            x=expected,
            y=positions,
            orientation="h",
            width=0.42,
            marker_color=[GAIN_GREEN if value >= 0 else SLATE for value in expected],
            # A leading space keeps the amount off the bar's edge.
            text=[
                f" {format_try(value, signed=True)}"
                for value in ordered["expected_gross_profit_change"]
            ],
            textposition="inside",
            insidetextanchor="start",
            textangle=0,
            textfont={"family": FONT_DATA, "color": "white", "size": 14},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": high - expected,
                "arrayminus": expected - low,
                "color": INK,
                "thickness": 2,
            },
            customdata=ordered["customer_segment_name"],
            hovertemplate="%{customdata}: TRY %{x:,.1f}m<extra></extra>",
        )
    )
    for position, row in zip(positions, ordered.itertuples(index=False), strict=True):
        figure.add_annotation(
            x=0,
            xref="paper",
            xanchor="left",
            y=position + 0.24,
            yanchor="bottom",
            text=(
                f"<b>{row.customer_segment_name}</b>   "
                f"price {format_pct(row.price_change_pct, 1, signed=True)}, "
                f"volume {format_pct(row.expected_volume_change_pct, 1, signed=True)}"
            ),
            showarrow=False,
            font={"family": FONT_BODY, "size": 14, "color": INK},
        )
    figure.update_layout(
        title="Recommended price step: expected 12-month change in gross profit", height=420
    )
    apply_business_theme(figure, mono_axis="x")
    figure.update_yaxes(
        showticklabels=False, showgrid=False, zeroline=False, range=[-0.5, len(ordered) - 0.15]
    )
    figure.update_xaxes(
        title="TRY m, constant 2025 prices; the line shows the range from the elasticity's "
        "95% confidence interval",
        range=[min(0.0, float(low.min()) * 1.1), float(high.max()) * 1.06],
        showgrid=True,
        gridcolor=GRID,
        zeroline=True,
        zerolinecolor=SLATE_SOFT,
    )
    return figure
