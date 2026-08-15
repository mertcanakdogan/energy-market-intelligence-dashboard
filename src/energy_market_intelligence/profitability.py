"""Profitability summaries and transparent revenue-change decomposition."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def summarize_profitability(fact: pd.DataFrame, group_columns: Sequence[str]) -> pd.DataFrame:
    """Aggregate additive values and recompute ratio metrics from totals."""

    additive = ["volume_mwh", "revenue", "variable_cost", "gross_profit"]
    result = fact.groupby(list(group_columns), as_index=False, dropna=False)[additive].sum()
    result["gross_margin_pct"] = result["gross_profit"].div(result["revenue"].replace(0, np.nan))
    result["profit_per_mwh"] = result["gross_profit"].div(result["volume_mwh"].replace(0, np.nan))
    return result


def decompose_revenue_change(
    prior_volume: float,
    prior_price: float,
    current_volume: float,
    current_price: float,
) -> dict[str, float]:
    """Reconcile revenue change using a base-period volume/price/interaction bridge.

    Volume effect = (V1 - V0) × P0
    Price effect = V0 × (P1 - P0)
    Interaction effect = (V1 - V0) × (P1 - P0)

    The interaction is a non-causal residual created by simultaneous volume and price changes.
    """

    volume_effect = (current_volume - prior_volume) * prior_price
    price_effect = prior_volume * (current_price - prior_price)
    interaction_effect = (current_volume - prior_volume) * (current_price - prior_price)
    total_change = current_volume * current_price - prior_volume * prior_price
    reconciliation_gap = total_change - volume_effect - price_effect - interaction_effect
    return {
        "volume_effect": volume_effect,
        "price_effect": price_effect,
        "interaction_effect": interaction_effect,
        "total_change": total_change,
        "reconciliation_gap": reconciliation_gap,
    }
