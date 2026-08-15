from __future__ import annotations

import pandas as pd

from energy_market_intelligence.synthetic_data import GeneratorConfig, generate_synthetic_data


def test_generation_is_deterministic() -> None:
    left = generate_synthetic_data(GeneratorConfig(seed=42))
    right = generate_synthetic_data(GeneratorConfig(seed=42))
    pd.testing.assert_frame_equal(left["fact_sales"], right["fact_sales"])


def test_different_seed_changes_fact_values() -> None:
    left = generate_synthetic_data(GeneratorConfig(seed=1))["fact_sales"]
    right = generate_synthetic_data(GeneratorConfig(seed=2))["fact_sales"]
    assert not left["volume_mwh"].equals(right["volume_mwh"])


def test_dimension_cardinalities(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    assert len(synthetic_bundle["dim_date"]) == 36
    assert len(synthetic_bundle["dim_region"]) == 18
    assert len(synthetic_bundle["dim_company"]) == 7
    assert len(synthetic_bundle["dim_product"]) == 4


def test_fact_has_complete_declared_grain(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    fact = synthetic_bundle["fact_sales"]
    assert len(fact) == 36 * 18 * 7 * 4
    assert not fact.duplicated(["month_id", "region_id", "company_id", "product_id"]).any()


def test_financial_identities_hold(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    fact = synthetic_bundle["fact_sales"]
    assert (fact["revenue"] - fact["volume_mwh"] * fact["average_price"]).abs().max() < 0.02
    assert (fact["gross_profit"] - (fact["revenue"] - fact["variable_cost"])).abs().max() < 0.02


def test_all_commercial_values_are_non_negative(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    cols = ["volume_mwh", "average_price", "revenue", "variable_cost", "gross_profit"]
    assert (synthetic_bundle["fact_sales"][cols] >= 0).all().all()


def test_generator_contains_structured_growth_and_seasonality(
    synthetic_bundle: dict[str, pd.DataFrame],
) -> None:
    fact = synthetic_bundle["fact_sales"]
    monthly = fact.groupby("month_id")["volume_mwh"].sum()
    first_year = monthly.iloc[:12].sum()
    final_year = monthly.iloc[-12:].sum()
    monthly_pattern = monthly.groupby((monthly.index - 1) % 12).mean()
    assert final_year > first_year
    assert monthly_pattern.max() / monthly_pattern.min() > 1.08
