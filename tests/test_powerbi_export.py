from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from energy_market_intelligence.powerbi_export import POWERBI_TABLES, export_powerbi_star_schema


def test_export_writes_one_csv_per_star_schema_table(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame]
) -> None:
    written = export_powerbi_star_schema(synthetic_bundle, tmp_path / "pbi")
    assert {path.stem for path in written} == set(POWERBI_TABLES)
    assert all(path.exists() for path in written)


def test_exported_fact_round_trips_and_keeps_the_grain(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame]
) -> None:
    export_powerbi_star_schema(synthetic_bundle, tmp_path)
    fact = pd.read_csv(tmp_path / "fact_pricing.csv")
    assert len(fact) == len(synthetic_bundle["fact_pricing"])
    keys = ["month_id", "region_id", "product_id", "customer_segment_id"]
    assert not fact.duplicated(keys).any()
    assert {"list_price", "pocket_price", "pocket_revenue", "gross_profit"}.issubset(fact.columns)


def test_dates_are_exported_as_iso_strings(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame]
) -> None:
    export_powerbi_star_schema(synthetic_bundle, tmp_path)
    dates = pd.read_csv(tmp_path / "dim_date.csv")
    assert dates["date"].iloc[0] == "2023-01-01"


def test_missing_table_is_reported(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame]
) -> None:
    incomplete = {k: v for k, v in synthetic_bundle.items() if k != "dim_product"}
    with pytest.raises(KeyError, match="dim_product"):
        export_powerbi_star_schema(incomplete, tmp_path)
