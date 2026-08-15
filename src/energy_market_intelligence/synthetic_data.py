"""Deterministic, structured synthetic commercial data generation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

COMPANY_NAMES = (
    "Northstar Energy",
    "Meridian Power",
    "Atlas Energy",
    "Horizon Utilities",
    "Vertex Energy",
    "Summit Power",
    "Aurora Energy",
)

REGION_NAMES = (
    "North Coast",
    "Silver Plains",
    "Pine Valley",
    "Lake District",
    "Western Reach",
    "Redwood Corridor",
    "Central Basin",
    "Highland Zone",
    "Eastern Ridge",
    "Harbor Belt",
    "Cedar Fields",
    "Granite Valley",
    "Sunrise Coast",
    "Riverland",
    "Blue Mesa",
    "Maple Frontier",
    "Evergreen Basin",
    "Southern Cross",
)

PRODUCTS = (
    (1, "Fixed Supply", "Fixed"),
    (2, "Flexible Supply", "Flexible"),
    (3, "Renewable Blend", "Renewable"),
    (4, "Business Select", "Business"),
)


@dataclass(frozen=True)
class GeneratorConfig:
    """Public-demo controls for deterministic data generation."""

    seed: int = 20260815
    start_month: str = "2023-01-01"
    months: int = 36
    regions: int = 18


def _date_dimension(config: GeneratorConfig) -> pd.DataFrame:
    dates = pd.date_range(config.start_month, periods=config.months, freq="MS")
    return pd.DataFrame(
        {
            "month_id": np.arange(1, len(dates) + 1, dtype=int),
            "date": dates,
            "year": dates.year,
            "quarter": "Q" + dates.quarter.astype(str),
            "month": dates.month,
            "month_name": dates.strftime("%b"),
        }
    )


def _region_dimension(config: GeneratorConfig) -> pd.DataFrame:
    if not 1 <= config.regions <= len(REGION_NAMES):
        raise ValueError(f"regions must be between 1 and {len(REGION_NAMES)}")
    sizes = np.linspace(0.78, 1.35, config.regions)
    economic = np.array(
        [
            0.92,
            1.08,
            0.98,
            1.15,
            0.88,
            1.12,
            1.03,
            0.95,
            1.18,
            1.10,
            0.91,
            1.00,
            1.22,
            1.06,
            0.86,
            0.97,
            1.16,
            0.90,
        ]
    )[: config.regions]
    return pd.DataFrame(
        {
            "region_id": np.arange(1, config.regions + 1, dtype=int),
            "region_name": REGION_NAMES[: config.regions],
            "market_size_band": pd.cut(
                sizes, bins=[0, 0.95, 1.15, np.inf], labels=["Small", "Medium", "Large"]
            ).astype(str),
            "economic_index": economic,
            "strategic_segment": [
                ("Develop" if index % 5 == 0 else "Defend" if index % 4 == 0 else "Core")
                for index in range(config.regions)
            ],
            "size_factor": sizes,
        }
    )


def _company_dimension() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": np.arange(1, len(COMPANY_NAMES) + 1, dtype=int),
            "company_name": COMPANY_NAMES,
            "company_type": ["Focus company"] + ["Competitor"] * (len(COMPANY_NAMES) - 1),
        }
    )


def _product_dimension() -> pd.DataFrame:
    return pd.DataFrame(PRODUCTS, columns=["product_id", "product_name", "product_segment"])


def _commercial_fact(
    dates: pd.DataFrame,
    regions: pd.DataFrame,
    companies: pd.DataFrame,
    products: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    seasonality = np.array([1.12, 1.08, 1.02, 0.96, 0.91, 0.88, 0.90, 0.94, 0.99, 1.04, 1.09, 1.15])
    regional_monthly_growth = np.array(
        [
            0.0045,
            0.0030,
            0.0010,
            0.0052,
            -0.0010,
            0.0040,
            0.0022,
            -0.0018,
            0.0058,
            0.0038,
            -0.0008,
            0.0016,
            0.0062,
            0.0034,
            -0.0022,
            0.0012,
            0.0050,
            -0.0014,
        ]
    )[: len(regions)]
    product_mix = np.array([0.34, 0.27, 0.17, 0.22])
    product_growth = np.array([-0.0005, 0.0010, 0.0045, 0.0020])
    base_company_weight = np.array([0.18, 0.20, 0.16, 0.15, 0.12, 0.10, 0.09])
    company_monthly_momentum = np.array([0.0018, -0.0012, 0.0030, -0.0006, 0.0010, -0.0014, 0.0004])
    company_price_position = np.array([1.02, 0.98, 1.04, 0.97, 1.01, 0.96, 1.03])
    product_price = np.array([76.0, 72.0, 82.0, 78.0])
    product_cost = np.array([58.0, 56.0, 63.0, 59.0])
    rows: list[dict[str, float | int]] = []

    for date_row in dates.itertuples(index=False):
        month_index = int(date_row.month_id) - 1
        annual_trend = 1.0 + 0.0025 * month_index
        cost_inflation = 1.0 + 0.0030 * month_index
        compression = 1.035 if 18 <= month_index <= 25 else 1.0
        for region in regions.itertuples(index=False):
            region_index = int(region.region_id) - 1
            market_base = 28_000 * float(region.size_factor) * float(region.economic_index)
            region_trend = (1 + regional_monthly_growth[region_index]) ** month_index
            region_noise = rng.normal(1.0, 0.018)
            for product in products.itertuples(index=False):
                product_index = int(product.product_id) - 1
                total_product_volume = (
                    market_base
                    * seasonality[month_index % 12]
                    * annual_trend
                    * region_trend
                    * product_mix[product_index]
                    * (1 + product_growth[product_index]) ** month_index
                    * region_noise
                    * rng.normal(1.0, 0.012)
                )
                region_preferences = 1 + 0.10 * np.sin(
                    (region_index + 1) * (np.arange(len(companies)) + 1) * 0.71
                )
                if region_index in {8, 12, 16}:
                    region_preferences[0] *= 0.72
                if region_index in {3, 9}:
                    region_preferences[0] *= 1.25
                weights = (
                    base_company_weight
                    * region_preferences
                    * np.exp(company_monthly_momentum * month_index)
                    * rng.lognormal(0.0, 0.012, len(companies))
                )
                shares = weights / weights.sum()
                for company in companies.itertuples(index=False):
                    company_index = int(company.company_id) - 1
                    volume = max(total_product_volume * shares[company_index], 0.0)
                    market_price_trend = (
                        1 + 0.0018 * month_index + 0.018 * np.sin(month_index / 4.2)
                    )
                    average_price = (
                        product_price[product_index]
                        * company_price_position[company_index]
                        * market_price_trend
                        * (1 + 0.012 * (float(region.economic_index) - 1))
                        * rng.normal(1.0, 0.006)
                    )
                    efficiency = 0.985 if company_index == 0 else 1 + 0.008 * np.cos(company_index)
                    if company_index == 0 and region_index in {4, 7, 14, 17}:
                        efficiency *= 1.045
                    unit_cost = (
                        product_cost[product_index]
                        * cost_inflation
                        * compression
                        * efficiency
                        * rng.normal(1.0, 0.006)
                    )
                    volume = round(volume, 2)
                    average_price = round(average_price, 2)
                    revenue = round(volume * average_price, 2)
                    variable_cost = round(volume * unit_cost, 2)
                    gross_profit = round(revenue - variable_cost, 2)
                    rows.append(
                        {
                            "month_id": int(date_row.month_id),
                            "region_id": int(region.region_id),
                            "company_id": int(company.company_id),
                            "product_id": int(product.product_id),
                            "volume_mwh": volume,
                            "average_price": average_price,
                            "revenue": revenue,
                            "variable_cost": variable_cost,
                            "gross_profit": gross_profit,
                            "gross_margin_pct": round(gross_profit / revenue, 6)
                            if revenue
                            else 0.0,
                        }
                    )
    return pd.DataFrame(rows)


def generate_synthetic_data(config: GeneratorConfig | None = None) -> dict[str, pd.DataFrame]:
    """Generate a deterministic star-schema bundle using newly designed public-demo rules."""

    config = config or GeneratorConfig()
    rng = np.random.default_rng(config.seed)
    dates = _date_dimension(config)
    regions = _region_dimension(config)
    companies = _company_dimension()
    products = _product_dimension()
    fact = _commercial_fact(dates, regions, companies, products, rng)
    return {
        "dim_date": dates,
        "dim_region": regions.drop(columns="size_factor"),
        "dim_company": companies,
        "dim_product": products,
        "fact_sales": fact,
    }
