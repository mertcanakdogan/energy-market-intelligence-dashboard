from __future__ import annotations

import pandas as pd
import pytest

from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.promotion import (
    estimate_promo_uplift,
    prepare_did_frame,
    treated_control_trend,
)


@pytest.fixture(scope="module")
def estimates(pricing_frame: pd.DataFrame, pricing_config: PricingConfig) -> pd.DataFrame:
    return estimate_promo_uplift(pricing_frame, pricing_config.promotion.true_volume_uplift)


def test_price_adjusted_did_recovers_the_true_uplift(
    estimates: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    row = estimates.set_index("method").loc["price_adjusted"]
    truth = pricing_config.promotion.true_volume_uplift
    assert row["truth_in_ci"]
    assert abs(row["uplift"] - truth) < 0.02
    assert row["ci_low"] < row["uplift"] < row["ci_high"]


def test_naive_did_overstates_because_it_ignores_the_price_cut(
    estimates: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    by_method = estimates.set_index("method")
    truth = pricing_config.promotion.true_volume_uplift
    assert by_method.loc["naive", "uplift"] > truth + 0.02
    assert by_method.loc["naive", "abs_error"] > by_method.loc["price_adjusted", "abs_error"]


def test_design_has_treated_and_control_regions(
    estimates: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    row = estimates.iloc[0]
    assert row["treated_regions"] == len(pricing_config.promotion.treated_regions)
    assert row["control_regions"] == 18 - row["treated_regions"]


def test_months_after_the_campaign_are_excluded(
    pricing_frame: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    data = prepare_did_frame(pricing_frame)
    assert data["month_id"].max() == pricing_config.promotion.end_month_id
    assert data["treated_post"].sum() == data["promo_flag"].sum()


def test_estimate_without_truth_omits_comparison_columns(pricing_frame: pd.DataFrame) -> None:
    result = estimate_promo_uplift(pricing_frame)
    assert "true_uplift" not in result.columns


def test_trend_is_indexed_to_pre_campaign_average(
    pricing_frame: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    trend = treated_control_trend(pricing_frame)
    window = (pricing_config.promotion.start_month_id, pricing_config.promotion.end_month_id)
    pre = trend[trend["month_id"] < window[0]]
    assert pre[["control", "treated"]].mean().between(99.9, 100.1).all()
    during = trend[trend["month_id"].between(*window)]
    assert (during["treated"] - during["control"]).mean() > 0


def test_missing_promotion_is_rejected(pricing_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="never set"):
        prepare_did_frame(pricing_frame.assign(promo_flag=0))


def test_missing_columns_are_rejected(pricing_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="missing columns"):
        prepare_did_frame(pricing_frame.drop(columns="volume_mwh"))


def test_requires_control_regions(pricing_frame: pd.DataFrame) -> None:
    everywhere = pricing_frame.assign(promo_flag=1)
    with pytest.raises(ValueError, match="treated and control"):
        prepare_did_frame(everywhere)
