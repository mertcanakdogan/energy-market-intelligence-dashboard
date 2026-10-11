"""Difference-in-differences estimate of the incremental volume uplift of a discount campaign.

Treated regions are those that ever carry ``promo_flag``; the campaign window is the set of
months in which the flag is on. Pre-period = months before the window, post-period = the
window. Months after the campaign are excluded so that the contrast is a clean 2 x 2 design.

Two estimators are reported:

* ``naive``: plain 2 x 2 DiD on log volume. It also picks up the volume gained from the price
  cut that comes with the campaign and any difference in the staggered list-price increases
  between treated and control regions.
* ``price_adjusted``: two-way fixed effects (unit and month) with segment-specific pocket-price
  slopes and competitor price. Its treatment coefficient is the non-price campaign uplift.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

REQUIRED_COLUMNS = {
    "month_id",
    "region_name",
    "product_name",
    "customer_segment_name",
    "volume_mwh",
    "pocket_price",
    "competitor_price",
    "promo_flag",
}
NAIVE_FORMULA = "log_volume ~ treated + post + treated_post"
ADJUSTED_FORMULA = (
    "log_volume ~ treated_post + log_competitor + log_pocket:C(customer_segment_name)"
    " + C(unit) + C(month_id)"
)


def prepare_did_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag treated regions and the campaign window; drop post-campaign months."""

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"promotion input is missing columns: {sorted(missing)}")
    promo_rows = frame[frame["promo_flag"] == 1]
    if promo_rows.empty:
        raise ValueError("no promotion rows found: promo_flag is never set")
    treated_regions = set(promo_rows["region_name"])
    start, end = int(promo_rows["month_id"].min()), int(promo_rows["month_id"].max())
    data = frame[frame["month_id"] <= end].copy()
    data["treated"] = data["region_name"].isin(treated_regions).astype(int)
    data["post"] = (data["month_id"] >= start).astype(int)
    data["treated_post"] = data["treated"] * data["post"]
    if data["treated"].nunique() < 2:
        raise ValueError("difference-in-differences needs both treated and control regions")
    data["log_volume"] = np.log(data["volume_mwh"])
    data["log_pocket"] = np.log(data["pocket_price"])
    data["log_competitor"] = np.log(data["competitor_price"])
    data["unit"] = (
        data["region_name"] + "|" + data["product_name"] + "|" + data["customer_segment_name"]
    )
    return data


def _fit(formula: str, data: pd.DataFrame, confidence: float):
    groups = pd.factorize(data["region_name"])[0]
    model = smf.ols(formula, data=data).fit(
        cov_type="cluster", cov_kwds={"groups": groups}, use_t=True
    )
    low, high = model.conf_int(alpha=1.0 - confidence).loc["treated_post"]
    return model, float(low), float(high)


def estimate_promo_uplift(
    frame: pd.DataFrame, true_uplift: float | None = None, confidence: float = 0.95
) -> pd.DataFrame:
    """Return the naive and price-adjusted DiD uplift (as a fraction) with confidence intervals.

    The coefficient on log volume is converted to a percentage uplift with ``exp(b) - 1``.
    """

    data = prepare_did_frame(frame)
    rows = []
    for method, formula in (("naive", NAIVE_FORMULA), ("price_adjusted", ADJUSTED_FORMULA)):
        model, low, high = _fit(formula, data, confidence)
        row: dict[str, object] = {
            "method": method,
            "uplift": float(np.expm1(model.params["treated_post"])),
            "ci_low": float(np.expm1(low)),
            "ci_high": float(np.expm1(high)),
            "std_error_log": float(model.bse["treated_post"]),
            "n_obs": int(model.nobs),
            "treated_regions": int(data.loc[data["treated"] == 1, "region_name"].nunique()),
            "control_regions": int(data.loc[data["treated"] == 0, "region_name"].nunique()),
        }
        if true_uplift is not None:
            row["true_uplift"] = float(true_uplift)
            row["abs_error"] = abs(float(row["uplift"]) - true_uplift)
            row["truth_in_ci"] = bool(float(row["ci_low"]) <= true_uplift <= float(row["ci_high"]))
        rows.append(row)
    return pd.DataFrame(rows)


def treated_control_trend(frame: pd.DataFrame) -> pd.DataFrame:
    """Indexed monthly volume (pre-campaign average = 100) for treated vs control regions."""

    data = prepare_did_frame(frame)
    monthly = (
        data.groupby(["month_id", "treated"], as_index=False)["volume_mwh"]
        .sum()
        .pivot(index="month_id", columns="treated", values="volume_mwh")
        .rename(columns={0: "control", 1: "treated"})
    )
    pre_months = data.loc[data["post"] == 0, "month_id"].unique()
    base = monthly.loc[monthly.index.isin(pre_months)].mean()
    return (monthly / base * 100).reset_index()
