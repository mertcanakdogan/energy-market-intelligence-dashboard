from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from energy_market_intelligence.competition import (
    calculate_hhi,
    classify_hhi,
    rank_competitor_momentum,
)


def test_hhi_uses_fractional_shares() -> None:
    assert calculate_hhi(pd.Series([0.5, 0.5])) == 0.5


def test_hhi_rejects_impossible_share_total() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        calculate_hhi(pd.Series([0.8, 0.8]))


@pytest.mark.parametrize(
    ("hhi", "expected"),
    [(0.10, "Fragmented"), (0.20, "Moderately concentrated"), (0.35, "Concentrated")],
)
def test_hhi_classification(hhi: float, expected: str) -> None:
    assert classify_hhi(hhi) == expected


def test_competitor_momentum_ranks_largest_share_gain_first() -> None:
    frame = pd.DataFrame(
        {
            "company_name": ["A", "B", "C"],
            "current_share": [0.3, 0.4, 0.3],
            "prior_share": [0.2, 0.4, 0.4],
        }
    )
    result = rank_competitor_momentum(frame)
    assert result.iloc[0]["company_name"] == "A"
    assert np.isclose(result.iloc[0]["share_change_pp"], 10.0)
