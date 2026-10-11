from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from energy_market_intelligence.database import build_database, execute_sql_models, list_relations


def test_build_database_creates_star_schema(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame], project_root: Path
) -> None:
    db_path = tmp_path / "analytics.duckdb"
    build_database(synthetic_bundle, db_path, project_root / "sql")
    relations = list_relations(db_path)
    assert {
        "dim_date",
        "dim_region",
        "dim_company",
        "dim_product",
        "dim_customer_segment",
        "fact_sales",
        "fact_pricing",
    }.issubset(relations)


def test_all_sql_models_create_expected_views(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame], project_root: Path
) -> None:
    db_path = tmp_path / "analytics.duckdb"
    build_database(synthetic_bundle, db_path, project_root / "sql")
    relations = list_relations(db_path)
    expected = {
        "vw_market_metrics",
        "vw_growth_analysis",
        "vw_competitor_momentum",
        "vw_regional_concentration",
        "vw_profitability_summary",
        "vw_regional_opportunity_inputs",
        "vw_executive_kpis",
        "vw_price_waterfall",
        "vw_pvm_bridge",
    }
    assert expected.issubset(relations)


def test_sql_market_shares_sum_to_one(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame], project_root: Path
) -> None:
    db_path = tmp_path / "analytics.duckdb"
    build_database(synthetic_bundle, db_path, project_root / "sql")
    with duckdb.connect(str(db_path), read_only=True) as connection:
        result = connection.execute(
            "SELECT date, region_name, SUM(market_share) AS share "
            "FROM vw_company_monthly GROUP BY ALL"
        ).df()
    assert np.allclose(result["share"], 1.0)


def test_sql_hhi_is_within_fractional_bounds(
    tmp_path: Path, synthetic_bundle: dict[str, pd.DataFrame], project_root: Path
) -> None:
    db_path = tmp_path / "analytics.duckdb"
    build_database(synthetic_bundle, db_path, project_root / "sql")
    with duckdb.connect(str(db_path), read_only=True) as connection:
        result = connection.execute("SELECT hhi FROM vw_regional_concentration").df()
    assert result["hhi"].between(1 / 7, 1).all()


def test_execute_sql_models_uses_filename_order(tmp_path: Path) -> None:
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    (sql_dir / "01_first.sql").write_text(
        "CREATE TABLE ordered_test (value INTEGER);", encoding="utf-8"
    )
    (sql_dir / "02_second.sql").write_text("INSERT INTO ordered_test VALUES (2);", encoding="utf-8")
    with duckdb.connect() as connection:
        executed = execute_sql_models(connection, sql_dir)
        value = connection.execute("SELECT value FROM ordered_test").fetchone()[0]
    assert executed == ["01_first.sql", "02_second.sql"]
    assert value == 2
