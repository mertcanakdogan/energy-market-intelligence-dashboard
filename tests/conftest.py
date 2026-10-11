from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from helpers import regression_frame

from energy_market_intelligence.database import build_database, query_dataframe
from energy_market_intelligence.pricing_config import PricingConfig, load_pricing_config
from energy_market_intelligence.pricing_data import generate_full_bundle
from energy_market_intelligence.synthetic_data import GeneratorConfig


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def pricing_config(project_root: Path) -> PricingConfig:
    return load_pricing_config(project_root / "config" / "default.yaml")


@pytest.fixture(scope="session")
def synthetic_bundle(pricing_config: PricingConfig) -> dict[str, pd.DataFrame]:
    """Market star schema plus the pricing tables, generated once per test session."""

    return generate_full_bundle(GeneratorConfig(seed=20260815), pricing_config)


@pytest.fixture(scope="session")
def pricing_frame(synthetic_bundle: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return regression_frame(synthetic_bundle)


@pytest.fixture(scope="session")
def analytics_db(
    tmp_path_factory: pytest.TempPathFactory,
    synthetic_bundle: dict[str, pd.DataFrame],
    project_root: Path,
) -> Path:
    """DuckDB database with every SQL model built from the shared bundle."""

    db_path = tmp_path_factory.mktemp("analytics") / "analytics.duckdb"
    build_database(synthetic_bundle, db_path, project_root / "sql")
    return db_path


@pytest.fixture(scope="session")
def waterfall_frame(analytics_db: Path) -> pd.DataFrame:
    return query_dataframe(analytics_db, "SELECT * FROM vw_price_waterfall")


@pytest.fixture()
def small_fact() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month_id": [1, 1, 2, 2],
            "region_id": [1, 1, 1, 1],
            "company_id": [1, 2, 1, 2],
            "product_id": [1, 1, 1, 1],
            "volume_mwh": [100.0, 300.0, 120.0, 280.0],
            "average_price": [50.0, 45.0, 55.0, 46.0],
            "revenue": [5000.0, 13500.0, 6600.0, 12880.0],
            "variable_cost": [3500.0, 10500.0, 4200.0, 10080.0],
            "gross_profit": [1500.0, 3000.0, 2400.0, 2800.0],
            "gross_margin_pct": [0.3, 3000 / 13500, 2400 / 6600, 2800 / 12880],
        }
    )
