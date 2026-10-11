"""Landing page: the thesis, the price breakdown, three questions and the proof the model works."""

import streamlit as st

import dashboard_style as style
from dashboard_support import (
    load_elasticities,
    load_pricing_config,
    load_promotion_results,
    load_view,
    page_spec,
    takeaway,
)
from energy_market_intelligence.insights import (
    action_answer,
    bridge_answer,
    leakage_answer,
    leakage_thesis,
    overview_takeaway,
    promo_proof,
    trust_note,
)
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_visualization import portfolio_bill
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY

waterfall = load_view("vw_price_waterfall")
flags = load_view("vw_discount_policy_flags")
pvm_summary = load_view("vw_pvm_bridge_summary")
elasticities = load_elasticities()
guard = load_pricing_config().recommendation
recommendation = recommend_prices(
    waterfall,
    elasticities,
    guard.max_price_step_pct,
    guard.margin_floor_pct,
    max_volume_loss=guard.max_volume_loss_pct,
)
portfolio = portfolio_bill(waterfall)
promotion_estimates, _trend = load_promotion_results()

# 1. The thesis, computed from the data.
with st.container(key="hero"):
    st.title(leakage_thesis(portfolio.leakage_rate, highlight=True))
    style.lead(
        f"{FOCUS_COMPANY} is a fictional electricity retailer and all data are synthetic. "
        "Amounts are in TRY at constant 2025 prices."
    )

takeaway(overview_takeaway(portfolio, waterfall, recommendation))

# 2. The price breakdown, and where leakage differs between the customer segments.
left, right = st.columns([6, 5], gap="large")
with left:
    st.markdown(style.bill_html(portfolio), unsafe_allow_html=True)
    st.markdown(style.bill_terms_html(), unsafe_allow_html=True)
with right:
    st.markdown(style.segment_leakage_html(waterfall), unsafe_allow_html=True)

# 3. Three questions, each with its one-line answer; the recommendation comes first.
st.subheader("Three questions, answered with data")
cards = (
    (
        "action",
        "views/price_recommendation.py",
        "What should the company do?",
        action_answer(recommendation),
    ),
    ("leakage", "views/price_waterfall.py", None, leakage_answer(portfolio, flags)),
    ("bridge", "views/pvm_bridge.py", None, bridge_answer(pvm_summary)),
)
for column, (key, path, label, answer) in zip(st.columns(3, gap="medium"), cards, strict=True):
    with column, st.container(key=f"card-{key}"):
        st.page_link(path, label=label or page_spec(path).question)
        style.answer(answer)

# 4. Why the model can be trusted: estimates next to the known truth.
st.subheader("Why can you trust the model?")
recovered = int(elasticities["truth_in_ci"].sum())
st.write(
    "The data are synthetic, so the true price elasticities are known; the model estimates them "
    f"without seeing them. In {recovered} of {len(elasticities)} segments the true value lies "
    "inside the 95% confidence interval of the estimate."
)
st.markdown(style.trust_strip_html(elasticities), unsafe_allow_html=True)
st.caption(trust_note(elasticities))
st.write(promo_proof(promotion_estimates))
proof_left, proof_right = st.columns(2, gap="medium")
proof_left.page_link("views/elasticity.py", label=page_spec("views/elasticity.py").question)
proof_right.page_link(
    "views/promotion_impact.py", label=page_spec("views/promotion_impact.py").question
)

with st.expander("Glossary (terms used in this app)"):
    st.markdown(
        """
- **List price:** the unit price on the price list (TRY/MWh).
- **Price breakdown:** the steps from list price to net price, listed like the lines of a bill.
- **On-invoice discount:** a discount taken off the list price on the invoice itself.
- **Off-invoice rebate:** money paid back to the customer after the invoice, such as rebates
  and bonuses.
- **Net (pocket) price:** the unit price the company really keeps after all discounts, rebates,
  payment-term costs and service and freight costs.
- **Leakage rate:** the part of the list price that the company does not keep:
  1 - net price / list price.
- **Price realisation:** net revenue / revenue at list price (100% minus the leakage rate).
- **Above-policy discount:** the part of a discount that goes above the limit set for a segment.
- **PVM (price-volume-mix) bridge:** splits a change in revenue or profit into the effects of
  price, volume sold, the mix of products and customers, and cost.
- **Price elasticity:** the percent change in volume when the price rises 1%. At -1.6, a 1%
  price rise cuts volume by about 1.6%. Below -1 (for example -1.6) demand is *elastic*; between
  -1 and 0 (for example -0.6) it is *inelastic*, that is, less sensitive to price.
- **Difference-in-differences (DiD):** measures the true effect of a promotion by comparing the
  change in the promotion provinces with the change in provinces without the promotion.
- **Confidence interval (CI):** the range in which the true value plausibly lies; a wide 95% CI
  means the estimate is uncertain.
- **Gross profit / gross margin:** net revenue minus energy (variable) cost; the margin is gross
  profit as a share of net revenue.
- **Constant 2025 prices:** all TRY amounts are adjusted for inflation, so years can be compared
  without the effect of rising price levels.
- **MWh / GWh / TWh:** megawatt-hour; 1 GWh = 1,000 MWh and 1 TWh = 1,000 GWh.
- **PTF, YEK-G:** PTF is Turkey's day-ahead market price for electricity (the wholesale
  price); the product name "Index-linked (PTF+)" refers to a tariff linked to it. YEK-G is a
  renewable-energy guarantee certificate; "Green energy (YEK-G)" is a tariff backed by it.
        """
    )

st.markdown(style.closing_html(), unsafe_allow_html=True)
st.page_link("views/price_waterfall.py", label="Start with Price leakage")
st.caption("Synthetic data and a fictional company. Not decision advice.")
