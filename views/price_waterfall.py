"""Price waterfall: from list price to pocket price, and the discount-policy check."""

import plotly.express as px
import streamlit as st

from dashboard_support import (
    breach,
    load_view,
    page_intro,
    select_regions,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import price_waterfall_insight
from energy_market_intelligence.localization import (
    SEGMENT_ORDER,
    format_number,
    format_pct,
    format_try,
)
from energy_market_intelligence.pricing_visualization import (
    DEDUCTION_LABELS,
    INVOICE_LABEL,
    price_waterfall_figure,
    segment_waterfall_table,
)
from energy_market_intelligence.visualization import (
    LEAK_RED,
    NAVY,
    apply_business_theme,
)

page_intro(
    "views/price_waterfall.py",
    "How the list price of one MWh of electricity comes down to the price the company really "
    "keeps (the pocket price) once discounts, rebates, payment terms and service costs are "
    "taken off. Data: 2025.",
)
detail = load_view("vw_price_waterfall")
flags = load_view("vw_discount_policy_flags")
regions = select_regions(detail, key="waterfall_regions")
selected = detail[detail["region_name"].isin(regions)]
if selected.empty:
    st.info("Select at least one province.")
    st.stop()

list_revenue = selected["list_revenue"].sum()
pocket_revenue = selected["pocket_revenue"].sum()
volume = selected["volume_mwh"].sum()
selected_flags = flags[flags["region_name"].isin(regions)]
cards = st.columns(4)
cards[0].metric(
    "List price (TRY/MWh)",
    format_number(list_revenue / volume, 0),
    help="Volume-weighted average list price.",
)
cards[1].metric(
    "Pocket price (TRY/MWh)",
    format_number(pocket_revenue / volume, 0),
    help="Volume-weighted price left after all discounts and cost items are taken off.",
)
cards[2].metric(
    "Price realisation",
    format_pct(pocket_revenue / list_revenue),
    help="Pocket revenue / revenue at list price.",
)
cards[3].metric(
    "Discount above policy",
    format_try(selected_flags["revenue_leakage_above_policy"].sum()),
    help="Yearly amount of discount given above the limit allowed for each segment.",
)
takeaway(price_waterfall_insight(selected, selected_flags))

show_chart(price_waterfall_figure(selected))
st.caption(
    "Navy bars show the list price and the subtotals (invoice price, net price); red bars show "
    "the items taken off the price. The vertical axis does not start at zero, so the "
    "differences stay readable."
)

st.header("Are discounts within policy?")
available = [name for name in SEGMENT_ORDER if name in set(flags["customer_segment_name"])]
segment = st.selectbox("Customer segment", available)
view = selected_flags[selected_flags["customer_segment_name"] == segment].sort_values(
    "excess_discount_pp", ascending=False
)
status = view["exceeds_policy"].map({True: "Above the policy limit", False: "Within the limit"})
figure = px.bar(
    view.assign(status=status),
    x="region_name",
    y="on_invoice_discount_pct",
    color="status",
    color_discrete_map={"Above the policy limit": LEAK_RED, "Within the limit": NAVY},
    title=f"{segment}: on-invoice discount by province and the policy limit",
    labels={
        "on_invoice_discount_pct": "Discount (% of list price)",
        "region_name": "Province",
    },
)
figure.update_layout(legend_title=None)
figure.add_hline(
    y=float(view["policy_max_discount_pct"].iloc[0]),
    line_dash="dash",
    annotation_text="policy limit",
)
figure.update_yaxes(tickformat=".0%")
apply_business_theme(figure, y_title="Discount (% of list price)")
figure.update_xaxes(title=None)
show_chart(figure)

breaches = selected_flags[selected_flags["exceeds_policy"]].sort_values(
    "revenue_leakage_above_policy", ascending=False
)
if breaches.empty:
    st.caption("In the selected provinces no segment goes above the discount policy limit.")
else:
    breach(
        f"{len(breaches)} province and customer-group combinations give discounts above the "
        "policy limit. "
        "Discount above policy = (discount rate - policy limit) x revenue at list price."
    )
show_table(
    breaches[
        [
            "customer_segment_name",
            "region_name",
            "on_invoice_discount_pct",
            "policy_max_discount_pct",
            "excess_discount_pp",
            "revenue_leakage_above_policy",
        ]
    ].assign(excess_discount_pp=lambda frame: frame["excess_discount_pp"] * 100),
    fractions={"on_invoice_discount_pct", "policy_max_discount_pct"},
)
with st.expander("Waterfall per MWh by segment"):
    show_table(
        segment_waterfall_table(selected).rename(
            columns={
                "on_invoice_discount": f"{DEDUCTION_LABELS['on_invoice_discount']} (TRY/MWh)",
                "invoice_price": f"{INVOICE_LABEL} (TRY/MWh)",
                "off_invoice_rebate": f"{DEDUCTION_LABELS['off_invoice_rebate']} (TRY/MWh)",
                "payment_term_cost": f"{DEDUCTION_LABELS['payment_term_cost']} (TRY/MWh)",
                "freight_service_cost": f"{DEDUCTION_LABELS['freight_service_cost']} (TRY/MWh)",
            }
        )
    )
