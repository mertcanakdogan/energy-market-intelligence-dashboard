"""Price elasticity: the estimate per segment and the known true value."""

import streamlit as st

from dashboard_support import (
    load_elasticities,
    page_intro,
    positive,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import elasticity_insight
from energy_market_intelligence.localization import format_number, order_segments
from energy_market_intelligence.pricing_visualization import elasticity_recovery_figure

page_intro(
    "views/elasticity.py",
    "By how many percent sales volume changes when the pocket price rises 1%, for each "
    "customer segment. The data are synthetic, so the true values are known and the accuracy "
    "of the estimate can be checked.",
)
table = order_segments(load_elasticities()).reset_index(drop=True)

cards = st.columns(len(table))
for column, row in zip(cards, table.itertuples(index=False), strict=True):
    column.metric(
        row.customer_segment_name,
        format_number(row.elasticity, 2),
        f"95% CI: {format_number(row.ci_low, 2)} / {format_number(row.ci_high, 2)}",
        delta_color="off",
        help="Estimated price elasticity. Below -1 demand is elastic (price-sensitive); "
        "above -1 it is inelastic.",
    )
takeaway(elasticity_insight(table))

show_chart(elasticity_recovery_figure(table))
recovered = int(table["truth_in_ci"].sum())
positive(
    f"The known true elasticity lies inside the 95% confidence interval of the estimate in "
    f"{recovered} of {len(table)} segments. The true parameters of the data generator are "
    "known, so the estimation method can be tested directly.",
    label="Model checked",
)
show_table(
    table[
        [
            "customer_segment_name",
            "elasticity",
            "std_error",
            "ci_low",
            "ci_high",
            "true_elasticity",
            "abs_error",
            "truth_in_ci",
            "cross_elasticity",
            "classification",
        ]
    ]
)
with st.expander("Method and assumptions"):
    st.markdown(
        """
- A separate log-log regression (OLS, ordinary least squares) for each customer segment:
  `log(volume) ~ log(pocket price) + log(competitor price) + trend + month dummies +
  province x product fixed effects + promotion`.
- Standard errors are clustered by province. The price changes that make the estimate possible
  come from list-price increases rolled out to the provinces at different times and from random
  monthly changes in discounts.
- The elasticity is constant by design. In reality demand does not keep a constant elasticity
  for large price changes, and competitors may react; the results are local estimates for small
  price steps.
        """
    )
