"""Landing page: the thesis, the price breakdown, three questions and the proof the model works."""

import streamlit as st

import dashboard_style as style
from dashboard_support import (
    load_elasticities,
    load_pricing_config,
    load_view,
    note,
    page_spec,
    show_chart,
)
from energy_market_intelligence.insights import (
    action_answer,
    bridge_answer,
    leakage_answer,
    leakage_thesis,
)
from energy_market_intelligence.localization import SEGMENT_ORDER
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_visualization import (
    PORTFOLIO,
    bill_waterfall_figure,
    portfolio_bill,
)
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

# 1. The thesis, computed from the data.
with st.container(key="hero"):
    st.title(leakage_thesis(portfolio.leakage_rate, highlight=True))
    style.lead(
        f"{FOCUS_COMPANY} is a fictional electricity retailer and all data are synthetic. "
        "Amounts are in TRY at constant 2025 prices."
    )

# 2. The price breakdown next to the waterfall it summarises.
segments = [name for name in SEGMENT_ORDER if name in set(waterfall["customer_segment_name"])]
scope = st.segmented_control(
    "Scope of the price breakdown", [PORTFOLIO, *segments], default=PORTFOLIO, key="home_scope"
)
bill = portfolio_bill(waterfall, None if scope in (None, PORTFOLIO) else scope)
left, right = st.columns([6, 5], gap="large")
with left:
    st.markdown(style.bill_html(bill), unsafe_allow_html=True)
with right:
    st.markdown("**From list price to net price** (TRY/MWh)")
    show_chart(
        bill_waterfall_figure(bill),
        alt=f"Items from list price to net price, TRY/MWh ({bill.scope})",
    )
    st.caption("The axis does not start at zero, so the gaps between the items stay readable.")

# 3. Three questions, each with its one-line answer.
st.subheader("Three questions, answered with data")
cards = (
    ("views/price_waterfall.py", None, leakage_answer(portfolio, flags)),
    ("views/pvm_bridge.py", None, bridge_answer(pvm_summary)),
    ("views/price_recommendation.py", "What should the company do?", action_answer(recommendation)),
)
for index, (column, (path, label, answer)) in enumerate(
    zip(st.columns(3, gap="medium"), cards, strict=True)
):
    with column, st.container(key=f"card-{index}"):
        st.page_link(path, label=label or page_spec(path).question)
        style.answer(answer)

# 4. Why the model can be trusted: true versus estimated elasticity.
st.subheader("Why can you trust the model?")
recovered = int(elasticities["truth_in_ci"].sum())
st.write(
    "The data are synthetic, so the true price elasticities are known; the model estimates them "
    f"without seeing them. In {recovered} of {len(elasticities)} segments the true value lies "
    "inside the 95% confidence interval of the estimate."
)
st.markdown(style.trust_strip_html(elasticities), unsafe_allow_html=True)
st.page_link("views/elasticity.py", label=page_spec("views/elasticity.py").question)

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

note(
    "All data and business logic in this app were redesigned for a public demonstration. "
    "The app does not make automatic business decisions.",
    label="For demonstration only",
)
