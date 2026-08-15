from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from energy_market_intelligence.synthetic_data import GeneratorConfig, generate_synthetic_data


@pytest.fixture(scope="session")
def synthetic_bundle() -> dict[str, pd.DataFrame]:
    return generate_synthetic_data(GeneratorConfig(seed=20260815))


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


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]
