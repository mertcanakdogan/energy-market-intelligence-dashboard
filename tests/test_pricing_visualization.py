from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from energy_market_intelligence.database import query_dataframe
from energy_market_intelligence.elasticity import estimate_segment_elasticities
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.pricing_visualization import (
    elasticity_recovery_figure,
    price_recommendation_figure,
    price_waterfall_figure,
    promo_did_figure,
    pvm_bridge_figure,
    segment_waterfall_table,
)
from energy_market_intelligence.promotion import estimate_promo_uplift, treated_control_trend


def test_segment_waterfall_table_is_per_mwh_and_reconciles(waterfall_frame: pd.DataFrame) -> None:
    table = segment_waterfall_table(waterfall_frame)
    assert len(table) == 3
    deductions = table[
        ["on_invoice_discount", "off_invoice_rebate", "payment_term_cost", "freight_service_cost"]
    ].sum(axis=1)
    assert ((table["list_price"] - deductions - table["pocket_price"]).abs() < 1e-6).all()


def test_price_waterfall_figure_has_one_panel_per_segment(waterfall_frame: pd.DataFrame) -> None:
    figure = price_waterfall_figure(waterfall_frame)
    waterfalls = [trace for trace in figure.data if isinstance(trace, go.Waterfall)]
    assert len(waterfalls) == 3
    assert all(len(trace.x) == 7 for trace in waterfalls)


def test_pvm_bridge_figure_shows_revenue_and_gross_profit_panels(analytics_db: Path) -> None:
    summary = query_dataframe(analytics_db, "SELECT * FROM vw_pvm_bridge_summary")
    figure = pvm_bridge_figure(summary)
    assert [len(trace.x) for trace in figure.data] == [4, 5]


@pytest.fixture(scope="module")
def estimates(pricing_frame: pd.DataFrame, pricing_config: PricingConfig):
    elasticity = estimate_segment_elasticities(pricing_frame, pricing_config.true_elasticities)
    promo = estimate_promo_uplift(pricing_frame, pricing_config.promotion.true_volume_uplift)
    return elasticity, promo


def test_elasticity_and_promo_figures_include_the_truth(
    estimates, pricing_frame: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    elasticity, promo = estimates
    recovery = elasticity_recovery_figure(elasticity)
    assert [trace.name for trace in recovery.data] == [
        "Tahmin (%95 güven aralığı)",
        "Gerçek değer (veri üreticisi)",
    ]
    window = (pricing_config.promotion.start_month_id, pricing_config.promotion.end_month_id)
    did = promo_did_figure(promo, treated_control_trend(pricing_frame), window)
    assert len(did.data) == 3


def test_recommendation_figure_has_one_bar_per_segment(
    estimates, waterfall_frame: pd.DataFrame, pricing_config: PricingConfig
) -> None:
    table = recommend_prices(waterfall_frame, estimates[0], 0.05, 0.15)
    figure = price_recommendation_figure(table)
    assert len(figure.data[0].y) == 3
