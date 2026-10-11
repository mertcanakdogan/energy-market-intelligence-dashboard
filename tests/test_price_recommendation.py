from __future__ import annotations

import math

import pandas as pd
import pytest

from energy_market_intelligence.elasticity import estimate_segment_elasticities
from energy_market_intelligence.price_recommendation import (
    recommend_price_change,
    recommend_prices,
)
from energy_market_intelligence.pricing_config import PricingConfig


def test_inelastic_demand_raises_price_to_the_step_cap() -> None:
    decision = recommend_price_change(100.0, 70.0, -0.6, max_step=0.05, margin_floor=0.1)
    assert decision["recommended_price"] == pytest.approx(105.0)
    assert decision["price_change_pct"] == pytest.approx(0.05)
    assert math.isnan(decision["unconstrained_optimum"])


def test_elastic_demand_uses_the_profit_maximising_price_when_inside_the_cap() -> None:
    # c * e / (1 + e) = 10 * -3 / -2 = 15; current 14.5 -> +3.4%, inside a 10% cap.
    decision = recommend_price_change(14.5, 10.0, -3.0, max_step=0.10, margin_floor=0.1)
    assert decision["recommended_price"] == pytest.approx(15.0)
    assert decision["binding_constraint"] == "profit-maximising price"


def test_elastic_demand_above_optimum_recommends_a_price_cut() -> None:
    decision = recommend_price_change(18.0, 10.0, -3.0, max_step=0.10, margin_floor=0.1)
    assert decision["recommended_price"] == pytest.approx(16.2)  # capped at -10%
    assert decision["price_change_pct"] == pytest.approx(-0.10)
    assert decision["binding_constraint"] == "step cap"


def test_step_cap_limits_a_distant_optimum() -> None:
    decision = recommend_price_change(80.0, 60.0, -1.6, max_step=0.05, margin_floor=0.1)
    assert decision["unconstrained_optimum"] == pytest.approx(160.0)
    assert decision["price_change_pct"] == pytest.approx(0.05)
    assert decision["binding_constraint"] == "step cap"


def test_volume_loss_guard_limits_the_increase() -> None:
    decision = recommend_price_change(
        80.0, 60.0, -1.6, max_step=0.10, margin_floor=0.1, max_volume_loss=0.05
    )
    assert decision["binding_constraint"] == "volume-loss guard"
    volume_change = (1 + decision["price_change_pct"]) ** -1.6 - 1
    assert volume_change == pytest.approx(-0.05)


def test_margin_floor_lifts_a_price_that_is_too_low() -> None:
    # Profit-maximising price = 120 (a 33% margin) but the floor demands 80 / 0.6 = 133.33.
    decision = recommend_price_change(125.0, 80.0, -3.0, max_step=0.10, margin_floor=0.4)
    assert decision["recommended_price"] == pytest.approx(80 / 0.6)
    assert decision["binding_constraint"] == "margin floor"


def test_unreachable_margin_floor_uses_the_full_cap_and_is_flagged() -> None:
    decision = recommend_price_change(80.0, 80.0, -3.0, max_step=0.05, margin_floor=0.2)
    assert decision["recommended_price"] == pytest.approx(84.0)  # floor would need 100
    assert "not reachable" in decision["binding_constraint"]


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"current_price": 0.0}, "positive"),
        ({"margin_floor": 1.0}, "margin_floor"),
        ({"max_step": 0.0}, "max_step"),
        ({"max_volume_loss": 1.5}, "max_volume_loss"),
    ],
)
def test_invalid_arguments_are_rejected(kwargs: dict, message: str) -> None:
    arguments = {
        "current_price": 100.0,
        "unit_cost": 70.0,
        "elasticity": -1.2,
        "max_step": 0.05,
        "margin_floor": 0.1,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError, match=message):
        recommend_price_change(**arguments)


@pytest.fixture(scope="module")
def elasticities(pricing_frame: pd.DataFrame, pricing_config: PricingConfig) -> pd.DataFrame:
    return estimate_segment_elasticities(pricing_frame, pricing_config.true_elasticities)


def test_segment_table_respects_cap_and_floor(
    waterfall_frame: pd.DataFrame, elasticities: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    spec = pricing_config.recommendation
    table = recommend_prices(
        waterfall_frame,
        elasticities,
        spec.max_price_step_pct,
        spec.margin_floor_pct,
        max_volume_loss=spec.max_volume_loss_pct,
    )
    assert set(table["customer_segment_name"]) == {"Residential", "Commercial (SME)", "Industrial"}
    assert (table["price_change_pct"].abs() <= spec.max_price_step_pct + 1e-12).all()
    reached = table["new_margin_pct"] >= spec.margin_floor_pct - 1e-9
    assert (reached | table["binding_constraint"].str.contains("not reachable")).all()
    assert (table["expected_volume_change_pct"] < 0).all()
    assert (table["expected_gross_profit_change"] > 0).all()
    assert (table["gross_profit_change_low"] <= table["expected_gross_profit_change"] + 1e-6).all()
    assert (table["expected_gross_profit_change"] <= table["gross_profit_change_high"] + 1e-6).all()


def test_volume_guard_differentiates_the_elastic_segment(
    waterfall_frame: pd.DataFrame, elasticities: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    spec = pricing_config.recommendation
    table = recommend_prices(
        waterfall_frame,
        elasticities,
        spec.max_price_step_pct,
        spec.margin_floor_pct,
        max_volume_loss=spec.max_volume_loss_pct,
    ).set_index("customer_segment_name")
    assert (
        table.loc["Residential", "price_change_pct"] < table.loc["Industrial", "price_change_pct"]
    )
    assert (
        table.loc["Residential", "expected_volume_change_pct"] >= -spec.max_volume_loss_pct - 1e-9
    )


def test_region_table_has_one_row_per_region_and_segment(
    waterfall_frame: pd.DataFrame, elasticities: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    spec = pricing_config.recommendation
    table = recommend_prices(
        waterfall_frame,
        elasticities,
        spec.max_price_step_pct,
        spec.margin_floor_pct,
        group_columns=("customer_segment_name", "region_name"),
    )
    assert len(table) == 18 * 3
    assert (table["price_change_pct"].abs() <= spec.max_price_step_pct + 1e-12).all()
    # Industrial discount-leakage regions cannot reach the floor in a single step.
    unreachable = table[table["binding_constraint"].str.contains("not reachable")]
    assert set(unreachable["customer_segment_name"]) <= {"Industrial", "Commercial (SME)"}
    assert not unreachable.empty


def test_missing_elasticity_or_columns_are_rejected(
    waterfall_frame: pd.DataFrame, elasticities: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="no elasticity"):
        recommend_prices(waterfall_frame, elasticities.iloc[:1], 0.05, 0.1)
    with pytest.raises(ValueError, match="missing columns"):
        recommend_prices(waterfall_frame.drop(columns="variable_cost"), elasticities, 0.05, 0.1)
