from __future__ import annotations

import pandas as pd
import pytest

from energy_market_intelligence.validation import DataValidationError, validate_bundle


def copied(bundle: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: frame.copy() for name, frame in bundle.items()}


def test_valid_bundle_passes(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    validate_bundle(synthetic_bundle)


@pytest.mark.parametrize(
    "table", ["dim_date", "dim_region", "dim_company", "dim_product", "fact_sales"]
)
def test_missing_required_table_fails(
    synthetic_bundle: dict[str, pd.DataFrame], table: str
) -> None:
    data = copied(synthetic_bundle)
    del data[table]
    with pytest.raises(DataValidationError, match="Missing required table"):
        validate_bundle(data)


def test_missing_required_column_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"] = data["fact_sales"].drop(columns="revenue")
    with pytest.raises(DataValidationError, match="missing columns"):
        validate_bundle(data)


def test_null_key_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"].loc[0, "region_id"] = None
    with pytest.raises(DataValidationError, match="null key"):
        validate_bundle(data)


def test_duplicate_fact_grain_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"] = pd.concat([data["fact_sales"], data["fact_sales"].iloc[[0]]])
    with pytest.raises(DataValidationError, match="duplicate grain"):
        validate_bundle(data)


def test_negative_volume_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"].loc[0, "volume_mwh"] = -1
    with pytest.raises(DataValidationError, match="negative volume"):
        validate_bundle(data)


def test_inconsistent_revenue_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"].loc[0, "revenue"] += 100
    with pytest.raises(DataValidationError, match="revenue calculation"):
        validate_bundle(data)


def test_inconsistent_gross_profit_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"].loc[0, "gross_profit"] += 100
    with pytest.raises(DataValidationError, match="gross profit"):
        validate_bundle(data)


def test_missing_dimension_key_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"].loc[0, "company_id"] = 999
    with pytest.raises(DataValidationError, match="missing dimension key"):
        validate_bundle(data)


def test_invalid_date_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["dim_date"]["date"] = data["dim_date"]["date"].astype(object)
    data["dim_date"].loc[0, "date"] = "not-a-date"
    with pytest.raises(DataValidationError, match="invalid date"):
        validate_bundle(data)


def test_impossible_margin_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_sales"].loc[0, "gross_margin_pct"] = 1.5
    with pytest.raises(DataValidationError, match="gross margin"):
        validate_bundle(data)
