"""Shared test helpers."""

from __future__ import annotations

import pandas as pd


def regression_frame(bundle: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Pandas equivalent of ``vw_pricing_regression_input`` (no DuckDB needed)."""

    fact = bundle["fact_pricing"]
    return (
        fact.merge(bundle["dim_date"][["month_id", "month"]], on="month_id")
        .merge(bundle["dim_region"][["region_id", "region_name"]], on="region_id")
        .merge(bundle["dim_product"][["product_id", "product_name"]], on="product_id")
        .merge(
            bundle["dim_customer_segment"][["customer_segment_id", "customer_segment_name"]],
            on="customer_segment_id",
        )
    )
