from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from energy_market_intelligence.database import build_database, list_relations, query_dataframe
from energy_market_intelligence.pricing_config import PricingConfig


def test_pricing_tables_and_views_exist(analytics_db: Path) -> None:
    relations = list_relations(analytics_db)
    assert {
        "dim_customer_segment",
        "dim_discount_policy",
        "fact_pricing",
        "vw_pricing_detail",
        "vw_pricing_regression_input",
        "vw_price_waterfall",
        "vw_discount_policy_flags",
        "vw_pvm_bridge",
        "vw_pvm_bridge_summary",
    }.issubset(relations)


def test_pricing_fact_row_count_and_grain(analytics_db: Path) -> None:
    result = query_dataframe(
        analytics_db,
        "SELECT COUNT(*) AS n, COUNT(DISTINCT (month_id, region_id, product_id, "
        "customer_segment_id)) AS d FROM fact_pricing",
    )
    assert result["n"].iloc[0] == result["d"].iloc[0] == 36 * 18 * 4 * 3


def test_waterfall_view_reconciles_list_to_pocket(waterfall_frame: pd.DataFrame) -> None:
    deductions = waterfall_frame[
        ["on_invoice_discount", "off_invoice_rebate", "payment_term_cost", "freight_service_cost"]
    ].sum(axis=1)
    assert np.allclose(waterfall_frame["list_price"] - deductions, waterfall_frame["pocket_price"])
    assert np.allclose(
        waterfall_frame["list_price"] - waterfall_frame["on_invoice_discount"],
        waterfall_frame["invoice_price"],
    )
    assert len(waterfall_frame) == 3 * 18 * 4


def test_waterfall_leakage_and_realization_are_complements(waterfall_frame: pd.DataFrame) -> None:
    assert np.allclose(waterfall_frame["leakage_pct"] + waterfall_frame["price_realization_pct"], 1)
    assert waterfall_frame["price_realization_pct"].between(0.6, 1).all()


def test_waterfall_covers_last_twelve_months_only(
    analytics_db: Path, waterfall_frame: pd.DataFrame
) -> None:
    last_year = query_dataframe(
        analytics_db,
        "SELECT SUM(volume_mwh) AS v FROM vw_pricing_detail WHERE month_id > "
        "(SELECT MAX(month_id) - 12 FROM vw_pricing_detail)",
    )
    assert np.isclose(waterfall_frame["volume_mwh"].sum(), last_year["v"].iloc[0])


def test_policy_flags_hit_exactly_the_configured_leakage_regions(
    analytics_db: Path, pricing_config: PricingConfig
) -> None:
    flags = query_dataframe(analytics_db, "SELECT * FROM vw_discount_policy_flags")
    assert len(flags) == 3 * 18
    breaching = set(flags.loc[flags["exceeds_policy"], "region_name"])
    assert breaching == set(pricing_config.leakage_regions)
    assert (flags.loc[~flags["exceeds_policy"], "revenue_leakage_above_policy"] == 0).all()
    assert (flags.loc[flags["exceeds_policy"], "revenue_leakage_above_policy"] > 0).all()


def test_policy_flags_use_the_configured_threshold(
    analytics_db: Path, pricing_config: PricingConfig
) -> None:
    flags = query_dataframe(analytics_db, "SELECT * FROM vw_discount_policy_flags")
    expected = flags["customer_segment_name"].map(pricing_config.policy_max_discount)
    assert np.allclose(flags["policy_max_discount_pct"], expected)
    assert np.allclose(
        flags["excess_discount_pp"],
        flags["on_invoice_discount_pct"] - flags["policy_max_discount_pct"],
    )
    ranks = flags[flags["excess_rank_in_segment"] == 1]
    assert len(ranks) == 3
    assert (ranks["exceeds_policy"]).all()


def test_pvm_bridge_reconciles_exactly(analytics_db: Path) -> None:
    bridge = query_dataframe(analytics_db, "SELECT * FROM vw_pvm_bridge")
    assert len(bridge) == 4 * 3
    assert bridge["reconciliation_gap"].abs().max() < 1e-6
    assert bridge["gp_reconciliation_gap"].abs().max() < 1e-6
    components = bridge["volume_effect"] + bridge["mix_effect"] + bridge["price_effect"]
    assert np.allclose(components, bridge["total_revenue_change"])


