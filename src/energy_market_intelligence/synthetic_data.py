"""Deterministic, structured synthetic commercial data generation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# All names are fictional. Company names follow the pattern "<invented word> Enerji" and are not
# real companies; they were checked against web search (see README, "Fictional setting").
COMPANY_NAMES = (
    "Tavra Enerji",
    "Veyra Enerji",
    "Ormena Enerji",
    "Kuvara Enerji",
    "Yelkara Enerji",
    "Ozvela Enerji",
    "Alvora Enerji",
)
FOCUS_COMPANY = COMPANY_NAMES[0]

# Sales regions: (name, size factor, economic index, monthly volume growth). They follow the
# geography of Turkey but are deliberately not tied to single provinces or utilities.
REGIONS = (
    ("İstanbul Avrupa", 1.55, 1.25, 0.0040),
    ("İstanbul Anadolu", 1.35, 1.22, 0.0045),
    ("Trakya", 0.85, 1.08, 0.0020),
    ("Marmara Güney", 1.20, 1.12, 0.0030),
    ("Ege Kuzey", 1.10, 1.10, 0.0050),
    ("Ege Güney", 0.95, 1.02, 0.0034),
    ("Batı Akdeniz", 0.98, 1.00, 0.0042),
    ("Doğu Akdeniz", 1.05, 0.95, 0.0010),
    ("İç Anadolu Batı", 0.80, 0.94, 0.0012),
    ("Ankara", 1.30, 1.18, 0.0052),
    ("İç Anadolu Doğu", 0.82, 0.90, -0.0008),
    ("Batı Karadeniz", 0.82, 0.93, -0.0012),
    ("Orta Karadeniz", 0.78, 0.89, 0.0006),
    ("Doğu Karadeniz", 0.76, 0.90, 0.0016),
    ("Doğu Anadolu Kuzey", 0.70, 0.84, -0.0018),
    ("Doğu Anadolu Güney", 0.74, 0.82, 0.0022),
    ("Güneydoğu Batı", 0.90, 0.88, 0.0038),
    ("Güneydoğu Doğu", 0.72, 0.85, -0.0020),
)
REGION_NAMES = tuple(name for name, *_ in REGIONS)

# (product_id, product name, short product family). Prices and costs are constant 2025 TL.
PRODUCTS = (
    (1, "Sabit Fiyatlı", "Sabit"),
    (2, "Değişken Fiyatlı (PTF+)", "Değişken"),
    (3, "Yeşil Enerji (YEK-G)", "Yeşil"),
    (4, "Kurumsal Paket", "Kurumsal"),
)
# Reference list price and unit variable cost per product, TL per MWh (constant 2025 TL).
PRODUCT_REFERENCE_PRICE_TL = (3040.0, 2880.0, 3280.0, 3120.0)
PRODUCT_UNIT_COST_TL = (2320.0, 2240.0, 2520.0, 2360.0)
# Calendar seasonality: winter heating and summer cooling peaks, spring and autumn troughs.
SEASONALITY = (1.08, 1.04, 0.97, 0.93, 0.92, 0.99, 1.10, 1.12, 1.02, 0.94, 1.00, 1.09)
# Average monthly volume of one region with size and economic factors of 1 (MWh).
MARKET_BASE_MWH = 31_000


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
    if not 1 <= config.regions <= len(REGIONS):
        raise ValueError(f"regions must be between 1 and {len(REGIONS)}")
    selected = REGIONS[: config.regions]
    sizes = np.array([size for _name, size, _economic, _growth in selected])
    return pd.DataFrame(
        {
            "region_id": np.arange(1, config.regions + 1, dtype=int),
            "region_name": [name for name, *_ in selected],
            "market_size_band": pd.cut(
                sizes, bins=[0, 0.95, 1.15, np.inf], labels=["Küçük", "Orta", "Büyük"]
            ).astype(str),
            "economic_index": [economic for _name, _size, economic, _growth in selected],
            "strategic_segment": [
                ("Geliştir" if index % 5 == 0 else "Savun" if index % 4 == 0 else "Çekirdek")
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
    seasonality = np.array(SEASONALITY)
    regional_monthly_growth = np.array([growth for *_rest, growth in REGIONS])[: len(regions)]
    product_mix = np.array([0.34, 0.27, 0.17, 0.22])
    product_growth = np.array([-0.0005, 0.0010, 0.0045, 0.0020])
    base_company_weight = np.array([0.18, 0.20, 0.16, 0.15, 0.12, 0.10, 0.09])
    company_monthly_momentum = np.array([0.0018, -0.0012, 0.0030, -0.0006, 0.0010, -0.0014, 0.0004])
    company_price_position = np.array([1.02, 0.98, 1.04, 0.97, 1.01, 0.96, 1.03])
    product_price = np.array(PRODUCT_REFERENCE_PRICE_TL)
    product_cost = np.array(PRODUCT_UNIT_COST_TL)
    rows: list[dict[str, float | int]] = []

    for date_row in dates.itertuples(index=False):
        month_index = int(date_row.month_id) - 1
        annual_trend = 1.0 + 0.0025 * month_index
        cost_inflation = 1.0 + 0.0030 * month_index
        compression = 1.035 if 18 <= month_index <= 25 else 1.0
        for region in regions.itertuples(index=False):
            region_index = int(region.region_id) - 1
            market_base = MARKET_BASE_MWH * float(region.size_factor) * float(region.economic_index)
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
