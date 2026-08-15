"""Regional Opportunity Streamlit page."""

import streamlit as st

from dashboard_support import load_config, load_view, page_intro
from energy_market_intelligence.opportunity import calculate_opportunity_scores
from energy_market_intelligence.visualization import opportunity_matrix_figure

page_intro("Regional Opportunity", "Explainable prioritisation for analyst review.")
st.info(
    "This is a transparent analytical prioritisation heuristic for demonstration purposes, "
    "not a causal model or automated decision rule."
)
config = load_config()
opportunity = calculate_opportunity_scores(
    load_view("vw_regional_opportunity_inputs"), config["opportunity_weights"]
)

minimum_score = st.sidebar.slider("Minimum opportunity score", 0, 100, 0)
sort_by = st.sidebar.selectbox(
    "Sort by", ["opportunity_score", "market_growth", "northstar_share", "gross_margin_pct"]
)
filtered = opportunity[opportunity["opportunity_score"] >= minimum_score].sort_values(
    sort_by, ascending=False
)
st.plotly_chart(opportunity_matrix_figure(filtered), width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Top opportunities")
    st.dataframe(filtered.head(5), hide_index=True, width="stretch")
with right:
    st.subheader("Risk / declining signals")
    risks = opportunity.sort_values(["market_growth", "share_momentum"]).head(5)
    st.dataframe(
        risks[["region_name", "market_growth", "share_momentum", "gross_margin_pct", "hhi"]],
        hide_index=True,
        width="stretch",
    )

st.subheader("Component score breakdown")
components = [
    "region_name",
    "opportunity_score",
    "market_size_score",
    "market_growth_score",
    "share_gap_score",
    "momentum_score",
    "margin_score",
    "competition_score",
]
st.dataframe(filtered[components], hide_index=True, width="stretch")
st.caption(f"Public-demo weights: {config['opportunity_weights']}")
