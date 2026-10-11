"""Landing page for the Northstar Energy pricing and revenue analytics case study."""

import streamlit as st

from dashboard_support import format_compact, load_elasticities, load_view

st.set_page_config(
    page_title="Northstar Energy | Pricing & Revenue Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px;}
    [data-testid="stMetric"] {border-top: 2px solid #1f4e79; padding-top: 0.7rem;}
    h1, h2, h3 {color: #20364d;}
    div[data-testid="stCaptionContainer"] {color: #52606d;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Northstar Energy: Pricing & Revenue Analytics")
st.subheader("Where should Northstar change prices, and what is it worth?")
st.write(
    "A portfolio case study on a fully synthetic energy retailer. Because the data are "
    "generated, the true price elasticities and promotion uplift are known, so every estimate "
    "on these pages can be checked against the truth. Start with the pricing pages; the "
    "market-intelligence pages below them cover growth, competition, and regional priorities."
)

waterfall = load_view("vw_price_waterfall")
pvm = load_view("vw_pvm_bridge_summary").iloc[0]
elasticities = load_elasticities()
list_revenue = waterfall["list_revenue"].sum()
pocket_revenue = waterfall["pocket_revenue"].sum()
flags = load_view("vw_discount_policy_flags")

cards = st.columns(4)
cards[0].metric("Price realization", f"{pocket_revenue / list_revenue:.1%}")
cards[1].metric(
    "Discount above policy",
    format_compact(flags["revenue_leakage_above_policy"].sum()),
    f"{int(flags['exceeds_policy'].sum())} region-segment cells",
    delta_color="off",
)
cards[2].metric("Gross profit change (YoY)", format_compact(pvm["total_gp_change"]))
cards[3].metric(
    "Elasticities recovered",
    f"{int(elasticities['truth_in_ci'].sum())} of {len(elasticities)}",
    "true value inside 95% CI",
    delta_color="off",
)

st.markdown("### Pricing pages")
st.page_link("pages/01_price_waterfall.py", label="Price Waterfall: list to pocket price")
st.page_link("pages/02_pvm_bridge.py", label="PVM Bridge: price, volume, mix, cost")
st.page_link("pages/03_elasticity.py", label="Price Elasticity: estimates vs known truth")
st.page_link("pages/04_promotion_impact.py", label="Promotion Impact: difference-in-differences")
st.page_link("pages/05_price_recommendation.py", label="Price Recommendation: decision aid")

st.info(
    "All data and business logic in this repository are newly designed for a public demonstration. "
    "The application does not make automated commercial decisions."
)
