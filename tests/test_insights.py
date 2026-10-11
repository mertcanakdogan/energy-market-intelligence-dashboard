from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from energy_market_intelligence.database import query_dataframe
from energy_market_intelligence.elasticity import estimate_segment_elasticities
from energy_market_intelligence.insights import (
    competition_insight,
    elasticity_insight,
    headline_findings,
    market_insight,
    opportunity_insight,
    performance_insight,
    price_waterfall_insight,
    profitability_insight,
    promo_insight,
    pvm_insight,
    recommendation_insight,
    scenario_insight,
)
from energy_market_intelligence.metrics import generate_management_observations
from energy_market_intelligence.opportunity import calculate_opportunity_scores
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.promotion import estimate_promo_uplift
from energy_market_intelligence.scenario import calculate_scenario


@pytest.fixture(scope="module")
def views(analytics_db: Path) -> dict[str, pd.DataFrame]:
    names = [
        "vw_discount_policy_flags",
        "vw_pvm_bridge_summary",
        "vw_executive_kpis",
        "vw_competitor_momentum",
        "vw_regional_concentration",
        "vw_regional_opportunity_inputs",
        "vw_profitability_summary",
        "vw_market_metrics",
    ]
    return {name: query_dataframe(analytics_db, f"SELECT * FROM {name}") for name in names}


@pytest.fixture(scope="module")
def estimates(pricing_frame: pd.DataFrame, pricing_config: PricingConfig):
    return (
        estimate_segment_elasticities(pricing_frame, pricing_config.true_elasticities),
        estimate_promo_uplift(pricing_frame, pricing_config.promotion.true_volume_uplift),
    )


def test_waterfall_insight_names_the_worst_segment_and_breaching_regions(
    waterfall_frame: pd.DataFrame, views: dict[str, pd.DataFrame]
) -> None:
    text = price_waterfall_insight(waterfall_frame, views["vw_discount_policy_flags"])
    realization = waterfall_frame["pocket_revenue"].sum() / waterfall_frame["list_revenue"].sum()
    assert f"{realization * 100:.1f}".replace(".", ",") in text
    assert "Sanayi" in text  # the segment with the widest list-to-pocket gap
    assert "mn TL" in text
    assert any(region in text for region in ("Ege Kuzey", "Doğu Anadolu Kuzey"))


def test_waterfall_insight_without_policy_breaches(
    waterfall_frame: pd.DataFrame, views: dict[str, pd.DataFrame]
) -> None:
    flags = views["vw_discount_policy_flags"].assign(exceeds_policy=False)
    assert "Hiçbir bölge" in price_waterfall_insight(waterfall_frame, flags)


def test_pvm_insight_reports_price_recovering_part_of_the_cost_increase(
    views: dict[str, pd.DataFrame],
) -> None:
    summary = views["vw_pvm_bridge_summary"]
    text = pvm_insight(summary)
    assert "Net ciro" in text and "Brüt kâr" in text and "telafi" in text
    flipped = summary.assign(gp_cost_effect=1.0, total_gp_change=1.0, total_revenue_change=-1.0)
    assert "telafi" not in pvm_insight(flipped)
    assert "azaldı" in pvm_insight(flipped)


def test_elasticity_and_promo_insights_state_the_truth_check(
    estimates: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    elasticity, promo = estimates
    text = elasticity_insight(elasticity)
    assert "Mesken -1,60" in text and "Sanayi -0,61" in text
    assert "3/3" in text
    assert "truth_in_ci" not in elasticity_insight(elasticity.drop(columns="truth_in_ci"))
    promo_text = promo_insight(promo)
    assert "%8,7" in promo_text and "%12,0" in promo_text and "%8,0" in promo_text
    assert "Gerçek" not in promo_insight(promo.drop(columns="true_uplift"))


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
    assert "artar" in text and "mn TL" in text and "karar destek" in text
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
    assert "azalır" in recommendation_insight(loss)


def test_market_page_insights_are_computed_from_the_views(
    views: dict[str, pd.DataFrame], pricing_config: PricingConfig, project_root: Path
) -> None:
    kpis = views["vw_executive_kpis"].iloc[0]
    assert "Pazar hacmi" in market_insight(kpis)
    text = competition_insight(views["vw_competitor_momentum"], views["vw_regional_concentration"])
    assert "Pazar lideri" in text and "Enerji" in text
    regional = (
        views["vw_market_metrics"]
        .groupby("date", as_index=False)[["market_volume_mwh", "focus_volume_mwh"]]
        .sum()
    )
    regional["focus_share"] = regional["focus_volume_mwh"] / regional["market_volume_mwh"]
    assert "mevsimsellik" in performance_insight(regional)
    summary = (
        views["vw_profitability_summary"]
        .groupby("region_name", as_index=False)[["revenue", "gross_profit"]]
        .sum()
    )
    summary["gross_margin_pct"] = summary["gross_profit"] / summary["revenue"]
    assert "En yüksek brüt marj" in profitability_insight(summary)
    weights = {
        "market_size": 0.2,
        "market_growth": 0.2,
        "share_gap": 0.2,
        "momentum": 0.15,
        "margin": 0.15,
        "competition": 0.1,
    }
    scores = calculate_opportunity_scores(views["vw_regional_opportunity_inputs"], weights)
    assert "Öncelik sıralamasında ilk bölge" in opportunity_insight(scores)


def test_scenario_insight_direction() -> None:
    baseline = {
        "volume_mwh": 1000.0,
        "revenue": 3_000_000.0,
        "variable_cost": 2_400_000.0,
        "gross_profit": 600_000.0,
    }
    gain = calculate_scenario(baseline, 5.0, -2.0, 0.0)
    loss = calculate_scenario(baseline, 0.0, -5.0, 0.0)
    assert "artar" in scenario_insight(gain)
    assert "azalır" in scenario_insight(loss)


def test_turkish_management_observations() -> None:
    kpis = {"share_change_pp": -1.2, "market_yoy_growth_pct": 4.5, "gross_margin_change_pp": 0.8}
    regions = pd.DataFrame({"region_name": ["Ankara"], "opportunity_score": [81.5]})
    text = " ".join(generate_management_observations(kpis, regions, language="tr"))
    assert "azaldı" in text and "%4,5" in text and "iyileşti" in text and "Ankara" in text
    assert "81,5/100" in text
    with pytest.raises(ValueError, match="language"):
        generate_management_observations(kpis, regions, language="de")
