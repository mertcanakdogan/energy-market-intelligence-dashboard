"""Non-causal what-if scenario arithmetic."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_scenario(
    baseline: dict[str, float],
    price_change_pct: float,
    volume_response_pct: float,
    variable_cost_change_pct: float,
) -> dict[str, float]:
    """Evaluate arithmetic consequences of user-defined assumptions."""

    if min(price_change_pct, volume_response_pct, variable_cost_change_pct) <= -100:
        raise ValueError("scenario percentage assumptions must be greater than -100")
    volume = float(baseline["volume_mwh"])
    revenue = float(baseline["revenue"])
    variable_cost = float(baseline["variable_cost"])
    gross_profit = float(baseline["gross_profit"])
    if volume <= 0:
        raise ValueError("scenario requires positive baseline volume")
    baseline_price = revenue / volume
    baseline_unit_cost = variable_cost / volume
    scenario_volume = volume * (1 + volume_response_pct / 100)
    scenario_price = baseline_price * (1 + price_change_pct / 100)
    scenario_unit_cost = baseline_unit_cost * (1 + variable_cost_change_pct / 100)
    scenario_revenue = scenario_volume * scenario_price
    scenario_cost = scenario_volume * scenario_unit_cost
    scenario_profit = scenario_revenue - scenario_cost
    return {
        "baseline_volume_mwh": volume,
        "baseline_revenue": revenue,
        "baseline_variable_cost": variable_cost,
        "baseline_gross_profit": gross_profit,
        "baseline_gross_margin_pct": gross_profit / revenue if revenue else np.nan,
        "scenario_volume_mwh": scenario_volume,
        "scenario_average_price": scenario_price,
        "scenario_revenue": scenario_revenue,
        "scenario_variable_cost": scenario_cost,
        "scenario_gross_profit": scenario_profit,
        "scenario_gross_margin_pct": scenario_profit / scenario_revenue
        if scenario_revenue
        else np.nan,
        "volume_delta": scenario_volume - volume,
        "revenue_delta": scenario_revenue - revenue,
        "gross_profit_delta": scenario_profit - gross_profit,
    }


def scenario_for_selection(
    frame: pd.DataFrame,
    region_name: str,
    product_segment: str,
    price_change_pct: float,
    volume_response_pct: float,
    variable_cost_change_pct: float,
) -> dict[str, float]:
    """Filter an analytical baseline and run the transparent scenario calculation."""

    selected = frame[
        (frame["region_name"] == region_name) & (frame["product_segment"] == product_segment)
    ]
    if selected.empty:
        raise ValueError("no baseline data matches the selected region and product")
    baseline = selected[["volume_mwh", "revenue", "variable_cost", "gross_profit"]].sum().to_dict()
    return calculate_scenario(
        baseline, price_change_pct, volume_response_pct, variable_cost_change_pct
    )
