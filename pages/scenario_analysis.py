"""Scenario Analysis Streamlit page."""

import pandas as pd
import streamlit as st

from dashboard_support import format_compact, load_elasticities, load_view, page_intro
from energy_market_intelligence.scenario import (
    scenario_for_selection,
    volume_response_from_elasticity,
)

page_intro("Scenario Analysis", "Transparent what-if arithmetic; this page is not a forecast.")
st.warning(
    "This simulator evaluates arithmetic consequences of assumptions; "
    "it is not a causal demand model. "
    "The volume response is either a user-defined assumption or implied by an estimated "
    "elasticity, which is itself uncertain."
)
baseline = load_view("vw_northstar_profitability_monthly")
elasticities = load_elasticities().set_index("customer_segment_name")
region = st.selectbox("Region", sorted(baseline["region_name"].unique()))
product = st.selectbox("Product segment", sorted(baseline["product_segment"].unique()))
price_change = st.slider("Price change %", -20.0, 20.0, 0.0, 0.5)
cost_change = st.slider("Variable cost change %", -20.0, 20.0, 0.0, 0.5)

mode = st.radio(
    "Volume response",
    ["Estimated elasticity", "Manual override"],
    horizontal=True,
    help="Estimated elasticity uses the log-log model on the Price Elasticity page.",
)
if mode == "Estimated elasticity":
    segment = st.selectbox("Customer segment (elasticity source)", list(elasticities.index))
    elasticity = float(elasticities.loc[segment, "elasticity"])
    volume_response = volume_response_from_elasticity(price_change, elasticity)
    st.caption(
        f"{segment}: elasticity {elasticity:.2f} (95% CI "
        f"{elasticities.loc[segment, 'ci_low']:.2f} to {elasticities.loc[segment, 'ci_high']:.2f}) "
        f"implies a volume response of {volume_response:+.2f}% "
        f"for a {price_change:+.1f}% price move."
    )
else:
    volume_response = st.slider("Expected volume response % (user-defined)", -25.0, 25.0, 0.0, 0.5)

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

if mode == "Estimated elasticity":
    st.subheader("Sensitivity to elasticity uncertainty")
    rows = []
    for label, value in (
        ("Lower bound (more elastic)", float(elasticities.loc[segment, "ci_low"])),
        ("Point estimate", elasticity),
        ("Upper bound (less elastic)", float(elasticities.loc[segment, "ci_high"])),
    ):
        response = volume_response_from_elasticity(price_change, value)
        outcome = scenario_for_selection(
            baseline, region, product, price_change, response, cost_change
        )
        rows.append(
            {
                "Elasticity": label,
                "Value": value,
                "Volume response %": response,
                "Gross profit change": outcome["gross_profit_delta"],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

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
st.caption(
    "Elasticity mode: volume response % = ((1 + price change %) ^ elasticity − 1) × 100. "
    "The elasticity is estimated per customer segment on the pricing ledger and applied here to "
    "the selected region and product baseline."
)
