"""Price elasticity: the estimate per segment and the known true value."""

import streamlit as st

from dashboard_support import (
    load_elasticities,
    page_intro,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import elasticity_insight
from energy_market_intelligence.localization import format_number, order_segments
from energy_market_intelligence.pricing_visualization import elasticity_recovery_figure

page_intro(
    "views/elasticity.py",
    "How much sales volume changes, in percent, when the pocket price (the price the company "
    "keeps after discounts) rises 1%, for each customer segment. The data are synthetic, so "
    "the true values are known and the accuracy of the estimate can be checked.",
)
table = order_segments(load_elasticities()).reset_index(drop=True)

cards = st.columns(len(table))
for column, row in zip(cards, table.itertuples(index=False), strict=True):
    column.metric(
        f"{row.customer_segment_name}: elasticity",
        format_number(row.elasticity, 2),
        f"Likely range: {format_number(row.ci_low, 2)} to {format_number(row.ci_high, 2)}",
        delta_color="off",
        delta_arrow="off",
        help="\u22121.60 means a 1% price rise loses about 1.6% of volume. The further below "
        "\u22121, the more price-sensitive the segment.",
    )
takeaway(elasticity_insight(table))

figure = elasticity_recovery_figure(table)
figure.update_xaxes(title="Price elasticity")  # the long export title would be cut on a phone
show_chart(figure)
st.caption(
    "Price elasticity: the % change in volume when the pocket price rises 1%. The line around "
    "each estimate is its likely range (95% confidence interval); the diamond is the true value. "
    "At \u22121 (dotted line) a price rise leaves revenue unchanged. The less price-sensitive a "
    "segment, the further its price can rise: see Price recommendation."
)
show_table(
    table[
        [
            "customer_segment_name",
            "elasticity",
            "true_elasticity",
            "truth_in_ci",
            "ci_low",
            "ci_high",
        ]
    ]
)
with st.expander("More statistics"):
    show_table(
        table[
            [
                "customer_segment_name",
                "std_error",
                "abs_error",
                "cross_elasticity",
                "classification",
            ]
        ]
    )
    st.caption(
        "Standard error: how uncertain the estimate is (smaller is more certain). Absolute error: "
        "the gap between the estimate and the true value. Competitor-price elasticity: the % "
        "change in volume when competitor prices rise 1%."
    )
with st.expander("Method and assumptions"):
    st.markdown(
        """
- A separate log-log regression (OLS, ordinary least squares) for each customer segment:
  `log(volume) ~ log(pocket price) + log(competitor price) + trend + month dummies +
  province × product fixed effects + promotion`.
- Standard errors are clustered by province. The price changes that make the estimate possible
  come from list-price increases rolled out to the provinces at different times and from random
  monthly changes in discounts.
- The elasticity is constant by design. In reality demand does not keep a constant elasticity
  for large price changes, and competitors may react; the results are local estimates for small
  price steps.
        """
    )
