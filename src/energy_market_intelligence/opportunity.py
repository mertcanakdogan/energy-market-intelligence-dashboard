"""Transparent public-demo regional opportunity prioritisation."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

WEIGHT_KEYS = ("market_size", "market_growth", "share_gap", "momentum", "margin", "competition")


def validate_weights(weights: Mapping[str, float]) -> None:
    """Require the complete public-demo weight set to be nonnegative and total one."""

    if set(weights) != set(WEIGHT_KEYS):
        raise ValueError(f"weights must contain exactly: {', '.join(WEIGHT_KEYS)}")
    if any(value < 0 for value in weights.values()) or not np.isclose(sum(weights.values()), 1.0):
        raise ValueError("opportunity weights must be nonnegative and sum to 1")


def minmax_score(values: pd.Series, *, higher_is_better: bool = True) -> pd.Series:
    """Map a component to [0, 100]; assign 50 when all observations are equal."""

    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.isna().any():
        numeric = numeric.fillna(numeric.median())
    span = numeric.max() - numeric.min()
    if span == 0 or not np.isfinite(span):
        score = pd.Series(50.0, index=values.index)
    else:
        score = (numeric - numeric.min()) / span * 100
    return score if higher_is_better else 100 - score


def calculate_opportunity_scores(frame: pd.DataFrame, weights: Mapping[str, float]) -> pd.DataFrame:
    """Calculate an explainable heuristic score without causal or decision claims."""

    validate_weights(weights)
    required = {
        "region_name",
        "market_volume",
        "market_growth",
        "northstar_share",
        "share_momentum",
        "gross_margin_pct",
        "hhi",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"opportunity input missing columns: {sorted(missing)}")
    result = frame.copy()
    result["market_size_score"] = minmax_score(result["market_volume"])
    result["market_growth_score"] = minmax_score(result["market_growth"])
    result["share_gap_score"] = minmax_score(1 - result["northstar_share"])
    result["momentum_score"] = minmax_score(result["share_momentum"])
    result["margin_score"] = minmax_score(result["gross_margin_pct"])
    result["competition_score"] = minmax_score(result["hhi"], higher_is_better=False)
    result["opportunity_score"] = sum(
        result[f"{key}_score"] * weights[key] for key in WEIGHT_KEYS
    ).clip(0, 100)
    result = result.sort_values(["opportunity_score", "region_name"], ascending=[False, True])
    result["opportunity_rank"] = np.arange(1, len(result) + 1)
    return result.reset_index(drop=True)
