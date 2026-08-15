"""Executive Summary Streamlit page."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_support import format_compact, load_config, load_view, page_intro
from energy_market_intelligence.metrics import generate_management_observations
from energy_market_intelligence.opportunity import calculate_opportunity_scores
from energy_market_intelligence.visualization import (
    gross_margin_trend_figure,
    market_share_trend_figure,
)

page_intro(
    "Executive Summary",
    "Latest 12 months versus the preceding 12 months unless otherwise stated.",
)
kpis = load_view("vw_executive_kpis").iloc[0]
trend = load_view("vw_growth_analysis").sort_values("date")
profit = load_view("vw_northstar_profitability_monthly")
regional = calculate_opportunity_scores(
    load_view("vw_regional_opportunity_inputs"), load_config()["opportunity_weights"]
)
share_change = load_view("vw_regional_share_change")
competitors = load_view("vw_competitor_momentum").sort_values("momentum_rank")

row1 = st.columns(5)
row1[0].metric(
    "Market volume",
    f"{format_compact(kpis['market_volume'])} MWh",
    f"{kpis['market_yoy_growth']:.1%}",
)
row1[1].metric(
    "Northstar volume",
    f"{format_compact(kpis['northstar_volume'])} MWh",
    f"{kpis['northstar_yoy_growth']:.1%}",
)
row1[2].metric(
    "Northstar share", f"{kpis['northstar_market_share']:.1%}", f"{kpis['share_change_pp']:+.2f} pp"
)
row1[3].metric("Gross profit", format_compact(kpis["gross_profit"]))
row1[4].metric(
    "Gross margin", f"{kpis['gross_margin_pct']:.1%}", f"{kpis['gross_margin_change_pp']:+.2f} pp"
)

left, right = st.columns(2)
with left:
    volume = trend.melt(
        id_vars="date",
        value_vars=["market_volume_mwh", "northstar_volume_mwh"],
        var_name="series",
        value_name="volume_mwh",
    )
    volume["series"] = volume["series"].map(
        {"market_volume_mwh": "Total market", "northstar_volume_mwh": "Northstar"}
    )
    figure = px.line(
        volume,
        x="date",
        y="volume_mwh",
        color="series",
        title="Market and Northstar monthly volume",
    )
    figure.update_layout(
        template="plotly_white", legend_title=None, yaxis_title="MWh", xaxis_title=None
    )
    st.plotly_chart(figure, width="stretch")
with right:
    st.plotly_chart(market_share_trend_figure(trend), width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Regional winners and losers")
    winners = share_change.nlargest(3, "share_change_pp")[["region_name", "share_change_pp"]]
    losers = share_change.nsmallest(3, "share_change_pp")[["region_name", "share_change_pp"]]
    comparison = pd.concat([winners.assign(signal="Gain"), losers.assign(signal="Loss")])
    chart = px.bar(
        comparison,
        x="share_change_pp",
        y="region_name",
        color="signal",
        orientation="h",
        title="Northstar share movement by region",
    )
    chart.update_layout(
        template="plotly_white",
        xaxis_title="Percentage points",
        yaxis_title=None,
        legend_title=None,
    )
    st.plotly_chart(chart, width="stretch")
with right:
    st.plotly_chart(gross_margin_trend_figure(profit), width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Competitor momentum")
    st.dataframe(
        competitors[
            ["momentum_rank", "company_name", "current_share", "share_change_pp", "momentum_signal"]
        ].head(5),
        hide_index=True,
        width="stretch",
        column_config={
            "current_share": st.column_config.NumberColumn(format="percent"),
            "share_change_pp": st.column_config.NumberColumn(format="%+.2f pp"),
        },
    )
with right:
    st.subheader("Opportunity Top 5")
    st.dataframe(
        regional[
            [
                "opportunity_rank",
                "region_name",
                "opportunity_score",
                "market_growth",
                "northstar_share",
            ]
        ].head(5),
        hide_index=True,
        width="stretch",
        column_config={
            "opportunity_score": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.1f"
            ),
            "market_growth": st.column_config.NumberColumn(format="percent"),
            "northstar_share": st.column_config.NumberColumn(format="percent"),
        },
    )

st.subheader("Management observations")
observation_kpis = {
    "share_change_pp": float(kpis["share_change_pp"]),
    "market_yoy_growth_pct": float(kpis["market_yoy_growth"]) * 100,
    "gross_margin_change_pp": float(kpis["gross_margin_change_pp"]),
}
for observation in generate_management_observations(observation_kpis, regional):
    st.markdown(f"- {observation}")
