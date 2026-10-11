from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from energy_market_intelligence.scenario import (
    calculate_scenario,
    scenario_for_selection,
    volume_response_from_elasticity,
)

BASELINE = {"volume_mwh": 100.0, "revenue": 5000.0, "variable_cost": 3500.0, "gross_profit": 1500.0}


def test_zero_assumptions_preserve_baseline() -> None:
    result = calculate_scenario(BASELINE, 0, 0, 0)
    assert result["scenario_revenue"] == BASELINE["revenue"]
    assert result["scenario_gross_profit"] == BASELINE["gross_profit"]


def test_price_and_volume_assumptions_apply_arithmetically() -> None:
    result = calculate_scenario(
        BASELINE, price_change_pct=10, volume_response_pct=-5, variable_cost_change_pct=0
    )
    assert np.isclose(result["scenario_volume_mwh"], 95)
    assert np.isclose(result["scenario_revenue"], 95 * 55)


def test_variable_cost_change_applies_to_unit_cost() -> None:
    result = calculate_scenario(BASELINE, 0, 0, 10)
    assert result["scenario_variable_cost"] == 3850
    assert result["scenario_gross_profit"] == 1150


def test_scenario_returns_deltas_and_margin() -> None:
    result = calculate_scenario(BASELINE, 5, 2, 1)
    assert "revenue_delta" in result
    assert "gross_profit_delta" in result
    assert np.isclose(result["baseline_gross_margin_pct"], 0.3)


def test_invalid_assumption_below_negative_one_hundred_fails() -> None:
    with pytest.raises(ValueError, match="greater than -100"):
        calculate_scenario(BASELINE, -101, 0, 0)


def test_zero_volume_baseline_fails() -> None:
    with pytest.raises(ValueError, match="positive baseline volume"):
        calculate_scenario({**BASELINE, "volume_mwh": 0}, 0, 0, 0)


def test_scenario_selection_filters_region_and_product() -> None:
    frame = pd.DataFrame(
        {
            "region_name": ["R1", "R2"],
            "product_segment": ["P1", "P2"],
            "volume_mwh": [100.0, 200.0],
            "revenue": [5000.0, 12000.0],
            "variable_cost": [3500.0, 8000.0],
            "gross_profit": [1500.0, 4000.0],
        }
    )
    result = scenario_for_selection(frame, "R1", "P1", 0, 0, 0)
    assert result["baseline_volume_mwh"] == 100


def test_volume_response_from_elasticity_matches_constant_elasticity_formula() -> None:
    assert np.isclose(volume_response_from_elasticity(5, -1.6), (1.05**-1.6 - 1) * 100)
    assert volume_response_from_elasticity(0, -1.6) == 0
    assert volume_response_from_elasticity(-5, -0.6) > 0


def test_elasticity_driven_scenario_reproduces_the_recommendation_arithmetic() -> None:
    response = volume_response_from_elasticity(5, -1.0)
    result = calculate_scenario(BASELINE, 5, response, 0)
    # Unit elasticity keeps revenue (almost) flat while profit rises through lower volume.
    assert np.isclose(result["scenario_revenue"], BASELINE["revenue"])
    assert result["gross_profit_delta"] > 0


def test_volume_response_rejects_impossible_price_change() -> None:
    with pytest.raises(ValueError, match="greater than -100"):
        volume_response_from_elasticity(-100, -1.0)
