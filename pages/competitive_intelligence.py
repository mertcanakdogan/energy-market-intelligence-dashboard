"""Competitive Intelligence Streamlit page."""

import plotly.express as px
import streamlit as st

from dashboard_support import load_view, page_intro
from energy_market_intelligence.visualization import competitor_change_figure

page_intro(
    "Competitive Intelligence",
    "Share momentum and fractional HHI provide analytical context, "
    "not legal or regulatory judgments.",
)
momentum = load_view("vw_competitor_momentum").sort_values("momentum_rank")
ranking = load_view("vw_regional_company_ranking")
concentration = load_view("vw_regional_concentration")

left, right = st.columns(2)
left.plotly_chart(competitor_change_figure(momentum), width="stretch")
share_figure = px.bar(
        momentum.sort_values("current_share"),
        x="current_share",
        y="company_name",
        orientation="h",
        title="Current company share ranking",
        labels={"current_share": "Market share", "company_name": "Company"},
    )
share_figure.update_xaxes(tickformat=".1%")
right.plotly_chart(share_figure, width="stretch")

dominant = ranking.query("company_rank == 1")
left, right = st.columns(2)
left.plotly_chart(
    px.bar(
        concentration.sort_values("hhi"),
        x="hhi",
        y="region_name",
        color="concentration_classification",
        orientation="h",
        title="How concentrated is each regional market?",
        labels={"hhi": "HHI (fractional shares)", "region_name": "Region"},
    ),
    width="stretch",
)
right.plotly_chart(
    px.histogram(
        dominant,
        x="company_name",
        title="Which company leads the most regions?",
        labels={"company_name": "Regional leader"},
    ),
    width="stretch",
)

st.subheader("Regional company ranking")
selected = st.selectbox("Region", sorted(ranking["region_name"].unique()))
st.dataframe(
    ranking[ranking["region_name"] == selected].sort_values("company_rank"),
    hide_index=True,
    width="stretch",
)
