"""General commercial metric calculations and deterministic narrative signals."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide aligned series and return NaN where the denominator is zero."""

    return numerator.div(denominator.replace(0, np.nan))


def calculate_company_market_share(fact: pd.DataFrame) -> pd.DataFrame:
    """Aggregate product rows and calculate fractional share within month and region."""

    group = ["month_id", "region_id", "company_id"]
    result = fact.groupby(group, as_index=False)["volume_mwh"].sum()
    result["market_volume_mwh"] = result.groupby(["month_id", "region_id"])["volume_mwh"].transform(
        "sum"
    )
    result["market_share"] = safe_divide(result["volume_mwh"], result["market_volume_mwh"])
    return result


def add_growth_metrics(
    frame: pd.DataFrame,
    value_column: str,
    group_columns: Sequence[str],
    *,
    periods: int,
    label: str,
    date_column: str = "date",
) -> pd.DataFrame:
    """Add lag and fractional growth after stable group/date ordering."""

    sort_columns = [*group_columns, date_column]
    result = frame.sort_values(sort_columns).copy()
    if group_columns:
        prior = result.groupby(list(group_columns), dropna=False)[value_column].shift(periods)
    else:
        prior = result[value_column].shift(periods)
    result[f"{label}_prior"] = prior
    result[f"{label}_growth_pct"] = safe_divide(result[value_column] - prior, prior)
    return result


def add_rolling_metrics(
    frame: pd.DataFrame,
    value_column: str,
    group_columns: Sequence[str],
    *,
    windows: Sequence[int] = (3, 6),
    date_column: str = "date",
) -> pd.DataFrame:
    """Add trailing means with a one-period minimum for early observations."""

    result = frame.sort_values([*group_columns, date_column]).copy()
    for window in windows:
        output = f"{value_column}_rolling_{window}"
        if group_columns:
            result[output] = result.groupby(list(group_columns), dropna=False)[
                value_column
            ].transform(
                lambda values, current_window=window: values.rolling(
                    current_window, min_periods=1
                ).mean()
            )
        else:
            result[output] = result[value_column].rolling(window, min_periods=1).mean()
    return result


def generate_management_observations(
    kpis: dict[str, float], regional_opportunity: pd.DataFrame
) -> list[str]:
    """Create concise, rule-based observations using only calculated metrics."""

    share_change = kpis.get("share_change_pp", np.nan)
    market_growth = kpis.get("market_yoy_growth_pct", np.nan)
    margin_change = kpis.get("gross_margin_change_pp", np.nan)
    observations = [
        (
            f"Northstar share {'increased' if share_change >= 0 else 'decreased'} by "
            f"{abs(share_change):.1f} pp year over year while market volume "
            f"{'grew' if market_growth >= 0 else 'contracted'} {abs(market_growth):.1f}%."
        )
    ]
    if np.isfinite(margin_change):
        observations.append(
            f"Gross margin {'improved' if margin_change >= 0 else 'declined'} by "
            f"{abs(margin_change):.1f} pp versus the prior year."
        )
    if not regional_opportunity.empty:
        top = regional_opportunity.sort_values("opportunity_score", ascending=False).iloc[0]
        observations.append(
            f"{top['region_name']} is the highest analytical priority at "
            f"{top['opportunity_score']:.1f}/100, combining growth, share gap, "
            "margin, and competition signals."
        )
    return observations
