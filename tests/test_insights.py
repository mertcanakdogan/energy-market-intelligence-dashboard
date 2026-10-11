from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from energy_market_intelligence.database import query_dataframe
from energy_market_intelligence.elasticity import estimate_segment_elasticities
from energy_market_intelligence.insights import (
    elasticity_insight,
    headline_findings,
    price_waterfall_insight,
    promo_insight,
    pvm_insight,
    recommendation_insight,
)
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.promotion import estimate_promo_uplift


@pytest.fixture(scope="module")
def views(analytics_db: Path) -> dict[str, pd.DataFrame]:
    names = ["vw_discount_policy_flags", "vw_pvm_bridge_summary"]
    return {name: query_dataframe(analytics_db, f"SELECT * FROM {name}") for name in names}


@pytest.fixture(scope="module")
def estimates(pricing_frame: pd.DataFrame, pricing_config: PricingConfig):
    return (
        estimate_segment_elasticities(pricing_frame, pricing_config.true_elasticities),
        estimate_promo_uplift(pricing_frame, pricing_config.promotion.true_volume_uplift),
    )


def test_waterfall_insight_names_the_worst_segment_and_breaching_provinces(
    waterfall_frame: pd.DataFrame, views: dict[str, pd.DataFrame]
) -> None:
    text = price_waterfall_insight(waterfall_frame, views["vw_discount_policy_flags"])
    realization = waterfall_frame["pocket_revenue"].sum() / waterfall_frame["list_revenue"].sum()
    assert f"the company keeps TRY\u00a0{realization * 100:.1f} on average" in text
    assert "Industrial segment" in text  # the segment with the widest list-to-pocket gap
    assert "TRY/MWh" in text and "provinces" in text
    assert re.search(r"costs TRY\s\d+\.\dm a year", text)
    assert any(province in text for province in ("Izmir", "Erzurum"))


def test_waterfall_insight_without_policy_breaches(
    waterfall_frame: pd.DataFrame, views: dict[str, pd.DataFrame]
) -> None:
    flags = views["vw_discount_policy_flags"].assign(exceeds_policy=False)
    assert "No province gives discounts above the policy limit." in price_waterfall_insight(
        waterfall_frame, flags
    )


def test_pvm_insight_reports_price_recovering_part_of_the_cost_increase(
    views: dict[str, pd.DataFrame],
) -> None:
    summary = views["vw_pvm_bridge_summary"]
    text = pvm_insight(summary)
    assert "Net revenue" in text and "Gross profit" in text and "made up for" in text
    flipped = summary.assign(gp_cost_effect=1.0, total_gp_change=1.0, total_revenue_change=-1.0)
    assert "made up for" not in pvm_insight(flipped)
    assert "Net revenue fell by" in pvm_insight(flipped)


def test_elasticity_and_promo_insights_state_the_truth_check(
    estimates: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    elasticity, promo = estimates
    text = elasticity_insight(elasticity)
    assert "Residential \u22121.60" in text and "Industrial \u22120.61" in text
    assert "If prices rise 5%, volume falls about" in text
    assert "3 of 3 segments" in text
    assert "true values are known" not in elasticity_insight(elasticity.drop(columns="truth_in_ci"))
    promo_text = promo_insight(promo)
    assert "8.7%" in promo_text and "12.0%" in promo_text and "8.0%" in promo_text
    assert "true value" not in promo_insight(promo.drop(columns="true_uplift"))


def test_recommendation_insight_and_headline_findings(
    waterfall_frame: pd.DataFrame,
    views: dict[str, pd.DataFrame],
    estimates: tuple[pd.DataFrame, pd.DataFrame],
    pricing_config: PricingConfig,
) -> None:
    elasticity, promo = estimates
    spec = pricing_config.recommendation
    table = recommend_prices(
        waterfall_frame,
        elasticity,
        spec.max_price_step_pct,
        spec.margin_floor_pct,
        max_volume_loss=spec.max_volume_loss_pct,
    )
    text = recommendation_insight(table)
    assert "gross profit rises by TRY" in text and "a year" in text
    findings = headline_findings(
        waterfall_frame,
        views["vw_discount_policy_flags"],
        views["vw_pvm_bridge_summary"],
        elasticity,
        promo,
        table,
    )
    assert len(findings) == 4
    assert all(item and "nan" not in item.lower() for item in findings)
    loss = table.assign(
        expected_gross_profit_change=-1.0, price_change_pct=-0.01, expected_volume_change_pct=-0.01
    )
    assert "gross profit falls by" in recommendation_insight(loss)


def test_sentences_write_money_as_try(
    waterfall_frame: pd.DataFrame,
    views: dict[str, pd.DataFrame],
    estimates: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    elasticity, promo = estimates
    text = " ".join(
        [
            price_waterfall_insight(waterfall_frame, views["vw_discount_policy_flags"]),
            pvm_insight(views["vw_pvm_bridge_summary"]),
            elasticity_insight(elasticity),
            promo_insight(promo),
        ]
    )
    assert not re.search(r"\bTL\b", text)
    assert "\u20ba" not in text  # the lira sign
