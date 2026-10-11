"""Price recommendation Streamlit page."""

import streamlit as st

from dashboard_support import (
    format_compact,
    load_elasticities,
    load_pricing_config,
    load_view,
    page_intro,
)
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_visualization import price_recommendation_figure

page_intro(
    "Price Recommendation",
    "Decision aid: how far could pocket prices move, and what would it be worth?",
)
st.warning(
    "This is a decision aid, not an automated pricing rule. It assumes a constant estimated "
    "elasticity, no competitor reaction and unchanged unit costs, and it is only meaningful "
    "for small price steps."
)
defaults = load_pricing_config().recommendation
st.sidebar.header("Guard rails")
max_step = st.sidebar.slider(
    "Max price step (%)", 1.0, 15.0, defaults.max_price_step_pct * 100, 0.5
)
margin_floor = st.sidebar.slider(
    "Margin floor (%)", 0.0, 40.0, defaults.margin_floor_pct * 100, 0.5
)
volume_guard = st.sidebar.slider(
    "Max volume loss (%)", 1.0, 20.0, defaults.max_volume_loss_pct * 100, 0.5
)
level = st.sidebar.radio("Level of detail", ["Customer segment", "Segment x region"])

baseline = load_view("vw_price_waterfall")
elasticities = load_elasticities()
guard_rails = {
    "max_step": max_step / 100,
    "margin_floor": margin_floor / 100,
    "max_volume_loss": volume_guard / 100,
}
by_segment = recommend_prices(baseline, elasticities, **guard_rails)
if level == "Customer segment":
    group = ["customer_segment_name"]
    table = by_segment
else:
    group = ["customer_segment_name", "region_name"]
    table = recommend_prices(baseline, elasticities, **guard_rails, group_columns=group)

total_change = table["expected_gross_profit_change"].sum()
weighted_price = (table["price_change_pct"] * table["baseline_volume_mwh"]).sum()
cards = st.columns(3)
cards[0].metric(
    "Expected gross-profit change",
    format_compact(total_change),
    f"{total_change / table['baseline_gross_profit'].sum():+.1%}",
)
cards[1].metric(
    "Volume-weighted price change",
    f"{weighted_price / table['baseline_volume_mwh'].sum():+.2%}",
)
cards[2].metric(
    "Groups that cannot reach the margin floor",
    int(table["binding_constraint"].str.contains("not reachable").sum()),
)

st.plotly_chart(price_recommendation_figure(by_segment), width="stretch")
st.dataframe(
    table.sort_values("expected_gross_profit_change", ascending=False)[
        [
            *group,
            "current_pocket_price",
            "unit_variable_cost",
            "current_margin_pct",
            "elasticity",
            "price_change_pct",
            "expected_volume_change_pct",
            "expected_gross_profit_change",
            "gross_profit_change_low",
            "gross_profit_change_high",
            "binding_constraint",
        ]
    ],
    hide_index=True,
    width="stretch",
)
with st.expander("Rules applied"):
    st.markdown(
        """
1. Elastic segments (elasticity below -1): target the profit-maximising pocket price
   `c * e / (1 + e)`. Inelastic segments: target the largest allowed step.
2. Limit every move to the max price step.
3. Limit increases to the price at which expected volume loss equals the volume-loss guard.
4. Enforce the pocket-margin floor last; it wins over the volume guard. If the floor cannot be
   reached within the step cap, the full step is recommended and the group is flagged.

Expected volume change = `(1 + price change) ^ elasticity - 1`. Gross-profit whiskers use the
95% confidence bounds of the elasticity estimate.
        """
    )
