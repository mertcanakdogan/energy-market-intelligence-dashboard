"""Market Performance Streamlit page."""

import plotly.express as px
import streamlit as st

from dashboard_support import load_view, page_intro, select_regions

page_intro("Market Performance", "Growth, volume, and share viewed across time and geography.")
regional = load_view("vw_market_metrics")
companies = load_view("vw_company_monthly")
selected_regions = select_regions(regional, key="market_regions")
minimum = regional["date"].min().date()
maximum = regional["date"].max().date()
date_range = st.sidebar.slider("Date range", minimum, maximum, (minimum, maximum))

filtered = regional[
    regional["region_name"].isin(selected_regions)
    & regional["date"].dt.date.between(date_range[0], date_range[1])
]
company_filtered = companies[
    companies["region_name"].isin(selected_regions)
    & companies["date"].dt.date.between(date_range[0], date_range[1])
]
monthly = filtered.groupby("date", as_index=False)[
    ["market_volume_mwh", "northstar_volume_mwh"]
].sum()
monthly["northstar_share"] = monthly["northstar_volume_mwh"] / monthly["market_volume_mwh"]

left, right = st.columns(2)
left.plotly_chart(
    px.line(
        monthly,
        x="date",
        y="market_volume_mwh",
        title="How is total market volume changing?",
        labels={"market_volume_mwh": "Market volume (MWh)"},
    ),
    width="stretch",
)
share_figure = px.line(
        monthly,
        x="date",
        y="northstar_share",
        title="Is Northstar gaining share?",
        labels={"northstar_share": "Northstar share"},
    )
share_figure.update_yaxes(tickformat=".1%")
right.plotly_chart(share_figure, width="stretch")

company_summary = (
    company_filtered.groupby("company_name", as_index=False)["company_volume_mwh"]
    .sum()
    .sort_values("company_volume_mwh", ascending=False)
)
region_summary = filtered.groupby("region_name", as_index=False).agg(
    market_volume_mwh=("market_volume_mwh", "sum"),
    northstar_volume_mwh=("northstar_volume_mwh", "sum"),
)
region_summary["northstar_share"] = (
    region_summary["northstar_volume_mwh"] / region_summary["market_volume_mwh"]
)
left, right = st.columns(2)
left.plotly_chart(
    px.bar(
        company_summary,
        x="company_name",
        y="company_volume_mwh",
        title="Which companies hold the most volume?",
        labels={"company_volume_mwh": "Volume (MWh)", "company_name": "Company"},
    ),
    width="stretch",
)
regional_figure = px.scatter(
        region_summary,
        x="market_volume_mwh",
        y="northstar_share",
        text="region_name",
        title="Where does market scale differ from Northstar share?",
        labels={"market_volume_mwh": "Market volume (MWh)", "northstar_share": "Northstar share"},
    )
regional_figure.update_yaxes(tickformat=".1%")
right.plotly_chart(regional_figure, width="stretch")

st.subheader("Regional monthly diagnostics")
st.dataframe(filtered.sort_values("date", ascending=False), hide_index=True, width="stretch")
