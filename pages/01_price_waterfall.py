"""Price Waterfall Streamlit page."""

import plotly.express as px
import streamlit as st

from dashboard_support import format_compact, load_view, page_intro, select_regions
from energy_market_intelligence.pricing_visualization import (
    price_waterfall_figure,
    segment_waterfall_table,
)

page_intro(
    "Price Waterfall",
    "From list price to pocket price: where does Northstar leak margin? Latest 12 months.",
)
detail = load_view("vw_price_waterfall")
flags = load_view("vw_discount_policy_flags")
regions = select_regions(detail, key="waterfall_regions")
selected = detail[detail["region_name"].isin(regions)]
if selected.empty:
    st.warning("Select at least one region.")
    st.stop()

list_revenue = selected["list_revenue"].sum()
pocket_revenue = selected["pocket_revenue"].sum()
volume = selected["volume_mwh"].sum()
selected_flags = flags[flags["region_name"].isin(regions)]
cards = st.columns(4)
cards[0].metric("List price / MWh", f"{list_revenue / volume:,.2f}")
cards[1].metric("Pocket price / MWh", f"{pocket_revenue / volume:,.2f}")
cards[2].metric("Price realization", f"{pocket_revenue / list_revenue:.1%}")
cards[3].metric(
    "Discount above policy",
    format_compact(selected_flags["revenue_leakage_above_policy"].sum()),
    help="Revenue given away on-invoice beyond each segment's policy discount depth.",
)

st.plotly_chart(price_waterfall_figure(selected), width="stretch")

st.subheader("Is discounting within policy?")
segment = st.selectbox("Customer segment", sorted(flags["customer_segment_name"].unique()))
view = selected_flags[selected_flags["customer_segment_name"] == segment].sort_values(
    "excess_discount_pp", ascending=False
)
figure = px.bar(
    view,
    x="region_name",
    y="on_invoice_discount_pct",
    color="exceeds_policy",
    color_discrete_map={True: "#B84A4A", False: "#2A7F8E"},
    title=f"{segment}: on-invoice discount depth by region vs policy threshold",
    labels={"on_invoice_discount_pct": "Discount (% of list)", "region_name": "Region"},
)
figure.add_hline(
    y=float(view["policy_max_discount_pct"].iloc[0]),
    line_dash="dash",
    annotation_text="policy maximum",
)
figure.update_yaxes(tickformat=".0%")
st.plotly_chart(figure, width="stretch")

breaches = selected_flags[selected_flags["exceeds_policy"]].sort_values(
    "revenue_leakage_above_policy", ascending=False
)
st.caption(
    f"{len(breaches)} region-segment combinations exceed their discount policy. "
    "Leakage above policy = (discount depth - policy maximum) x list revenue."
)
st.dataframe(
    breaches[
        [
            "customer_segment_name",
            "region_name",
            "on_invoice_discount_pct",
            "policy_max_discount_pct",
            "excess_discount_pp",
            "revenue_leakage_above_policy",
        ]
    ],
    hide_index=True,
    width="stretch",
    column_config={
        "on_invoice_discount_pct": st.column_config.NumberColumn("Discount", format="percent"),
        "policy_max_discount_pct": st.column_config.NumberColumn("Policy max", format="percent"),
        "excess_discount_pp": st.column_config.NumberColumn("Excess (pp)", format="%.3f"),
        "revenue_leakage_above_policy": st.column_config.NumberColumn(
            "Leakage above policy", format="localized"
        ),
    },
)
with st.expander("Per-MWh waterfall table"):
    st.dataframe(segment_waterfall_table(selected), hide_index=True, width="stretch")
