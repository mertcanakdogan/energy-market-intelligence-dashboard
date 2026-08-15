from __future__ import annotations

import numpy as np
import pandas as pd

from energy_market_intelligence.profitability import (
    decompose_revenue_change,
    summarize_profitability,
)


def test_profitability_summary_aggregates_financials(small_fact: pd.DataFrame) -> None:
    result = summarize_profitability(small_fact, ["company_id"])
    row = result.query("company_id == 1").iloc[0]
    assert row["revenue"] == 11600
    assert row["gross_profit"] == 3900


def test_profitability_summary_recomputes_weighted_margin(small_fact: pd.DataFrame) -> None:
    result = summarize_profitability(small_fact, ["company_id"])
    row = result.query("company_id == 1").iloc[0]
    assert np.isclose(row["gross_margin_pct"], 3900 / 11600)


def test_profitability_summary_handles_zero_volume() -> None:
    frame = pd.DataFrame(
        {
            "group": ["x"],
            "volume_mwh": [0.0],
            "revenue": [0.0],
            "variable_cost": [0.0],
            "gross_profit": [0.0],
        }
    )
    row = summarize_profitability(frame, ["group"]).iloc[0]
    assert np.isnan(row["profit_per_mwh"])
    assert np.isnan(row["gross_margin_pct"])


def test_revenue_decomposition_reconciles_exactly() -> None:
    result = decompose_revenue_change(100, 50, 120, 55)
    assert result["volume_effect"] == 1000
    assert result["price_effect"] == 500
    assert result["interaction_effect"] == 100
    assert result["total_change"] == 1600
    assert result["reconciliation_gap"] == 0


def test_revenue_decomposition_handles_zero_baseline() -> None:
    result = decompose_revenue_change(0, 0, 10, 20)
    assert result["interaction_effect"] == 200
    assert result["total_change"] == 200
