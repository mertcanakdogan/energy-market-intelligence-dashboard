from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest
from helpers import regression_frame

from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.pricing_data import PRICING_KEYS, generate_pricing_data
from energy_market_intelligence.synthetic_data import GeneratorConfig, generate_synthetic_data


@pytest.fixture(scope="module")
def small_market() -> dict[str, pd.DataFrame]:
    return generate_synthetic_data(GeneratorConfig(seed=7, months=30, regions=18))


def test_generation_is_reproducible(
    small_market: dict[str, pd.DataFrame], pricing_config: PricingConfig
) -> None:
    left = generate_pricing_data(small_market, pricing_config, seed=11)["fact_pricing"]
    right = generate_pricing_data(small_market, pricing_config, seed=11)["fact_pricing"]
    other = generate_pricing_data(small_market, pricing_config, seed=12)["fact_pricing"]
    pd.testing.assert_frame_equal(left, right)
    assert not left["volume_mwh"].equals(other["volume_mwh"])


def test_fact_has_declared_grain(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    fact = synthetic_bundle["fact_pricing"]
    assert len(fact) == 36 * 18 * 4 * 3
    assert not fact.duplicated(PRICING_KEYS).any()
    assert len(synthetic_bundle["dim_customer_segment"]) == 3


def test_waterfall_identity_list_minus_deductions_equals_pocket(
    synthetic_bundle: dict[str, pd.DataFrame],
) -> None:
    fact = synthetic_bundle["fact_pricing"]
    deductions = fact[
        ["on_invoice_discount", "off_invoice_rebate", "payment_term_cost", "freight_service_cost"]
    ].sum(axis=1)
    assert (fact["list_price"] - deductions - fact["pocket_price"]).abs().max() < 1e-4
    assert (
        fact["list_price"] - fact["on_invoice_discount"] - fact["invoice_price"]
    ).abs().max() < 1e-4
    assert (fact["pocket_revenue"] - fact["volume_mwh"] * fact["pocket_price"]).abs().max() < 0.01
    assert (
        fact["gross_profit"] - (fact["pocket_revenue"] - fact["variable_cost"])
    ).abs().max() < 0.01


def test_prices_volumes_and_margins_are_positive(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    fact = synthetic_bundle["fact_pricing"]
    assert (
        (fact[["list_price", "pocket_price", "unit_variable_cost", "volume_mwh"]] > 0).all().all()
    )
    assert (fact["gross_profit"] > 0).all()


def test_discount_depth_orders_by_segment(synthetic_bundle: dict[str, pd.DataFrame]) -> None:
    fact = synthetic_bundle["fact_pricing"].merge(
        synthetic_bundle["dim_customer_segment"], on="customer_segment_id"
    )
    depth = (
        (fact["on_invoice_discount"] / fact["list_price"])
        .groupby(fact["customer_segment_name"])
        .mean()
    )
    assert depth["Industrial"] > depth["Commercial (SME)"] > depth["Residential"]


def test_leakage_regions_discount_above_others(
    synthetic_bundle: dict[str, pd.DataFrame], pricing_config: PricingConfig
) -> None:
    frame = regression_frame(synthetic_bundle)
    frame["depth"] = frame["on_invoice_discount"] / frame["list_price"]
    by_region = frame[frame["promo_flag"] == 0].groupby("region_name")["depth"].mean()
    leaking = by_region[list(pricing_config.leakage_regions)]
    others = by_region.drop(list(pricing_config.leakage_regions))
    assert leaking.min() > others.max()


def test_list_price_increases_are_staggered_by_region(
    synthetic_bundle: dict[str, pd.DataFrame],
) -> None:
    frame = regression_frame(synthetic_bundle)
    cell = frame[
        (frame["product_name"] == "Fixed price")
        & (frame["customer_segment_name"] == "Commercial (SME)")
    ]
    steps = (
        cell.sort_values("month_id")
        .groupby("region_name")["list_price"]
        .apply(
            lambda prices: tuple(  # month_id of every list-price jump (rows are sorted by month_id)
                np.flatnonzero(prices.pct_change().abs().to_numpy() > 0.02) + 1
            )
        )
    )
    assert steps["Diyarbakır"] == ()
    assert steps["Tekirdağ"] == (7,)
    assert steps["Bursa"] == (14,)
    assert len({steps[name] for name in steps.index}) >= 4


def test_promotion_flags_only_treated_regions_inside_the_window(
    synthetic_bundle: dict[str, pd.DataFrame], pricing_config: PricingConfig
) -> None:
    frame = regression_frame(synthetic_bundle)
    flagged = frame[frame["promo_flag"] == 1]
    promo = pricing_config.promotion
    assert set(flagged["region_name"]) == set(promo.treated_regions)
    assert flagged["month_id"].min() == promo.start_month_id
    assert flagged["month_id"].max() == promo.end_month_id


def test_volume_scale_is_comparable_to_market_fact(
    synthetic_bundle: dict[str, pd.DataFrame],
) -> None:
    pricing_volume = synthetic_bundle["fact_pricing"]["volume_mwh"].sum()
    sales = synthetic_bundle["fact_sales"]
    market_volume = sales.loc[sales["company_id"] == 1, "volume_mwh"].sum()
    assert 0.8 < pricing_volume / market_volume < 1.25


def test_volume_falls_with_pocket_price_within_a_cell(
    synthetic_bundle: dict[str, pd.DataFrame],
) -> None:
    frame = regression_frame(synthetic_bundle)
    frame = frame[frame["customer_segment_name"] == "Residential"]
    demeaned = frame.assign(
        log_volume=np.log(frame["volume_mwh"]), log_price=np.log(frame["pocket_price"])
    )
    cell = ["region_name", "product_name"]
    for column in ("log_volume", "log_price"):
        demeaned[column] -= demeaned.groupby(cell)[column].transform("mean")
    assert demeaned["log_volume"].corr(demeaned["log_price"]) < -0.2


def test_unknown_province_in_config_is_rejected(
    small_market: dict[str, pd.DataFrame], pricing_config: PricingConfig
) -> None:
    broken = dataclasses.replace(pricing_config, leakage_regions={"Atlantis": 0.05})
    with pytest.raises(ValueError, match="unknown provinces"):
        generate_pricing_data(small_market, broken, seed=1)


def test_missing_product_in_config_is_rejected(
    small_market: dict[str, pd.DataFrame], pricing_config: PricingConfig
) -> None:
    prices = dict(pricing_config.product_reference_price)
    prices.pop("Fixed price")
    broken = dataclasses.replace(pricing_config, product_reference_price=prices)
    with pytest.raises(ValueError, match="missing entries"):
        generate_pricing_data(small_market, broken, seed=1)
