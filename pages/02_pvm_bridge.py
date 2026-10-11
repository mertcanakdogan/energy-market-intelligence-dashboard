"""Price-volume-mix bridge Streamlit page."""

import streamlit as st

from dashboard_support import format_compact, load_view, page_intro
from energy_market_intelligence.pricing_visualization import pvm_bridge_figure

page_intro(
    "PVM Bridge",
    "Why did net revenue and gross profit change? Latest 12 months versus the prior 12.",
)
summary = load_view("vw_pvm_bridge_summary")
cells = load_view("vw_pvm_bridge")
row = summary.iloc[0]

cards = st.columns(4)
cards[0].metric("Net revenue change", format_compact(row["total_revenue_change"]))
cards[1].metric("Price effect", format_compact(row["price_effect"]))
cards[2].metric("Gross profit change", format_compact(row["total_gp_change"]))
cards[3].metric("Unit-cost effect", format_compact(row["gp_cost_effect"]))

st.plotly_chart(pvm_bridge_figure(summary), width="stretch")
largest_gap = cells[["reconciliation_gap", "gp_reconciliation_gap"]].abs().max().max()
st.info(
    "Volume = change in total volume at prior mix and price. Mix = shift between product x "
    "segment cells at prior prices. Price = change in net (pocket) price on current volume. "
    "Gross profit adds a unit-cost effect. The components sum exactly to the total change; "
    f"the largest reconciliation gap is {largest_gap:.1e}."
)

st.subheader("Product x segment detail")
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
st.dataframe(detail, hide_index=True, width="stretch")
