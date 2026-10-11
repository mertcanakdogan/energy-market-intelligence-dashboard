"""Reusable, fail-loud validation for the synthetic star schema."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


class DataValidationError(ValueError):
    """Raised when a dataset violates an explicit analytical contract."""


REQUIRED_COLUMNS = {
    "dim_date": {"month_id", "date", "year", "quarter", "month", "month_name"},
    "dim_region": {
        "region_id",
        "region_name",
        "market_size_band",
        "economic_index",
        "strategic_segment",
    },
    "dim_company": {"company_id", "company_name", "company_type"},
    "dim_product": {"product_id", "product_name", "product_segment"},
    "fact_sales": {
        "month_id",
        "region_id",
        "company_id",
        "product_id",
        "volume_mwh",
        "average_price",
        "revenue",
        "variable_cost",
        "gross_profit",
        "gross_margin_pct",
    },
}

DIMENSION_KEYS = {
    "month_id": "dim_date",
    "region_id": "dim_region",
    "company_id": "dim_company",
    "product_id": "dim_product",
}


def _require_tables_and_columns(bundle: Mapping[str, pd.DataFrame]) -> None:
    for table, columns in REQUIRED_COLUMNS.items():
        if table not in bundle:
            raise DataValidationError(f"Missing required table: {table}")
        missing = columns.difference(bundle[table].columns)
        if missing:
            raise DataValidationError(f"{table} missing columns: {sorted(missing)}")


def validate_bundle(bundle: Mapping[str, pd.DataFrame], tolerance: float = 0.02) -> None:
    """Validate one row per month × region × company × product and its dimensions."""

    _require_tables_and_columns(bundle)
    fact = bundle["fact_sales"]
    grain = list(DIMENSION_KEYS)
    if fact[grain].isna().any().any():
        raise DataValidationError("fact_sales contains a null key")
    if fact.duplicated(grain).any():
        raise DataValidationError("fact_sales contains duplicate grain rows")
    if (fact["volume_mwh"] < 0).any():
        raise DataValidationError("fact_sales contains negative volume")
    if (
        not np.isfinite(
            fact[["volume_mwh", "average_price", "revenue", "variable_cost", "gross_profit"]]
        )
        .all()
        .all()
    ):
        raise DataValidationError("fact_sales contains non-finite commercial values")
    if (fact["revenue"] - fact["volume_mwh"] * fact["average_price"]).abs().max() > tolerance:
        raise DataValidationError("inconsistent revenue calculation")
    if (fact["gross_profit"] - (fact["revenue"] - fact["variable_cost"])).abs().max() > tolerance:
        raise DataValidationError("inconsistent gross profit calculation")
    expected_margin = fact["gross_profit"].div(fact["revenue"].replace(0, np.nan)).fillna(0)
    if (expected_margin - fact["gross_margin_pct"]).abs().max() > 0.0001:
        raise DataValidationError("inconsistent gross margin calculation")
    if not fact["gross_margin_pct"].between(-1, 1).all():
        raise DataValidationError("gross margin is outside the valid analytical range")

    for key, table_name in DIMENSION_KEYS.items():
        dimension = bundle[table_name]
        if dimension[key].isna().any():
            raise DataValidationError(f"{table_name} contains a null key")
        if dimension[key].duplicated().any():
            raise DataValidationError(f"{table_name} contains duplicate keys")
        unknown = set(fact[key]).difference(dimension[key])
        if unknown:
            raise DataValidationError(f"{key} has a missing dimension key: {sorted(unknown)[:3]}")

    parsed_dates = pd.to_datetime(bundle["dim_date"]["date"], errors="coerce", format="mixed")
    if parsed_dates.isna().any():
        raise DataValidationError("dim_date contains an invalid date")
    if not parsed_dates.is_monotonic_increasing or parsed_dates.duplicated().any():
        raise DataValidationError("dim_date dates must be unique and increasing")


def validate_market_shares(
    frame: pd.DataFrame, group_columns: list[str], share_column: str
) -> None:
    """Require fractional company shares in [0, 1] that total one per market."""

    if not frame[share_column].between(0, 1).all():
        raise DataValidationError("impossible market share outside [0, 1]")
    totals = frame.groupby(group_columns, dropna=False)[share_column].sum()
    if not np.allclose(totals, 1.0, atol=1e-6):
        raise DataValidationError("market shares do not sum to 1")


PRICING_REQUIRED_COLUMNS = {
    "dim_customer_segment": {"customer_segment_id", "customer_segment_name", "payment_terms_days"},
    "dim_discount_policy": {"customer_segment_id", "customer_segment_name", "max_discount_pct"},
    "fact_pricing": {
        "month_id",
        "region_id",
        "product_id",
        "customer_segment_id",
        "volume_mwh",
        "promo_flag",
        "list_price",
        "on_invoice_discount",
        "invoice_price",
        "off_invoice_rebate",
        "payment_term_cost",
        "freight_service_cost",
        "pocket_price",
        "unit_variable_cost",
        "competitor_price",
        "list_revenue",
        "pocket_revenue",
        "variable_cost",
        "gross_profit",
    },
}

PRICING_DIMENSION_KEYS = {
    "month_id": "dim_date",
    "region_id": "dim_region",
    "product_id": "dim_product",
    "customer_segment_id": "dim_customer_segment",
}
PRICING_KEYS = ["month_id", "region_id", "product_id", "customer_segment_id"]
WATERFALL_TOLERANCE = 1e-4


def validate_pricing_bundle(bundle: Mapping[str, pd.DataFrame]) -> None:
    """Validate the pricing fact: grain, keys, positive prices and the waterfall identity."""

    for table, columns in PRICING_REQUIRED_COLUMNS.items():
        if table not in bundle:
            raise DataValidationError(f"Missing required table: {table}")
        missing = columns.difference(bundle[table].columns)
        if missing:
            raise DataValidationError(f"{table} missing columns: {sorted(missing)}")
    fact = bundle["fact_pricing"]
    if fact[PRICING_KEYS].isna().any().any():
        raise DataValidationError("fact_pricing contains a null key")
    if fact.duplicated(PRICING_KEYS).any():
        raise DataValidationError("fact_pricing contains duplicate grain rows")
    for key, table_name in PRICING_DIMENSION_KEYS.items():
        unknown = set(fact[key]).difference(bundle[table_name][key])
        if unknown:
            raise DataValidationError(
                f"fact_pricing {key} has unknown values: {sorted(unknown)[:3]}"
            )
    price_columns = [
        "list_price",
        "invoice_price",
        "pocket_price",
        "unit_variable_cost",
        "competitor_price",
    ]
    if not np.isfinite(fact[price_columns + ["volume_mwh"]]).all().all():
        raise DataValidationError("fact_pricing contains non-finite values")
    if (fact[price_columns] <= 0).any().any() or (fact["volume_mwh"] <= 0).any():
        raise DataValidationError("fact_pricing requires positive prices and volumes")
    deductions = fact[
        ["on_invoice_discount", "off_invoice_rebate", "payment_term_cost", "freight_service_cost"]
    ]
    if (deductions < 0).any().any():
        raise DataValidationError("fact_pricing contains a negative waterfall deduction")
    gap = fact["list_price"] - deductions.sum(axis=1) - fact["pocket_price"]
    if gap.abs().max() > WATERFALL_TOLERANCE:
        raise DataValidationError("price waterfall does not reconcile list price to pocket price")
    invoice_gap = fact["list_price"] - fact["on_invoice_discount"] - fact["invoice_price"]
    if invoice_gap.abs().max() > WATERFALL_TOLERANCE:
        raise DataValidationError("invoice price does not equal list price less discount")
    revenue_gap = fact["pocket_revenue"] - fact["volume_mwh"] * fact["pocket_price"]
    if revenue_gap.abs().max() > 0.01:
        raise DataValidationError("pocket revenue is inconsistent with volume x pocket price")
