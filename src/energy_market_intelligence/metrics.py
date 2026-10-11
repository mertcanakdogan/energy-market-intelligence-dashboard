"""General commercial metric calculations."""

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
