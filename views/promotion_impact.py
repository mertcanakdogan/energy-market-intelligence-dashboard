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
    "How much extra volume the discount promotion really created, measured by comparing "
    "provinces with and without the promotion (difference-in-differences, DiD). Promotion: "
    "January to April 2025.",
)
estimates, trend = load_promotion_results()
promo = load_pricing_config().promotion
by_method = estimates.set_index("method")
adjusted = by_method.loc["price_adjusted"]
naive = by_method.loc["naive"]

cards = st.columns(3)
cards[0].metric(
    "Price-adjusted effect",
    format_pct(adjusted["uplift"]),
    f"95% CI: {format_pct(adjusted['ci_low'])} to {format_pct(adjusted['ci_high'])}",
    delta_color="off",
    delta_arrow="off",
    help="Extra volume left once the effect of the promotion discount and of list-price "
    "differences is taken out.",
)
cards[1].metric(
    "Simple comparison",
    format_pct(naive["uplift"]),
    help="Before/after and with/without-promotion difference; it is too high because it also "
    "includes the effect of price.",
)
cards[2].metric(
    "True effect (data generator)",
    format_pct(adjusted["true_uplift"]),
    help="The true extra-volume effect used to generate the synthetic data.",
)
takeaway(promo_insight(estimates))

show_chart(promo_trend_figure(trend, (promo.start_month_id, promo.end_month_id)))
st.caption(
    f"The promotion ran in {adjusted['treated_regions']} provinces; "
    f"{adjusted['control_regions']} provinces without it are the control group."
)
show_chart(promo_estimate_figure(estimates))
st.caption(
    "The line around each estimate is its 95% confidence interval; the diamond is the true "
    "value. The simple comparison overstates the effect, because it also counts the effect "
    "of the promotion discount and the list-price increases on volume."
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
