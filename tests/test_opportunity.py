from __future__ import annotations

import pandas as pd
import pytest

from energy_market_intelligence.opportunity import (
    calculate_opportunity_scores,
    minmax_score,
    validate_weights,
)

WEIGHTS = {
    "market_size": 0.2,
    "market_growth": 0.2,
    "share_gap": 0.2,
    "momentum": 0.15,
    "margin": 0.15,
    "competition": 0.1,
}


def opportunity_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region_name": ["Strong", "Weak"],
            "market_volume": [1000.0, 100.0],
            "market_growth": [0.1, -0.1],
            "northstar_share": [0.1, 0.5],
            "share_momentum": [0.02, -0.02],
            "gross_margin_pct": [0.3, 0.1],
            "hhi": [0.1, 0.4],
        }
    )


def test_weights_must_sum_to_one() -> None:
    invalid = {**WEIGHTS, "competition": 0.05}
    with pytest.raises(ValueError, match="sum to 1"):
        validate_weights(invalid)


def test_minmax_score_is_bounded() -> None:
    score = minmax_score(pd.Series([-5.0, 0.0, 10.0]))
    assert score.min() == 0
    assert score.max() == 100


def test_constant_component_receives_neutral_score() -> None:
    assert minmax_score(pd.Series([2.0, 2.0])).tolist() == [50.0, 50.0]


def test_opportunity_score_exposes_components_and_bounds() -> None:
    result = calculate_opportunity_scores(opportunity_input(), WEIGHTS)
    expected = {
        "market_size_score",
        "market_growth_score",
        "share_gap_score",
        "momentum_score",
        "margin_score",
        "competition_score",
    }
    assert expected.issubset(result.columns)
    assert result["opportunity_score"].between(0, 100).all()


def test_more_attractive_region_ranks_first() -> None:
    result = calculate_opportunity_scores(opportunity_input(), WEIGHTS)
    assert result.iloc[0]["region_name"] == "Strong"
    assert result.iloc[0]["opportunity_rank"] == 1


def test_opportunity_input_missing_column_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        calculate_opportunity_scores(opportunity_input().drop(columns="hhi"), WEIGHTS)
