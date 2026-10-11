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
    PORTFOLIO,
    bill_waterfall_figure,
    portfolio_bill,
    segment_waterfall_table,
)
from energy_market_intelligence.visualization import (
    FONT_BODY,
    GRID,
    INK,
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
    st.info("Select at least one province in the menu.")
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
    "Leakage rate",
    format_pct(1 - pocket_revenue / list_revenue),
    help="The share of the list price that the company does not keep: "
    "1 \u2212 pocket price / list price.",
)
cards[3].metric(
    "Discount above policy",
    format_try(selected_flags["revenue_leakage_above_policy"].sum()),
    help="Yearly amount of discount given above the limit allowed for each segment.",
)
takeaway(price_waterfall_insight(selected, selected_flags))

segments = [name for name in SEGMENT_ORDER if name in set(selected["customer_segment_name"])]
scope = st.segmented_control(
    "Show the price breakdown for", [PORTFOLIO, *segments], default=PORTFOLIO, key="bill_scope"
)
scope = scope or PORTFOLIO
bill = portfolio_bill(selected, None if scope == PORTFOLIO else scope)
figure = bill_waterfall_figure(bill)
figure.update_layout(title=f"From list price to pocket price: {scope} (TRY/MWh, 2025)")
show_chart(figure)
st.caption(
    "Navy bars show the list price and the pocket price; red bars show the items taken off the "
    "price. The axis does not start at zero, so the differences stay readable."
)

st.header("Are discounts within policy?")
available = [name for name in SEGMENT_ORDER if name in set(flags["customer_segment_name"])]
segment = st.segmented_control(
    "Customer segment", available, default=available[0], key="policy_segment"
)
segment = segment or available[0]
view = selected_flags[selected_flags["customer_segment_name"] == segment].sort_values(
    "excess_discount_pp", ascending=False
)
status = view["exceeds_policy"].map({True: "Above the policy limit", False: "Within the limit"})
# Horizontal bars: every province keeps its name on a phone, highest discount on top.
figure = px.bar(
    view.assign(status=status),
    x="on_invoice_discount_pct",
    y="region_name",
    orientation="h",
    color="status",
    color_discrete_map={"Above the policy limit": LEAK_RED, "Within the limit": NAVY},
    title=f"{segment}: on-invoice discount by province and the policy limit",
    labels={
        "on_invoice_discount_pct": "Discount (% of list price)",
        "region_name": "Province",
    },
)
figure.update_layout(legend_title=None, height=40 + 26 * len(view) + 120, bargap=0.3)
figure.add_vline(
    x=float(view["policy_max_discount_pct"].iloc[0]),
    line_dash="dash",
    line_color=INK,
    annotation_text="policy limit",
    annotation_position="bottom right",
)
apply_business_theme(figure, y_title=None, mono_axis="x")
figure.update_xaxes(
    title="Discount (% of list price)", tickformat=".0%", showgrid=True, gridcolor=GRID
)
figure.update_yaxes(
    categoryorder="array",
    categoryarray=view["region_name"].tolist()[::-1],
    showgrid=False,
    tickfont={"family": FONT_BODY, "size": 13, "color": INK},
)
show_chart(figure)

breaches = selected_flags[selected_flags["exceeds_policy"]].sort_values(
    "revenue_leakage_above_policy", ascending=False
)
if breaches.empty:
    st.caption("In the selected provinces no segment goes above the discount policy limit.")
else:
    breach(
        f"Across all segments, {len(breaches)} combinations of province and customer segment "
        "give discounts above the policy limit. Discount above policy = (discount rate − "
        "policy limit) × revenue at list price."
    )
    # The money column comes straight after the names, so it stays visible on a phone.
    show_table(
        breaches[
            [
                "customer_segment_name",
                "region_name",
                "revenue_leakage_above_policy",
                "on_invoice_discount_pct",
                "policy_max_discount_pct",
                "excess_discount_pp",
            ]
        ]
        .assign(excess_discount_pp=lambda frame: frame["excess_discount_pp"] * 100)
        .rename(columns={"revenue_leakage_above_policy": "Above policy (TRY)"}),
        fractions={"on_invoice_discount_pct", "policy_max_discount_pct"},
    )
with st.expander("Price breakdown per MWh by segment (table)"):
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
