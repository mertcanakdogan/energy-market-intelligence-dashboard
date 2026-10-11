from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from helpers import regression_frame

from energy_market_intelligence.elasticity import (
    estimate_segment_elasticities,
    truth_in_interval,
)
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.pricing_data import generate_pricing_data


@pytest.fixture(scope="module")
def estimates(pricing_frame: pd.DataFrame, pricing_config: PricingConfig) -> pd.DataFrame:
    return estimate_segment_elasticities(pricing_frame, pricing_config.true_elasticities)


def test_truth_lies_inside_the_confidence_interval_for_every_segment(
    estimates: pd.DataFrame,
) -> None:
    assert set(estimates["customer_segment_name"]) == {
        "Residential",
        "Commercial (SME)",
        "Industrial",
    }
    assert estimates["truth_in_ci"].all()


def test_estimates_are_close_to_the_known_elasticities(estimates: pd.DataFrame) -> None:
    assert (estimates["abs_error"] < 0.1).all()
    assert (estimates["std_error"] > 0).all()
    assert (estimates["ci_low"] < estimates["elasticity"]).all()
    assert (estimates["elasticity"] < estimates["ci_high"]).all()


def test_segments_are_classified_as_elastic_or_inelastic(estimates: pd.DataFrame) -> None:
    labels = estimates.set_index("customer_segment_name")["classification"]
    assert labels["Residential"] == "elastic"
    assert labels["Industrial"] == "inelastic"


def test_cross_elasticity_is_positive_and_near_truth(
    estimates: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    assert (estimates["cross_elasticity"] > 0).all()
    assert abs(estimates["cross_elasticity"].mean() - pricing_config.cross_elasticity) < 0.15


def test_wider_confidence_level_gives_wider_interval(pricing_frame: pd.DataFrame) -> None:
    narrow = estimate_segment_elasticities(pricing_frame, confidence=0.80)
    wide = estimate_segment_elasticities(pricing_frame, confidence=0.99)
    assert ((wide["ci_high"] - wide["ci_low"]) > (narrow["ci_high"] - narrow["ci_low"])).all()
    assert "true_elasticity" not in narrow.columns


def test_truth_in_interval_boundaries() -> None:
    assert truth_in_interval(-1.0, -1.2, -0.8)
    assert truth_in_interval(-1.2, -1.2, -0.8)
    assert not truth_in_interval(-0.5, -1.2, -0.8)


def test_missing_columns_are_rejected(pricing_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="missing columns"):
        estimate_segment_elasticities(pricing_frame.drop(columns="competitor_price"))


def test_non_positive_prices_are_rejected(pricing_frame: pd.DataFrame) -> None:
    broken = pricing_frame.copy()
    broken.loc[broken.index[0], "pocket_price"] = 0.0
    with pytest.raises(ValueError, match="positive"):
        estimate_segment_elasticities(broken)


def test_estimator_is_unbiased_and_well_calibrated_across_seeds(
    synthetic_bundle: dict[str, pd.DataFrame], pricing_config: PricingConfig
) -> None:
    """Re-draw the pricing noise for several seeds: coverage should be near 95% with no bias."""

    market = {
        name: frame
        for name, frame in synthetic_bundle.items()
        if name not in {"fact_pricing", "dim_customer_segment", "dim_discount_policy"}
    }
    results = []
    for seed in (101, 102, 103, 104, 105, 106):
        bundle = {**market, **generate_pricing_data(market, pricing_config, seed)}
        table = estimate_segment_elasticities(
            regression_frame(bundle), pricing_config.true_elasticities
        )
        results.append(table.assign(seed=seed))
    combined = pd.concat(results)
    assert combined["truth_in_ci"].mean() >= 0.85
    bias = (
        (combined["elasticity"] - combined["true_elasticity"])
        .groupby(combined["customer_segment_name"])
        .mean()
    )
    assert np.all(bias.abs() < 0.08)
