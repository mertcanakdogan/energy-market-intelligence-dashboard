from __future__ import annotations

import numpy as np
import pandas as pd

from energy_market_intelligence.metrics import (
    add_growth_metrics,
    add_rolling_metrics,
    calculate_company_market_share,
    generate_management_observations,
    safe_divide,
)


def test_safe_divide_returns_nan_for_zero_denominator() -> None:
    result = safe_divide(pd.Series([2.0, 2.0]), pd.Series([1.0, 0.0]))
    assert result.iloc[0] == 2.0
    assert np.isnan(result.iloc[1])


def test_company_market_share_sums_to_one(small_fact: pd.DataFrame) -> None:
    result = calculate_company_market_share(small_fact)
    sums = result.groupby(["month_id", "region_id"])["market_share"].sum()
    assert np.allclose(sums, 1.0)


def test_company_market_share_uses_fractional_representation(small_fact: pd.DataFrame) -> None:
    result = calculate_company_market_share(small_fact)
    first = result.query("month_id == 1 and company_id == 1").iloc[0]
    assert first["market_share"] == 0.25


def test_growth_metrics_respect_groups() -> None:
    frame = pd.DataFrame(
        {"group": ["a", "a", "b", "b"], "date": [1, 2, 1, 2], "value": [10, 15, 20, 10]}
    )
    result = add_growth_metrics(frame, "value", ["group"], periods=1, label="mom")
    assert result["mom_growth_pct"].iloc[1] == 0.5
    assert result["mom_growth_pct"].iloc[3] == -0.5


def test_growth_metrics_handle_zero_prior_value() -> None:
    frame = pd.DataFrame({"date": [1, 2], "value": [0.0, 5.0]})
    result = add_growth_metrics(frame, "value", [], periods=1, label="mom")
    assert np.isnan(result["mom_growth_pct"].iloc[1])


def test_rolling_metrics_use_requested_windows() -> None:
    frame = pd.DataFrame({"group": ["a"] * 4, "date": range(4), "value": [1.0, 2.0, 3.0, 4.0]})
    result = add_rolling_metrics(frame, "value", ["group"], windows=(3,))
    assert result["value_rolling_3"].tolist() == [1.0, 1.5, 2.0, 3.0]


def test_management_observations_are_metric_derived() -> None:
    kpis = {"share_change_pp": 1.2, "market_yoy_growth_pct": 4.5, "gross_margin_change_pp": -0.8}
    regions = pd.DataFrame(
        {
            "region_name": ["R1"],
            "market_growth": [0.08],
            "northstar_share": [0.12],
            "opportunity_score": [80],
        }
    )
    text = " ".join(generate_management_observations(kpis, regions))
    assert "1.2 pp" in text
    assert "4.5%" in text
    assert "R1" in text
