"""Scenario Analysis Streamlit page."""

import pandas as pd
import streamlit as st

from dashboard_support import format_compact, load_view, page_intro
from energy_market_intelligence.scenario import scenario_for_selection

page_intro("Scenario Analysis", "Transparent what-if arithmetic; this page is not a forecast.")
st.warning(
    "This simulator evaluates arithmetic consequences of assumptions; "
    "it is not a causal demand model. "
    "Any volume response is a user-defined scenario assumption."
)
baseline = load_view("vw_northstar_profitability_monthly")
region = st.selectbox("Region", sorted(baseline["region_name"].unique()))
product = st.selectbox("Product segment", sorted(baseline["product_segment"].unique()))
price_change = st.slider("Price change %", -20.0, 20.0, 0.0, 0.5)
volume_response = st.slider("Expected volume response % (user-defined)", -25.0, 25.0, 0.0, 0.5)
cost_change = st.slider("Variable cost change %", -20.0, 20.0, 0.0, 0.5)

result = scenario_for_selection(
    baseline, region, product, price_change, volume_response, cost_change
)
cards = st.columns(4)
cards[0].metric(
    "Estimated volume",
    f"{format_compact(result['scenario_volume_mwh'])} MWh",
    f"{result['volume_delta']:+,.0f}",
)
cards[1].metric(
    "Estimated revenue",
    format_compact(result["scenario_revenue"]),
    f"{result['revenue_delta']:+,.0f}",
)
cards[2].metric(
    "Estimated gross profit",
    format_compact(result["scenario_gross_profit"]),
    f"{result['gross_profit_delta']:+,.0f}",
)
margin_delta = (result["scenario_gross_margin_pct"] - result["baseline_gross_margin_pct"]) * 100
cards[3].metric(
    "Estimated gross margin",
    f"{result['scenario_gross_margin_pct']:.1%}",
    f"{margin_delta:+.2f} pp",
)

st.subheader("Formula audit")
formula = pd.DataFrame(
    {
        "Metric": ["Volume", "Average price", "Unit variable cost", "Revenue", "Gross profit"],
        "Calculation": [
            "baseline volume × (1 + volume response %)",
            "baseline price × (1 + price change %)",
            "baseline unit cost × (1 + variable cost change %)",
            "scenario volume × scenario price",
            "scenario revenue − scenario variable cost",
        ],
    }
)
st.dataframe(formula, hide_index=True, width="stretch")
