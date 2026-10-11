"""Constant-elasticity price recommendations with a step cap and a margin floor.

This is a decision aid, not an optimiser to be run unattended. It assumes that

* volume responds to *pocket* price with the estimated constant elasticity,
* unit variable cost and competitor prices do not react to the price move, and
* the estimated elasticity holds over the (small) price step that is recommended.

Rules, applied in this order for every group:

1. Elastic (elasticity < -1): the unconstrained profit-maximising price is ``c * e / (1 + e)``
   with unit cost ``c``. Inelastic (elasticity >= -1): profit rises with price, so the
   unconstrained target is the largest allowed increase.
2. The move is capped at ``+/- max_step`` of the current pocket price.
3. An optional volume-loss guard limits an increase to the price at which the expected volume
   loss equals ``max_volume_loss``.
4. The margin floor ``(price - c) / price >= floor`` is enforced last, and wins over the guard:
   the price is lifted to ``c / (1 - floor)`` if that is reachable within the step cap,
   otherwise the full cap is used and the group is flagged as not reaching the floor.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

BASELINE_COLUMNS = {"volume_mwh", "pocket_revenue", "variable_cost"}
DEFAULT_GROUP = ("customer_segment_name",)


def recommend_price_change(
    current_price: float,
    unit_cost: float,
    elasticity: float,
    max_step: float,
    margin_floor: float,
    max_volume_loss: float | None = None,
) -> dict[str, float | str]:
    """Recommend a pocket-price change (fraction of the current price) for one group."""

    if current_price <= 0 or unit_cost < 0:
        raise ValueError("current price must be positive and unit cost non-negative")
    if not 0 <= margin_floor < 1:
        raise ValueError("margin_floor must be in [0, 1)")
    if max_step <= 0:
        raise ValueError("max_step must be positive")
    if max_volume_loss is not None and not 0 < max_volume_loss < 1:
        raise ValueError("max_volume_loss must be in (0, 1)")
    lower = current_price * (1 - max_step)
    cap_upper = current_price * (1 + max_step)
    upper, upper_label = cap_upper, "step cap"
    if max_volume_loss is not None and elasticity < 0:
        # Largest price ratio r with r ** elasticity >= 1 - max_volume_loss.
        guard_upper = current_price * (1 - max_volume_loss) ** (1 / elasticity)
        if guard_upper < cap_upper:
            upper, upper_label = guard_upper, "volume-loss guard"
    if elasticity < -1:
        optimum = unit_cost * elasticity / (1 + elasticity)
        target, basis = optimum, "profit-maximising price"
    else:
        optimum = float("nan")
        target, basis = cap_upper, "inelastic demand: raise to the step cap"
    new_price = min(max(target, lower), upper)
    if new_price == target:
        binding = basis
    else:
        binding = upper_label if target > upper else "step cap"
    floor_price = unit_cost / (1 - margin_floor)
    if new_price < floor_price:
        reachable = floor_price <= cap_upper
        new_price = floor_price if reachable else cap_upper
        binding = "margin floor" if reachable else "margin floor (not reachable in one step)"
    return {
        "recommended_price": new_price,
        "price_change_pct": new_price / current_price - 1,
        "unconstrained_optimum": optimum,
        "binding_constraint": binding,
    }


def _expected_gross_profit(volume: float, price: float, unit_cost: float) -> float:
    return volume * (price - unit_cost)


def recommend_prices(
    baseline: pd.DataFrame,
    elasticities: pd.DataFrame,
    max_step: float,
    margin_floor: float,
    group_columns: Sequence[str] = DEFAULT_GROUP,
    max_volume_loss: float | None = None,
) -> pd.DataFrame:
    """Build the recommendation table for every group of ``baseline``.

    ``baseline`` needs ``volume_mwh``, ``pocket_revenue`` and ``variable_cost`` (12-month totals)
    plus the grouping columns; ``elasticities`` is the output of
    :func:`energy_market_intelligence.elasticity.estimate_segment_elasticities`.
    """

    missing = BASELINE_COLUMNS.difference(baseline.columns)
    if missing:
        raise ValueError(f"baseline is missing columns: {sorted(missing)}")
    group_columns = list(group_columns)
    grouped = baseline.groupby(group_columns, as_index=False)[sorted(BASELINE_COLUMNS)].sum()
    merged = grouped.merge(
        elasticities[["customer_segment_name", "elasticity", "ci_low", "ci_high"]],
        on="customer_segment_name",
        how="left",
        validate="many_to_one",
    )
    if merged["elasticity"].isna().any():
        raise ValueError("no elasticity estimate for some customer segments")
    rows = []
    for record in merged.itertuples(index=False):
        price = record.pocket_revenue / record.volume_mwh
        cost = record.variable_cost / record.volume_mwh
        decision = recommend_price_change(
            price, cost, record.elasticity, max_step, margin_floor, max_volume_loss
        )
        change = float(decision["price_change_pct"])
        baseline_profit = _expected_gross_profit(record.volume_mwh, price, cost)
        new_price = float(decision["recommended_price"])

        def profit_at(elasticity: float, volume=record.volume_mwh, cost=cost) -> float:
            return _expected_gross_profit(volume * (1 + change) ** elasticity, new_price, cost)

        bounds = sorted(
            [profit_at(record.ci_low) - baseline_profit, profit_at(record.ci_high) - baseline_profit]
        )
        row = {column: getattr(record, column) for column in group_columns}
        row.update(
            {
                "baseline_volume_mwh": record.volume_mwh,
                "current_pocket_price": price,
                "unit_variable_cost": cost,
                "current_margin_pct": (price - cost) / price,
                "elasticity": record.elasticity,
                "elasticity_ci_low": record.ci_low,
                "elasticity_ci_high": record.ci_high,
                "recommended_pocket_price": new_price,
                "price_change_pct": change,
                "expected_volume_change_pct": (1 + change) ** record.elasticity - 1,
                "baseline_gross_profit": baseline_profit,
                "expected_gross_profit_change": profit_at(record.elasticity) - baseline_profit,
                "gross_profit_change_low": bounds[0],
                "gross_profit_change_high": bounds[1],
                "new_margin_pct": (new_price - cost) / new_price,
                "binding_constraint": decision["binding_constraint"],
            }
        )
        row["expected_gross_profit_change_pct"] = (
            row["expected_gross_profit_change"] / baseline_profit if baseline_profit else float("nan")
        )
        rows.append(row)
    return pd.DataFrame(rows)
