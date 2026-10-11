"""Promotion impact Streamlit page."""

import streamlit as st

from dashboard_support import load_pricing_config, load_promotion_results, page_intro
from energy_market_intelligence.pricing_visualization import promo_did_figure

page_intro(
    "Promotion Impact",
    "Difference-in-differences: what extra volume did the discount campaign really create?",
)
estimates, trend = load_promotion_results()
promo = load_pricing_config().promotion
by_method = estimates.set_index("method")
adjusted = by_method.loc["price_adjusted"]
naive = by_method.loc["naive"]

cards = st.columns(3)
cards[0].metric(
    "Price-adjusted uplift",
    f"{adjusted['uplift']:.1%}",
    f"95% CI {adjusted['ci_low']:.1%} to {adjusted['ci_high']:.1%}",
    delta_color="off",
)
cards[1].metric("Naive 2x2 uplift", f"{naive['uplift']:.1%}")
cards[2].metric("True uplift (generator)", f"{adjusted['true_uplift']:.1%}")

st.plotly_chart(
    promo_did_figure(estimates, trend, (promo.start_month_id, promo.end_month_id)),
    width="stretch",
)
st.write(
    f"Treated: {adjusted['treated_regions']} regions; control: {adjusted['control_regions']} "
    f"regions; campaign months {promo.start_month_id}-{promo.end_month_id}. The naive estimate "
    "also counts the volume that the campaign price cut and the staggered list-price "
    "increases would produce on their own, so it overstates the incremental uplift."
)
st.dataframe(estimates, hide_index=True, width="stretch")
with st.expander("Method and assumptions"):
    st.markdown(
        """
- Pre-period: months before the campaign. Post-period: campaign months. Later months are
  excluded.
- Price-adjusted model: two-way fixed effects (region x product x segment and month),
  segment-specific pocket-price slopes and competitor price; standard errors clustered by region.
- Identifying assumption: absent the campaign, treated and control regions would have followed
  parallel trends once price is accounted for. Regions were assigned by the data generator, not
  randomly, so this is an assumption that should be checked on real data.
        """
    )
