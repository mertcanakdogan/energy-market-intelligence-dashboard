"""Profitability Streamlit page."""

import plotly.express as px
import streamlit as st

from dashboard_support import format_compact, load_view, page_intro
from energy_market_intelligence.visualization import gross_margin_trend_figure, profit_bridge_figure

page_intro(
    "Profitability", "Separate commercial volume from the quality of gross profit it generates."
)
monthly = load_view("vw_northstar_profitability_monthly")
summary = load_view("vw_profitability_summary")
bridge = load_view("vw_revenue_bridge")

totals = summary[["volume_mwh", "revenue", "gross_profit"]].sum()
margin = totals["gross_profit"] / totals["revenue"]
profit_per_mwh = totals["gross_profit"] / totals["volume_mwh"]
cards = st.columns(4)
cards[0].metric("Revenue", format_compact(totals["revenue"]))
cards[1].metric("Gross profit", format_compact(totals["gross_profit"]))
cards[2].metric("Gross margin", f"{margin:.1%}")
cards[3].metric("Profit / MWh", f"{profit_per_mwh:,.2f}")

left, right = st.columns(2)
left.plotly_chart(gross_margin_trend_figure(monthly), width="stretch")
region = summary.groupby("region_name", as_index=False)[
    ["volume_mwh", "revenue", "gross_profit"]
].sum()
region["gross_margin_pct"] = region["gross_profit"] / region["revenue"]
region_figure = px.scatter(
        region,
        x="volume_mwh",
        y="gross_margin_pct",
        size="gross_profit",
        text="region_name",
        title="Which regions combine volume and margin?",
        labels={"volume_mwh": "Northstar volume (MWh)", "gross_margin_pct": "Gross margin"},
    )
region_figure.update_yaxes(tickformat=".1%")
right.plotly_chart(region_figure, width="stretch")

left, right = st.columns(2)
product = summary.groupby("product_segment", as_index=False)[
    ["volume_mwh", "revenue", "gross_profit"]
].sum()
product["gross_margin_pct"] = product["gross_profit"] / product["revenue"]
left.plotly_chart(
    px.bar(
        product,
        x="product_segment",
        y="gross_profit",
        color="gross_margin_pct",
        title="Which product segments contribute gross profit?",
        labels={"gross_profit": "Gross profit", "product_segment": "Product segment"},
    ),
    width="stretch",
)
right.plotly_chart(profit_bridge_figure(bridge), width="stretch")

st.caption(
    "The bridge uses base-period volume and price effects plus an interaction term. "
    "It reconciles revenue change and does not claim causality."
)
