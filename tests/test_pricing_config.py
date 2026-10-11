from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from energy_market_intelligence.pricing_config import PricingConfig


@pytest.fixture()
def raw_section(project_root: Path) -> dict:
    with (project_root / "config" / "default.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)["pricing"]


def test_ground_truth_is_documented_in_config(pricing_config: PricingConfig) -> None:
    truth = pricing_config.true_elasticities
    assert set(truth) == {"Residential", "Commercial (SME)", "Industrial"}
    assert any(value < -1 for value in truth.values())
    assert any(value > -1 for value in truth.values())
    assert pricing_config.cross_elasticity > 0
    assert pricing_config.promotion.true_volume_uplift == pytest.approx(0.08)
    assert (
        pricing_config.policy_max_discount["Industrial"]
        > pricing_config.policy_max_discount["Residential"]
    )


def test_price_increases_are_staggered(pricing_config: PricingConfig) -> None:
    months = {increase.month_id for increase in pricing_config.list_price_increases}
    assert len(months) >= 3


def test_volume_shares_must_sum_to_one(raw_section: dict) -> None:
    broken = copy.deepcopy(raw_section)
    broken["segments"][0]["volume_share"] = 0.5
    with pytest.raises(ValueError, match="sum to 1"):
        PricingConfig.from_mapping(broken)


def test_config_requires_elastic_and_inelastic_segments(raw_section: dict) -> None:
    broken = copy.deepcopy(raw_section)
    for segment in broken["segments"]:
        segment["true_elasticity"] = -0.5
    with pytest.raises(ValueError, match="elastic and an inelastic"):
        PricingConfig.from_mapping(broken)


def test_seasonality_needs_twelve_factors(raw_section: dict) -> None:
    broken = copy.deepcopy(raw_section)
    broken["seasonality"] = broken["seasonality"][:11]
    with pytest.raises(ValueError, match="12 monthly"):
        PricingConfig.from_mapping(broken)


def test_empty_promotion_window_is_rejected(raw_section: dict) -> None:
    broken = copy.deepcopy(raw_section)
    broken["promotion"]["end_month_id"] = broken["promotion"]["start_month_id"] - 1
    with pytest.raises(ValueError, match="window is empty"):
        PricingConfig.from_mapping(broken)
