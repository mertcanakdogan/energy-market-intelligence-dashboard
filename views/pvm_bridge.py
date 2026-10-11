"""Revenue bridge: price, volume, mix and cost effects."""

import streamlit as st

from dashboard_support import load_view, note, page_intro, show_chart, show_table, takeaway
from energy_market_intelligence.insights import pvm_insight
from energy_market_intelligence.localization import format_try
from energy_market_intelligence.pricing_visualization import pvm_bridge_figure

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

show_chart(pvm_bridge_figure(summary))
largest_gap = cells[["reconciliation_gap", "gp_reconciliation_gap"]].abs().max().max()
note(
    "Volume: the change in total sales volume (at the old price and mix). "
    "Mix: the change in how volume is split across products and customer segments. "
    "Price: the change in the pocket price (at the new volume). Gross profit also has a unit "
    "cost effect. The parts add up exactly to the total change; the largest reconciliation "
    f"gap is {format_try(largest_gap)}.",
    label="Terms",
)

st.subheader("Detail by product and segment")
detail = cells[
    [
        "product_name",
        "customer_segment_name",
        "prior_volume",
        "current_volume",
        "prior_price",
        "current_price",
        "volume_effect",
        "mix_effect",
        "price_effect",
        "total_revenue_change",
        "gp_cost_effect",
        "total_gp_change",
        "reconciliation_gap",
    ]
].sort_values("total_gp_change")
show_table(detail)
st.caption(
    "PTF is Turkey's day-ahead market price for electricity; the product name "
    '"Index-linked (PTF+)" refers to a tariff linked to it. YEK-G is a renewable-energy '
    "guarantee certificate."
)
