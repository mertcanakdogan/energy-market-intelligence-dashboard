"""Revenue bridge: price, volume, mix and cost effects."""

import streamlit as st

from dashboard_support import load_view, note, page_intro, show_chart, show_table, takeaway
from energy_market_intelligence.insights import pvm_insight
from energy_market_intelligence.localization import format_try
from energy_market_intelligence.pricing_visualization import pvm_bridge_panel_figures

page_intro(
    "views/pvm_bridge.py",
    "Splits the change in net revenue and gross profit into price, volume, mix and cost "
    "effects. Comparison: 2025 (last 12 months) with 2024 (previous 12 months).",
)
summary = load_view("vw_pvm_bridge_summary")
cells = load_view("vw_pvm_bridge")
row = summary.iloc[0]

cards = st.columns(4)
cards[0].metric(
    "Net revenue change",
    format_try(row["total_revenue_change"], signed=True),
    help="Revenue at the pocket price; 2025 minus 2024.",
)
cards[1].metric(
    "Price effect",
    format_try(row["price_effect"], signed=True),
    help="Effect on revenue of the change in pocket price, with volume held fixed.",
)
cards[2].metric(
    "Gross profit change",
    format_try(row["total_gp_change"], signed=True),
    help="Net revenue minus energy cost; 2025 minus 2024.",
)
cards[3].metric(
    "Unit cost effect",
    format_try(row["gp_cost_effect"], signed=True),
    help="Effect on gross profit of the rise (or fall) in energy cost per MWh.",
)
takeaway(pvm_insight(summary))

# Two charts side by side on a laptop; Streamlit stacks the columns on a phone.
panels = pvm_bridge_panel_figures(summary)
for column, figure in zip(st.columns(len(panels), gap="medium"), panels, strict=True):
    with column:
        show_chart(figure)
st.caption("Both charts use the same scale, so equal amounts have equal bar lengths.")
largest_gap = cells[["reconciliation_gap", "gp_reconciliation_gap"]].abs().max().max()
closing = (
    "The parts add up exactly to the total change."
    if largest_gap < 1
    else f"The parts add up to the total change within {format_try(largest_gap)}."
)
note(
    "Volume: the change in total sales volume (at the old price and mix). "
    "Mix: the change in how volume is split across products and customer segments. "
    "Price: the change in the pocket price (at the new volume). Gross profit also has a unit "
    f"cost effect. {closing}",
    label="Terms",
)

st.header("Detail by product and segment")
# The effects first; the volumes and prices behind them stay one click away.
ordered = cells.sort_values("total_gp_change")
show_table(
    ordered[
        [
            "product_name",
            "customer_segment_name",
            "total_gp_change",
            "price_effect",
            "gp_cost_effect",
        ]
    ]
)
st.caption("Sorted by gross profit change, largest fall first.")
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
