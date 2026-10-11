"""Plotly figures for the pricing case study (pipeline PNG exports and Streamlit pages)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from energy_market_intelligence.visualization import (
    ACCENT_TEAL,
    NEGATIVE_RED,
    NORTHSTAR_BLUE,
    apply_business_theme,
)

AMBER = "#C98A1B"
WATERFALL_STEPS = (
    ("List price", "list_price", "absolute"),
    ("On-invoice discount", "on_invoice_discount", "relative"),
    ("Invoice price", "invoice_price", "total"),
    ("Off-invoice rebate", "off_invoice_rebate", "relative"),
    ("Payment terms", "payment_term_cost", "relative"),
    ("Freight & service", "freight_service_cost", "relative"),
    ("Pocket price", "pocket_price", "total"),
)
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
    return totals[["customer_segment_name", "volume_mwh", *AMOUNT_COLUMNS]]


def price_waterfall_figure(waterfall: pd.DataFrame) -> go.Figure:
    """List-to-pocket price waterfall (per MWh) for each customer segment."""

    table = segment_waterfall_table(waterfall)
    segments = table["customer_segment_name"].tolist()
    figure = make_subplots(
        rows=1,
        cols=len(segments),
        subplot_titles=segments,
        shared_yaxes=True,
        horizontal_spacing=0.03,
    )
    for column, row in enumerate(table.itertuples(index=False), start=1):
        levels = [getattr(row, field) for _label, field, _measure in WATERFALL_STEPS]
        # Plotly derives "total" bars from the running sum, so their own y is 0.
        values = [
            0.0 if measure == "total" else (level if measure == "absolute" else -level)
            for (_label, _field, measure), level in zip(WATERFALL_STEPS, levels, strict=True)
        ]
        figure.add_trace(
            go.Waterfall(
                x=[label for label, _field, _measure in WATERFALL_STEPS],
                y=values,
                measure=[measure for _label, _field, measure in WATERFALL_STEPS],
                text=[f"{level:.1f}" for level in levels],
                textposition="outside",
                increasing={"marker": {"color": ACCENT_TEAL}},
                decreasing={"marker": {"color": NEGATIVE_RED}},
                totals={"marker": {"color": NORTHSTAR_BLUE}},
                connector={"line": {"color": "#9CA3AF"}},
                hoverinfo="x+text",
                showlegend=False,
            ),
            row=1,
            col=column,
        )
    figure.update_layout(
        title="Northstar price waterfall by customer segment (per MWh, latest 12 months)"
    )
    apply_business_theme(figure)
    figure.update_xaxes(tickangle=-40, tickfont={"size": 10})
    figure.update_yaxes(
        range=[float(table["pocket_price"].min()) * 0.9, float(table["list_price"].max()) * 1.04]
    )
    figure.update_yaxes(title="Synthetic currency units per MWh (axis truncated)", col=1)
    return figure


def pvm_bridge_figure(summary: pd.DataFrame) -> go.Figure:
    """Price-volume-mix bridge of net revenue and gross profit, latest 12 months vs prior 12."""

    row = summary.iloc[0]
    panels = (
        (
            "Net revenue change",
            [
                ("Volume", row["volume_effect"]),
                ("Mix", row["mix_effect"]),
                ("Price", row["price_effect"]),
            ],
            ("Revenue change", row["total_revenue_change"]),
        ),
        (
            "Gross profit change",
            [
                ("Volume", row["gp_volume_effect"]),
                ("Mix", row["gp_mix_effect"]),
                ("Price", row["gp_price_effect"]),
                ("Unit cost", row["gp_cost_effect"]),
            ],
            ("Gross profit change", row["total_gp_change"]),
        ),
    )
    figure = make_subplots(
        rows=1, cols=2, subplot_titles=[panel[0] for panel in panels], horizontal_spacing=0.1
    )
    for column, (_title, effects, (total_label, total)) in enumerate(panels, start=1):
        values = [value for _, value in effects] + [total]
        figure.add_trace(
            go.Waterfall(
                x=[label for label, _ in effects] + [total_label],
                y=values,
                measure=["relative"] * len(effects) + ["total"],
                text=[f"{value:+,.0f}" for value in values],
                textposition="outside",
                increasing={"marker": {"color": ACCENT_TEAL}},
                decreasing={"marker": {"color": NEGATIVE_RED}},
                totals={"marker": {"color": NORTHSTAR_BLUE}},
                connector={"line": {"color": "#9CA3AF"}},
                hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=column,
        )
    figure.update_layout(title="Northstar price-volume-mix bridge: latest 12 months vs prior 12")
    return apply_business_theme(figure, y_title="Synthetic currency units")


def _interval_trace(
    x: pd.Series, y: pd.Series, low: pd.Series, high: pd.Series, name: str
) -> go.Scatter:
    return go.Scatter(
        x=x,
        y=y,
        mode="markers",
        name=name,
        marker={"color": NORTHSTAR_BLUE, "size": 11},
        error_x={
            "type": "data",
            "symmetric": False,
            "array": high - x,
            "arrayminus": x - low,
            "color": NORTHSTAR_BLUE,
            "thickness": 2.5,
        },
    )


def elasticity_recovery_figure(table: pd.DataFrame) -> go.Figure:
    """Estimated elasticity with 95% CI next to the known true value, per segment."""

    figure = go.Figure()
    figure.add_trace(
        _interval_trace(
            table["elasticity"],
            table["customer_segment_name"],
            table["ci_low"],
            table["ci_high"],
            "Estimate (95% CI)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=table["true_elasticity"],
            y=table["customer_segment_name"],
            mode="markers",
            name="True value (generator)",
            marker={"color": AMBER, "size": 13, "symbol": "diamond"},
        )
    )
    figure.add_vline(x=-1, line_dash="dot", line_color="#9CA3AF", annotation_text="unit elastic")
    figure.update_layout(title="Elasticity recovery: estimate vs known truth")
    apply_business_theme(figure)
    figure.update_xaxes(title="Own-price elasticity of volume (pocket price)", showgrid=True)
    return figure


def promo_did_figure(
    estimates: pd.DataFrame, trend: pd.DataFrame, window: tuple[int, int]
) -> go.Figure:
    """Treated-vs-control volume index and DiD uplift estimates against the true uplift."""

    figure = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.55, 0.45],
        subplot_titles=("Volume index (pre-campaign = 100)", "Estimated uplift vs truth"),
        horizontal_spacing=0.1,
    )
    for name, color in (("control", ACCENT_TEAL), ("treated", NORTHSTAR_BLUE)):
        figure.add_trace(
            go.Scatter(
                x=trend["month_id"],
                y=trend[name],
                mode="lines+markers",
                name=f"{name.capitalize()} regions",
                line={"color": color, "width": 2.5},
                marker={"size": 4},
            ),
            row=1,
            col=1,
        )
    figure.add_vrect(
        x0=window[0] - 0.5,
        x1=window[1] + 0.5,
        fillcolor=AMBER,
        opacity=0.15,
        line_width=0,
        row=1,
        col=1,
    )
    labels = estimates["method"].map({"naive": "Naive DiD", "price_adjusted": "Price-adjusted DiD"})
    figure.add_trace(
        _interval_trace(
            estimates["uplift"] * 100,
            labels,
            estimates["ci_low"] * 100,
            estimates["ci_high"] * 100,
            "Estimate (95% CI)",
        ),
        row=1,
        col=2,
    )
    truth = float(estimates["true_uplift"].iloc[0]) * 100
    figure.add_vline(
        x=truth,
        line_dash="dash",
        line_color=AMBER,
        annotation_text=f"true {truth:.0f}%",
        row=1,
        col=2,
    )
    figure.update_layout(title="Promotion impact: difference-in-differences")
    apply_business_theme(figure)
    figure.update_layout(legend={"orientation": "h", "yanchor": "bottom", "y": 1.1, "x": 0})
    figure.update_xaxes(title="Month", row=1, col=1)
    figure.update_xaxes(title="Volume uplift (%)", row=1, col=2, showgrid=True)
    return figure


def price_recommendation_figure(table: pd.DataFrame) -> go.Figure:
    """Expected 12-month gross-profit change by segment with the elasticity-CI range."""

    ordered = table.sort_values("expected_gross_profit_change")
    labels = [
        f"{row.customer_segment_name}<br>{row.price_change_pct:+.1%} price, "
        f"{row.expected_volume_change_pct:+.1%} volume"
        for row in ordered.itertuples(index=False)
    ]
    expected = ordered["expected_gross_profit_change"]
    figure = go.Figure(
        go.Bar(
            x=expected,
            y=labels,
            orientation="h",
            marker_color=ACCENT_TEAL,
            text=[f"{value / 1e6:+.2f}M" for value in expected],
            textposition="inside",
            insidetextanchor="middle",
            textfont={"color": "white", "size": 15},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": ordered["gross_profit_change_high"] - expected,
                "arrayminus": expected - ordered["gross_profit_change_low"],
                "color": "#4B5563",
                "thickness": 2,
            },
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(title="Recommended price step: expected 12-month gross-profit change")
    apply_business_theme(figure)
    figure.update_layout(margin={"l": 210, "r": 30, "t": 70, "b": 60})
    figure.update_xaxes(
        title="Synthetic currency units (bar = point estimate, whisker = elasticity CI)"
    )
    return figure
