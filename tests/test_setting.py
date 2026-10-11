"""The fictional Turkish setting: names, currency scale, calendar and display conventions."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from energy_market_intelligence.localization import SEGMENT_ORDER
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.synthetic_data import (
    COMPANY_NAMES,
    FOCUS_COMPANY,
    PRODUCTS,
    REGION_NAMES,
)

EXPECTED_PROVINCES = [
    "Istanbul",
    "Kocaeli",
    "Tekirdağ",
    "Bursa",
    "Izmir",
    "Muğla",
    "Antalya",
    "Adana",
    "Konya",
    "Ankara",
    "Kayseri",
    "Zonguldak",
    "Samsun",
    "Trabzon",
    "Erzurum",
    "Van",
    "Gaziantep",
    "Diyarbakır",
]


def test_companies_are_fictional_invented_names_with_the_energy_suffix() -> None:
    assert len(COMPANY_NAMES) == 7
    assert len(set(COMPANY_NAMES)) == 7
    assert COMPANY_NAMES[0] == FOCUS_COMPANY == "Tavra Energy"
    for name in COMPANY_NAMES:
        assert re.fullmatch(r"[A-Z][a-z]+ Energy", name), name
    cities = {"Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Konya", "Kocaeli"}
    assert not any(city in name for name in COMPANY_NAMES for city in cities)


def test_sales_areas_are_eighteen_distinct_turkish_provinces() -> None:
    assert list(REGION_NAMES) == EXPECTED_PROVINCES
    assert len(set(REGION_NAMES)) == 18


def test_products_have_english_names_and_match_the_config(pricing_config: PricingConfig) -> None:
    names = [name for _id, name, _family in PRODUCTS]
    assert names == [
        "Fixed price",
        "Index-linked (PTF+)",
        "Green energy (YEK-G)",
        "Corporate bundle",
    ]
    assert set(names) == set(pricing_config.product_reference_price)


def test_segments_use_one_naming_convention_everywhere(
    synthetic_bundle: dict[str, pd.DataFrame], pricing_config: PricingConfig
) -> None:
    config_names = tuple(segment.name for segment in pricing_config.segments)
    assert config_names == SEGMENT_ORDER
    dimension = synthetic_bundle["dim_customer_segment"]
    assert tuple(dimension["customer_segment_name"]) == SEGMENT_ORDER
    assert "customer_segment_en" not in dimension.columns


def test_prices_are_realistic_turkish_lira_per_mwh(
    synthetic_bundle: dict[str, pd.DataFrame],
) -> None:
    fact = synthetic_bundle["fact_pricing"]
    assert 3000 <= fact["list_price"].min() and fact["list_price"].max() <= 4500
    assert 2000 <= fact["unit_variable_cost"].min() and fact["unit_variable_cost"].max() <= 3000
    margin = fact["gross_profit"].sum() / fact["pocket_revenue"].sum()
    assert 0.05 < margin < 0.25
    market = synthetic_bundle["fact_sales"]
    assert 2500 < market["average_price"].mean() < 4500


def test_pocket_margins_range_from_single_digit_to_high_twenties(
    waterfall_frame: pd.DataFrame,
) -> None:
    cells = waterfall_frame.groupby(["region_name", "customer_segment_name"])[
        ["gross_profit", "pocket_revenue"]
    ].sum()
    margins = cells["gross_profit"] / cells["pocket_revenue"]
    assert 0.05 < margins.min() < 0.10  # leakage-region industrial customers
    assert margins.max() < 0.30
    overall = waterfall_frame["gross_profit"].sum() / waterfall_frame["pocket_revenue"].sum()
    assert 0.15 < overall < 0.25


def test_time_axis_is_calendar_2023_to_2025(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    dates = pd.to_datetime(synthetic_bundle["dim_date"]["date"])
    assert dates.iloc[0] == pd.Timestamp("2023-01-01")
    assert dates.iloc[-1] == pd.Timestamp("2025-12-01")


def test_latest_twelve_months_are_calendar_year_2025(
    analytics_db, synthetic_bundle: dict[str, pd.DataFrame]
) -> None:
    from energy_market_intelligence.database import query_dataframe

    detail = query_dataframe(analytics_db, "SELECT date FROM vw_pricing_detail")
    latest = detail[detail["date"] > detail["date"].max() - pd.DateOffset(months=12)]
    assert latest["date"].dt.year.unique().tolist() == [2025]
    assert latest["date"].nunique() == 12


def test_seasonality_peaks_in_summer_and_winter(pricing_config: PricingConfig) -> None:
    factors = pricing_config.seasonality
    assert max(factors) in {factors[6], factors[7]}  # July or August cooling peak
    assert factors[0] > factors[4] and factors[11] > factors[4]  # winter above May


@pytest.mark.parametrize("province", EXPECTED_PROVINCES)
def test_every_province_exists_in_the_database(province: str, analytics_db) -> None:
    from energy_market_intelligence.database import query_dataframe

    names = set(query_dataframe(analytics_db, "SELECT region_name FROM dim_region")["region_name"])
    assert province in names
