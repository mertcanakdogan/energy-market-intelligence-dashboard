from __future__ import annotations

import pandas as pd
import pytest

from energy_market_intelligence.validation import DataValidationError, validate_pricing_bundle


def copied(bundle: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: frame.copy() for name, frame in bundle.items()}


def test_valid_pricing_bundle_passes(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    validate_pricing_bundle(synthetic_bundle)


@pytest.mark.parametrize("table", ["dim_customer_segment", "dim_discount_policy", "fact_pricing"])
def test_missing_pricing_table_fails(synthetic_bundle: dict[str, pd.DataFrame], table: str) -> None:
    data = copied(synthetic_bundle)
    del data[table]
    with pytest.raises(DataValidationError, match="Missing required table"):
        validate_pricing_bundle(data)


def test_missing_pricing_column_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_pricing"] = data["fact_pricing"].drop(columns="pocket_price")
    with pytest.raises(DataValidationError, match="missing columns"):
        validate_pricing_bundle(data)


def test_duplicate_grain_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_pricing"] = pd.concat([data["fact_pricing"], data["fact_pricing"].iloc[:1]])
    with pytest.raises(DataValidationError, match="duplicate grain"):
        validate_pricing_bundle(data)


def test_unknown_segment_key_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_pricing"].loc[data["fact_pricing"].index[0], "customer_segment_id"] = 99
    with pytest.raises(DataValidationError, match="unknown values"):
        validate_pricing_bundle(data)


def test_broken_waterfall_identity_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_pricing"].loc[data["fact_pricing"].index[0], "pocket_price"] += 1.0
    with pytest.raises(DataValidationError, match="does not reconcile"):
        validate_pricing_bundle(data)


def test_non_positive_price_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_pricing"].loc[data["fact_pricing"].index[0], "competitor_price"] = 0.0
    with pytest.raises(DataValidationError, match="positive"):
        validate_pricing_bundle(data)


def test_negative_deduction_fails(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    data = copied(synthetic_bundle)
    data["fact_pricing"].loc[data["fact_pricing"].index[0], "off_invoice_rebate"] = -0.5
    with pytest.raises(DataValidationError, match="negative"):
        validate_pricing_bundle(data)
