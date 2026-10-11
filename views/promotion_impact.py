"""Promotion impact: the difference-in-differences method."""

import streamlit as st

from dashboard_support import (
    load_pricing_config,
    load_promotion_results,
    page_intro,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import promo_insight
from energy_market_intelligence.localization import format_pct
from energy_market_intelligence.pricing_visualization import (
    promo_estimate_figure,
    promo_trend_figure,
)

page_intro(
    "views/promotion_impact.py",
    "How much extra volume the discount promotion really created, measured by comparing how "
    "volume changed from before to during the promotion in provinces with it and in provinces "
    "without it (difference-in-differences, DiD). Promotion: an extra discount, January to "
    "April 2025.",
)
estimates, trend = load_promotion_results()
promo = load_pricing_config().promotion
by_method = estimates.set_index("method")
adjusted = by_method.loc["price_adjusted"]
naive = by_method.loc["naive"]

cards = st.columns(3)
cards[0].metric(
    "Extra volume: our estimate",
    format_pct(adjusted["uplift"]),
    f"Likely range: {format_pct(adjusted['ci_low'])} to {format_pct(adjusted['ci_high'])}",
    delta_color="off",
    delta_arrow="off",
    help=f"Extra volume the promotion created on top of what its "
    f"{format_pct(promo.promo_discount_pct, 0)} lower price alone would sell; list-price "
    "differences between provinces are also taken out.",
)
cards[1].metric(
    "Extra volume: simple comparison",
    format_pct(naive["uplift"]),
    help="Change in the promotion provinces minus change in the others, before vs during the "
    "promotion, without taking price into account. Too high, because cheaper power sells more "
    "anyway.",
)
cards[2].metric(
    "Extra volume: true value",
    format_pct(adjusted["true_uplift"]),
    help="The effect built into the synthetic data, so the two estimates can be checked.",
)
takeaway(promo_insight(estimates))

show_chart(promo_trend_figure(trend, (promo.start_month_id, promo.end_month_id)))
st.caption(
    f"The promotion ran in {adjusted['treated_regions']} provinces; "
    f"{adjusted['control_regions']} provinces without it are the control group. 100 is each "
    "group's average month before the promotion (dotted line); the swings are seasonal. The gap "
    "between the lines during the promotion is the simple comparison "
    f"({format_pct(naive['uplift'])}); taking out the effect of the lower price leaves "
    f"{format_pct(adjusted['uplift'])}. Months after the promotion are left out."
)
show_chart(promo_estimate_figure(estimates))
st.caption(
    "The line around each estimate is its 95% confidence interval; the diamond is the true "
    "value. The simple comparison overstates the effect, because it also counts the effect "
    "of the promotion discount and the list-price increases on volume. This page measures extra "
    "volume, not profit."
)
show_table(
    estimates[["method", "uplift", "true_uplift", "truth_in_ci", "ci_low", "ci_high"]],
    fractions={"uplift", "ci_low", "ci_high", "true_uplift"},
)
with st.expander("Method and assumptions"):
    st.markdown(
        """
- Before: the months before the promotion. After: the promotion months. Later months are left
  out.
- Price-adjusted model: two-way fixed effects (province × product × segment, and month), a
  pocket-price slope for each segment and the competitor price; standard errors are clustered
  by province.
- Key assumption: without the promotion, and once price is taken into account, the promotion
  and control provinces would have moved in parallel. The provinces were chosen by the data
  generator, not at random, so this assumption must be checked on real data.
        """
    )
