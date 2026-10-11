"""Price elasticity Streamlit page."""

import streamlit as st

from dashboard_support import load_elasticities, page_intro
from energy_market_intelligence.pricing_visualization import elasticity_recovery_figure

page_intro(
    "Price Elasticity",
    "How strongly does volume react to pocket price, by customer segment, and can we trust it?",
)
table = load_elasticities()

cards = st.columns(len(table))
for column, row in zip(cards, table.itertuples(index=False), strict=True):
    column.metric(
        f"{row.customer_segment_name} elasticity",
        f"{row.elasticity:.2f}",
        f"95% CI {row.ci_low:.2f} to {row.ci_high:.2f}",
        delta_color="off",
    )

st.plotly_chart(elasticity_recovery_figure(table), width="stretch")
recovered = int(table["truth_in_ci"].sum())
st.success(
    f"The known true elasticity lies inside the 95% confidence interval for "
    f"{recovered} of {len(table)} segments. The data are synthetic, so the generator's "
    "true parameters are known and the estimator can be checked against them."
)
st.dataframe(
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
    ],
    hide_index=True,
    width="stretch",
)
with st.expander("Method and assumptions"):
    st.markdown(
        """
- Separate log-log OLS per customer segment: `log(volume) ~ log(pocket price) +
  log(competitor price) + trend + month-of-year dummies + region x product fixed effects + promo`.
- Standard errors are clustered by region. Identification comes from staggered regional
  list-price increases and random month-level discount noise.
- Elasticity is constant by construction. Real demand is rarely constant-elasticity over large
  moves, and competitors may react. Treat results as local estimates for small price steps.
        """
    )
