"""Own-price elasticity of volume by customer segment (log-log OLS with fixed effects).

Model, estimated separately for each customer segment::

    log(volume) = a(region, product) + month-of-year dummies + trend
                  + beta * log(pocket price) + gamma * log(competitor price)
                  + delta * promo + error

``beta`` is the own-price elasticity. Standard errors are clustered by region. Identification
comes from price variation that is unrelated to demand shocks: staggered regional list-price
increases and random month-level discount noise, with region x product fixed effects absorbing
level differences (including structurally deeper discounts in leakage regions).
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

REQUIRED_COLUMNS = {
    "month_id",
    "month",
    "region_name",
    "product_name",
    "customer_segment_name",
    "volume_mwh",
    "pocket_price",
    "competitor_price",
    "promo_flag",
}
FORMULA = (
    "log_volume ~ log_pocket + log_competitor + trend + C(month_of_year) + C(unit) + promo_flag"
)


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"elasticity input is missing columns: {sorted(missing)}")
    data = frame.copy()
    if (data[["volume_mwh", "pocket_price", "competitor_price"]] <= 0).any().any():
        raise ValueError("elasticity estimation requires positive volumes and prices")
    data["log_volume"] = np.log(data["volume_mwh"])
    data["log_pocket"] = np.log(data["pocket_price"])
    data["log_competitor"] = np.log(data["competitor_price"])
    data["trend"] = data["month_id"].astype(float)
    data["month_of_year"] = data["month"].astype(int)
    data["unit"] = data["region_name"] + "|" + data["product_name"]
    return data


def truth_in_interval(truth: float, ci_low: float, ci_high: float) -> bool:
    """Report whether the known true parameter lies inside the confidence interval."""

    return bool(ci_low <= truth <= ci_high)


def estimate_segment_elasticities(
    frame: pd.DataFrame,
    true_elasticities: Mapping[str, float] | None = None,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Estimate own-price elasticity for every customer segment in ``frame``.

    Returns one row per segment with the estimate, clustered standard error, confidence
    interval, the cross-price elasticity and (when supplied) the known true value.
    """

    data = _prepare(frame)
    rows: list[dict[str, object]] = []
    for segment, subset in data.groupby("customer_segment_name", sort=True):
        groups = pd.factorize(subset["region_name"])[0]
        model = smf.ols(FORMULA, data=subset).fit(
            cov_type="cluster", cov_kwds={"groups": groups}, use_t=True
        )
        low, high = model.conf_int(alpha=1.0 - confidence).loc["log_pocket"]
        estimate = float(model.params["log_pocket"])
        row: dict[str, object] = {
            "customer_segment_name": segment,
            "elasticity": estimate,
            "std_error": float(model.bse["log_pocket"]),
            "ci_low": float(low),
            "ci_high": float(high),
            "cross_elasticity": float(model.params["log_competitor"]),
            "n_obs": int(model.nobs),
            "classification": "elastic" if estimate < -1 else "inelastic",
        }
        if true_elasticities is not None and segment in true_elasticities:
            truth = float(true_elasticities[str(segment)])
            row["true_elasticity"] = truth
            row["abs_error"] = abs(estimate - truth)
            row["truth_in_ci"] = truth_in_interval(truth, float(low), float(high))
        rows.append(row)
    return pd.DataFrame(rows)