def test_pvm_summary_matches_cell_totals_and_total_change(analytics_db: Path) -> None:
    bridge = query_dataframe(analytics_db, "SELECT * FROM vw_pvm_bridge")
    summary = query_dataframe(analytics_db, "SELECT * FROM vw_pvm_bridge_summary").iloc[0]
    assert np.isclose(summary["total_revenue_change"], bridge["total_revenue_change"].sum())
    assert np.isclose(
        summary["current_revenue"] - summary["prior_revenue"], summary["total_revenue_change"]
    )
    assert abs(summary["reconciliation_gap"]) < 1e-6
    assert abs(summary["gp_reconciliation_gap"]) < 1e-6
    assert np.isclose(
        summary["gp_volume_effect"]
        + summary["gp_mix_effect"]
        + summary["gp_price_effect"]
        + summary["gp_cost_effect"],
        summary["total_gp_change"],
    )


def test_pvm_mix_effect_vanishes_when_cell_shares_are_unchanged(
    synthetic_bundle: dict[str, pd.DataFrame], project_root: Path, tmp_path: Path
) -> None:
    """When both years have identical cell shares, the mix effect must vanish."""

    bundle = {name: frame.copy() for name, frame in synthetic_bundle.items()}
    fact = bundle["fact_pricing"]
    current = fact["month_id"] > 24
    # Align the prior year's cell shares with the current year's.
    keys = ["product_id", "customer_segment_id"]
    prior_share = fact[fact["month_id"].between(13, 24)].groupby(keys)["volume_mwh"].sum()
    current_share = fact[current].groupby(keys)["volume_mwh"].sum()
    factor = (current_share / current_share.sum()) / (prior_share / prior_share.sum())
    scale = fact.set_index(keys).index.map(factor).to_numpy()
    prior_rows = fact["month_id"].between(13, 24).to_numpy()
    volume_columns = [
        "volume_mwh",
        "list_revenue",
        "on_invoice_discount_amount",
        "invoice_revenue",
        "off_invoice_rebate_amount",
        "payment_term_cost_amount",
        "freight_service_cost_amount",
        "pocket_revenue",
        "variable_cost",
        "gross_profit",
    ]
    for column in volume_columns:
        fact.loc[prior_rows, column] = fact.loc[prior_rows, column].to_numpy() * scale[prior_rows]
    db_path = tmp_path / "uniform.duckdb"
    build_database(bundle, db_path, project_root / "sql")
    bridge = query_dataframe(db_path, "SELECT * FROM vw_pvm_bridge_summary").iloc[0]
    assert abs(bridge["mix_effect"]) < 1e-4 * abs(bridge["volume_effect"])
    assert abs(bridge["reconciliation_gap"]) < 1e-6


def test_pvm_reconciles_when_a_cell_is_missing_in_the_prior_period(
    synthetic_bundle: dict[str, pd.DataFrame], project_root: Path, tmp_path: Path
) -> None:
    bundle = {name: frame.copy() for name, frame in synthetic_bundle.items()}
    fact = bundle["fact_pricing"]
    new_cell = (
        (fact["product_id"] == 1) & (fact["customer_segment_id"] == 3) & (fact["month_id"] <= 24)
    )
    bundle["fact_pricing"] = fact[~new_cell]
    db_path = tmp_path / "gap.duckdb"
    build_database(bundle, db_path, project_root / "sql")
    bridge = query_dataframe(db_path, "SELECT * FROM vw_pvm_bridge")
    assert len(bridge) == 12
    assert bridge["reconciliation_gap"].abs().max() < 1e-6
    assert bridge["gp_reconciliation_gap"].abs().max() < 1e-6
    created = bridge[(bridge["product_name"] == "Fixed price")]
    created = created[created["customer_segment_name"] == "Industrial"].iloc[0]
    assert created["prior_volume"] == 0
    assert created["price_effect"] == pytest.approx(0)
