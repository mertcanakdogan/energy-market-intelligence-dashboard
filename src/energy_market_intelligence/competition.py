"""Competitive-share, momentum, ranking, and market-concentration helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_hhi(shares: pd.Series) -> float:
    """Calculate HHI from fractional shares, yielding a value between 0 and 1."""

    numeric = shares.astype(float)
    if not numeric.between(0, 1).all() or not np.isclose(numeric.sum(), 1.0, atol=1e-6):
        raise ValueError("fractional market shares must be in [0, 1] and sum to 1")
    return float(np.square(numeric).sum())


def classify_hhi(hhi: float) -> str:
    """Provide generic analytical context, not a legal or regulatory judgment."""

    if not 0 <= hhi <= 1:
        raise ValueError("HHI must be between 0 and 1")
    if hhi < 0.15:
        return "Fragmented"
    if hhi < 0.25:
        return "Moderately concentrated"
    return "Concentrated"


def rank_competitor_momentum(frame: pd.DataFrame) -> pd.DataFrame:
    """Rank companies by current-minus-prior share in percentage points."""

    required = {"company_name", "current_share", "prior_share"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"competitor momentum missing columns: {sorted(missing)}")
    result = frame.copy()
    result["share_change_pp"] = (result["current_share"] - result["prior_share"]) * 100
    result = result.sort_values(["share_change_pp", "company_name"], ascending=[False, True])
    result["momentum_rank"] = np.arange(1, len(result) + 1)
    return result.reset_index(drop=True)
