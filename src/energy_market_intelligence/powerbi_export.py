"""Export the pricing star schema as tidy CSV files for Power BI."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

POWERBI_TABLES = (
    "fact_pricing",
    "dim_date",
    "dim_region",
    "dim_product",
    "dim_customer_segment",
    "dim_discount_policy",
)


def export_powerbi_star_schema(bundle: Mapping[str, pd.DataFrame], directory: Path) -> list[Path]:
    """Write one CSV per star-schema table (ISO dates, no index) and return the paths."""

    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name in POWERBI_TABLES:
        if name not in bundle:
            raise KeyError(f"cannot export missing table: {name}")
        frame = bundle[name].copy()
        for column in frame.columns:
            if pd.api.types.is_datetime64_any_dtype(frame[column]):
                frame[column] = frame[column].dt.strftime("%Y-%m-%d")
        path = directory / f"{name}.csv"
        frame.to_csv(path, index=False)
        written.append(path)
    return written
