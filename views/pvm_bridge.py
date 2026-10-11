"""Revenue bridge: price, volume, mix and cost effects."""

import streamlit as st

from dashboard_support import load_view, note, page_intro, show_chart, show_table, takeaway
from energy_market_intelligence.insights import pvm_insight
from energy_market_intelligence.localization import format_pct, format_try
from energy_market_intelligence.pricing_visualization import pvm_bridge_panel_figures

page_intro(
    "views/pvm_bridge.py",
    "Splits the change in net revenue and gross profit into price, volume, mix and cost "
    "effects. Comparison: 2025 (last 12 months) with 2024 (previous 12 months).",
)
summary = load_view("vw_pvm_bridge_summary")
cells = load_view("vw_pvm_bridge")
row = summary.iloc[0]

prior_revenue = cells["prior_revenue"].sum()
prior_profit = prior_revenue - cells["prior_variable_cost"].sum()
cards = st.columns(4)
cards[0].metric(
    "Net revenue change",
    format_try(row["total_revenue_change"], signed=True),
    f"{format_pct(row['total_revenue_change'] / prior_revenue, 1, signed=True)} vs 2024",
    delta_color="off",
    delta_arrow="off",
    help="Revenue at the pocket price; 2025 minus 2024.",
)
cards[1].metric(
    "Volume effect on revenue",
    format_try(row["volume_effect"], signed=True),
    help="Revenue from selling more (or fewer) MWh, at 2024 prices and mix. The price and mix "
    "effects are in the chart below.",
)
cards[2].metric(
    "Gross profit change",
    format_try(row["total_gp_change"], signed=True),
    f"{format_pct(row['total_gp_change'] / prior_profit, 1, signed=True)} vs 2024",
    delta_color="off",
    delta_arrow="off",
    help="Net revenue minus energy cost; 2025 minus 2024.",
)
cards[3].metric(
    "Unit cost effect on gross profit",
    format_try(row["gp_cost_effect"], signed=True),
    help="Gross profit lost (minus) or gained (plus) because the energy cost per MWh changed; "
    "2025 vs 2024.",
)
takeaway(pvm_insight(summary))

# Two charts side by side on a laptop; Streamlit stacks the columns on a phone.
panels = pvm_bridge_panel_figures(summary)
for column, figure in zip(st.columns(len(panels), gap="medium"), panels, strict=True):
    with column:
        show_chart(figure)
st.caption(
    "Light bars add to the total, grey bars take away from it, the dark bar is the total change. "
    "Both charts use the same scale."
)
largest_gap = cells[["reconciliation_gap", "gp_reconciliation_gap"]].abs().max().max()
closing = (
    "The parts add up exactly to the total change."
    if largest_gap < 1
    else f"The parts add up to the total change within {format_try(largest_gap)}."
)
note(
    "Volume: revenue from selling more MWh, at 2024 prices and mix. Mix: the effect of a shift "
    "in which products and customer segments buy. Price: the effect of the change in pocket "
    "price, on 2025 volumes. Unit cost: gross profit lost because the energy cost per MWh rose. "
    "On gross profit the volume bar is smaller than on revenue, because extra MWh add only their "
    f"margin, not their full price. {closing}",
    label="Terms",
)

st.header("Detail by product and segment")
# The effects first; the volumes and prices behind them stay one click away.
# One name column ("Fixed price · Industrial") keeps the numbers in view on a phone.
ordered = cells.sort_values("total_gp_change").assign(
    product_and_segment=lambda frame: (
        frame["product_name"] + " \u00b7 " + frame["customer_segment_name"]
    )
)
show_table(
    ordered[
        [
            "product_and_segment",
            "total_gp_change",
            "gp_price_effect",
            "gp_cost_effect",
            "gp_volume_effect",
            "gp_mix_effect",
        ]
    ]
)
st.caption(
    "Effects on gross profit, sorted by gross profit change, largest fall first. Price, unit "
    "cost, volume and mix add up to the gross profit change."
)
with st.expander("All effects, volumes and prices"):
    show_table(
        ordered[
            [
                "product_name",
                "customer_segment_name",
                "total_revenue_change",
                "volume_effect",
                "mix_effect",
                "prior_volume",
                "current_volume",
                "prior_price",
                "current_price",
            ]
        ]
    )
st.caption(
    "PTF is Turkey's day-ahead market price for electricity; the product name "
    '"Index-linked (PTF+)" refers to a tariff linked to it. YEK-G is a renewable-energy '
    "guarantee certificate."
)
