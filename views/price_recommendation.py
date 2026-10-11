"""Price recommendation: a bounded, margin-floored decision-support calculation."""

import streamlit as st

from dashboard_support import (
    load_elasticities,
    load_pricing_config,
    load_view,
    note,
    page_intro,
    percent_slider,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import recommendation_insight
from energy_market_intelligence.localization import format_number, format_pct, format_try
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_visualization import price_recommendation_figure

page_intro(
    "views/price_recommendation.py",
    "How far the pocket price (the price the company keeps after discounts) of each customer "
    "segment could change, and the estimated effect on gross profit. Open “Change the "
    "limits” to see how the result changes.",
)
defaults = load_pricing_config().recommendation
# The limits sit on the page, not in the sidebar: on a phone the sidebar is hidden.
with st.expander("Change the limits"):
    limits = st.columns(3, gap="medium")
    with limits[0]:
        max_step = percent_slider(
            "Largest price step",
            1.0,
            15.0,
            defaults.max_price_step_pct * 100,
            signed=False,
            help="The pocket price changes by at most this much in one step.",
        )
    with limits[1]:
        margin_floor = percent_slider(
            "Margin floor",
            0.0,
            40.0,
            defaults.margin_floor_pct * 100,
            signed=False,
            help="The pocket margin at the recommended price does not fall below this value "
            "(if it can be reached).",
        )
    with limits[2]:
        volume_guard = percent_slider(
            "Largest volume loss",
            1.0,
            20.0,
            defaults.max_volume_loss_pct * 100,
            signed=False,
            help="A price rise is capped so that the expected volume loss stays within this limit.",
        )

baseline = load_view("vw_price_waterfall")
elasticities = load_elasticities()
guard_rails = {
    "max_step": max_step / 100,
    "margin_floor": margin_floor / 100,
    "max_volume_loss": volume_guard / 100,
}
table = recommend_prices(baseline, elasticities, **guard_rails)

total_change = table["expected_gross_profit_change"].sum()
weighted_price = (table["price_change_pct"] * table["baseline_volume_mwh"]).sum()
cards = st.columns(3)
cards[0].metric(
    "Expected gross profit change",
    format_try(total_change, signed=True),
    format_pct(total_change / table["baseline_gross_profit"].sum(), 1, signed=True),
    help="Estimated change in yearly gross profit if the recommended price steps are applied.",
)
cards[1].metric(
    "Average price change",
    format_pct(weighted_price / table["baseline_volume_mwh"].sum(), 1, signed=True),
    help="Volume-weighted average change in the pocket price.",
)
cards[2].metric(
    "Segments below the margin floor",
    int(table["binding_constraint"].str.contains("not reachable").sum()),
    help="Number of segments that cannot reach the margin floor in one price step.",
)
takeaway(recommendation_insight(table))

figure = price_recommendation_figure(table)
figure.update_xaxes(title="TRY m, constant 2025 prices")  # the long export title is cut on phones
show_chart(figure)
st.caption(
    "Bar: expected change in yearly gross profit. Line: the range that follows from the 95% "
    "confidence interval of the price elasticity."
)
note(
    "This is a decision-support calculation, not an automatic pricing rule. It assumes a "
    "constant estimated elasticity, no reaction from competitors and an unchanged unit cost; "
    "it only makes sense for small price steps.",
    label="Assumptions",
)
# The answer first (the gross profit change and its range), then the step behind it.
columns = [
    "expected_gross_profit_change",
    "gross_profit_range",
    "price_change_pct",
    "expected_volume_change_pct",
    "current_pocket_price",
    "current_margin_pct",
    "binding_constraint",
]


def with_range(frame):
    """One readable range column instead of separate low and high columns."""

    low = frame["gross_profit_change_low"].map(lambda value: format_number(value / 1e6, 1))
    high = frame["gross_profit_change_high"].map(lambda value: format_number(value / 1e6, 1))
    return frame.assign(gross_profit_range=low + " to " + high)


fractions = {"current_margin_pct", "price_change_pct", "expected_volume_change_pct"}
show_table(
    with_range(table).sort_values("expected_gross_profit_change", ascending=False)[
        ["customer_segment_name", *columns]
    ],
    fractions=fractions,
)
with st.expander("Recommendation by segment and province"):
    group = ["customer_segment_name", "region_name"]
    by_province = recommend_prices(baseline, elasticities, **guard_rails, group_columns=group)
    show_table(
        with_range(by_province).sort_values("expected_gross_profit_change", ascending=False)[
            [*group, *columns]
        ],
        fractions=fractions,
    )
with st.expander("Rules applied"):
    st.markdown(
        """
1. For elastic segments (elasticity below −1) the target is the pocket price that maximises
   profit: `c * e / (1 + e)` (c: unit cost, e: elasticity). For inelastic segments the target
   is the largest allowed rise.
2. Every change is capped at the largest price step.
3. A price rise is capped at the price where the expected volume loss reaches the volume-loss
   limit.
4. The margin floor is applied last and takes priority over the volume limit. If it cannot be
   reached in one step, the full step is recommended and the group is flagged.

Expected volume change = `(1 + price change) ^ elasticity - 1`. The gross profit range uses the
95% confidence limits of the elasticity estimate.
        """
    )
