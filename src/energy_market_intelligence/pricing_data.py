"""Synthetic focus-company pricing ledger with a known waterfall and demand ground truth.

Grain of ``fact_pricing``: month x region x product x customer segment.

Data-generating process (all parameters come from ``config/default.yaml``):

* ``list_price``: product reference price x premium, raised by staggered regional increases.
* Waterfall: list -> on-invoice discount -> invoice -> off-invoice rebate -> payment-term cost
  -> freight/service cost -> pocket price. Discount depth varies by segment and region, with a
  few "leakage" regions above policy.
* Demand: constant-elasticity log-log model in *pocket* price with competitor price, seasonality,
  trend, promotion uplift and noise. The true elasticities are the config values.

The pricing ledger is a separate sub-ledger: its volume scale is calibrated to the
market fact, but its rows are not a reconciled split of ``fact_sales``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.synthetic_data import GeneratorConfig, generate_synthetic_data

FOCUS_COMPANY_ID = 1
PRICING_KEYS = ["month_id", "region_id", "product_id", "customer_segment_id"]


def _segment_dimensions(config: PricingConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    ids = np.arange(1, len(config.segments) + 1, dtype=int)
    names = [segment.name for segment in config.segments]
    segments = pd.DataFrame(
        {
            "customer_segment_id": ids,
            "customer_segment_name": names,
            "customer_segment_en": [segment.name_en for segment in config.segments],
            "payment_terms_days": [segment.payment_terms_days for segment in config.segments],
        }
    )
    policy = pd.DataFrame(
        {
            "customer_segment_id": ids,
            "customer_segment_name": names,
            "max_discount_pct": [segment.policy_max_discount_pct for segment in config.segments],
        }
    )
    return segments, policy


def _competitor_prices(market: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Volume-weighted competitor price by month x region x product from the market fact."""

    fact = market["fact_sales"]
    rivals = fact[fact["company_id"] != FOCUS_COMPANY_ID].copy()
    rivals["price_volume"] = rivals["average_price"] * rivals["volume_mwh"]
    grouped = rivals.groupby(["month_id", "region_id", "product_id"], as_index=False)[
        ["price_volume", "volume_mwh"]
    ].sum()
    grouped["competitor_price"] = grouped["price_volume"] / grouped["volume_mwh"]
    return grouped[["month_id", "region_id", "product_id", "competitor_price"]]


def _focus_base_volume(market: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fact = market["fact_sales"]
    own = fact[fact["company_id"] == FOCUS_COMPANY_ID]
    base = own.groupby(["region_id", "product_id"], as_index=False)["volume_mwh"].mean()
    return base.rename(columns={"volume_mwh": "base_volume"})


def _list_price_multiplier(region_name: pd.Series, month_id: np.ndarray, config: PricingConfig):
    multiplier = np.ones(len(region_name))
    for increase in config.list_price_increases:
        affected = region_name.isin(increase.regions).to_numpy() & (month_id >= increase.month_id)
        multiplier = np.where(affected, multiplier * (1.0 + increase.pct), multiplier)
    return multiplier


def _validate_config_against_market(market: dict[str, pd.DataFrame], config: PricingConfig):
    products = market["dim_product"]
    missing = set(products["product_name"]).difference(config.product_reference_price)
    if missing:
        raise ValueError(f"pricing.products is missing entries for: {sorted(missing)}")
    referenced = (
        set(config.leakage_regions)
        | set(config.promotion.treated_regions)
        | {name for increase in config.list_price_increases for name in increase.regions}
    )
    unknown = referenced.difference(market["dim_region"]["region_name"])
    if unknown:
        raise ValueError(f"pricing config references unknown regions: {sorted(unknown)}")


def generate_pricing_data(
    market: dict[str, pd.DataFrame], config: PricingConfig, seed: int
) -> dict[str, pd.DataFrame]:
    """Generate ``dim_customer_segment``, ``dim_discount_policy`` and ``fact_pricing``.

    The result is fully determined by ``seed`` and ``config``.
    """

    _validate_config_against_market(market, config)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 3]))
    dates, regions, products = market["dim_date"], market["dim_region"], market["dim_product"]
    segment_dim, policy_dim = _segment_dimensions(config)

    grid = pd.MultiIndex.from_product(
        [
            dates["month_id"],
            regions["region_id"],
            products["product_id"],
            segment_dim["customer_segment_id"],
        ],
        names=PRICING_KEYS,
    ).to_frame(index=False)
    n_rows = len(grid)
    month_id = grid["month_id"].to_numpy()
    region_id = grid["region_id"].to_numpy()
    product_id = grid["product_id"].to_numpy()
    seg = grid["customer_segment_id"].to_numpy()
    month_index = month_id - 1
    calendar_month = grid["month_id"].map(dates.set_index("month_id")["month"]).to_numpy()
    region_name = grid["region_id"].map(regions.set_index("region_id")["region_name"])
    product_name = grid["product_id"].map(products.set_index("product_id")["product_name"])
    specs = {index + 1: spec for index, spec in enumerate(config.segments)}

    def seg_value(attribute: str) -> np.ndarray:
        return np.array([getattr(specs[i], attribute) for i in seg], dtype=float)

    reference_price = product_name.map(config.product_reference_price).to_numpy(dtype=float)
    base_cost = product_name.map(config.product_unit_cost).to_numpy(dtype=float)

    promo = config.promotion
    promo_flag = (
        region_name.isin(promo.treated_regions).to_numpy()
        & (month_id >= promo.start_month_id)
        & (month_id <= promo.end_month_id)
    ).astype(int)

    # --- price waterfall ---------------------------------------------------------------
    economic = grid["region_id"].map(regions.set_index("region_id")["economic_index"]).to_numpy()
    list_price = (
        reference_price
        * config.list_price_premium
        * (1 + 0.05 * (economic - 1))
        * _list_price_multiplier(region_name, month_id, config)
    )
    offsets = rng.normal(0.0, 0.004, size=(len(regions) + 1, len(segment_dim) + 1))
    region_segment_offset = offsets[region_id, seg]
    leakage = region_name.map(config.leakage_regions).fillna(0.0).to_numpy(dtype=float)
    discount_pct = np.clip(
        seg_value("base_discount_pct")
        + leakage
        + region_segment_offset
        + rng.normal(0.0, config.discount_noise_sd, n_rows)
        + promo.promo_discount_pct * promo_flag,
        0.0,
        0.5,
    )
    on_invoice_discount = np.round(list_price * discount_pct, 6)
    list_price = np.round(list_price, 6)
    invoice_price = np.round(list_price - on_invoice_discount, 6)
    rebate_pct = np.clip(seg_value("rebate_pct") + rng.normal(0.0, 0.002, n_rows), 0.0, None)
    off_invoice_rebate = np.round(invoice_price * rebate_pct, 6)
    payment_term_cost = np.round(
        invoice_price * config.cost_of_capital_annual * seg_value("payment_terms_days") / 365.0, 6
    )
    logistics = 1 + 0.10 * np.sin(region_id)
    freight_service_cost = np.round(
        seg_value("freight_service_per_mwh") * logistics * (1 + rng.normal(0.0, 0.02, n_rows)), 6
    )
    pocket_price = np.round(
        list_price
        - on_invoice_discount
        - off_invoice_rebate
        - payment_term_cost
        - freight_service_cost,
        6,
    )
    unit_cost = np.round(
        base_cost
        * (1 + config.cost_inflation_per_month * month_index)
        * seg_value("unit_cost_factor")
        * rng.normal(1.0, 0.004, n_rows),
        6,
    )

    # --- demand ------------------------------------------------------------------------
    competitor = grid.merge(
        _competitor_prices(market), on=["month_id", "region_id", "product_id"], how="left"
    )["competitor_price"].to_numpy()
    base_volume = grid.merge(
        _focus_base_volume(market), on=["region_id", "product_id"], how="left"
    )["base_volume"].to_numpy()
    reference_pocket = reference_price * config.list_price_premium * (
        1 - seg_value("base_discount_pct")
    ) * (1 - seg_value("rebate_pct")) * (
        1 - config.cost_of_capital_annual * seg_value("payment_terms_days") / 365.0
    ) - seg_value("freight_service_per_mwh")
    cell_shape = (len(regions) + 1, len(products) + 1, len(segment_dim) + 1)
    cell_effect = rng.normal(0.0, 0.05, size=cell_shape)[region_id, product_id, seg]
    seasonality = np.log(np.array(config.seasonality))[calendar_month - 1]
    log_volume = (
        np.log(base_volume * seg_value("volume_share"))
        + cell_effect
        + seasonality
        + config.demand_trend_per_month * month_index
        + seg_value("true_elasticity") * np.log(pocket_price / reference_pocket)
        + config.cross_elasticity * np.log(competitor / reference_price)
        + np.log1p(promo.true_volume_uplift) * promo_flag
        + rng.normal(0.0, config.demand_noise_sd, n_rows)
    )
    volume = np.round(np.exp(log_volume), 2)

    fact = grid.copy()
    fact["volume_mwh"] = volume
    fact["promo_flag"] = promo_flag
    fact["list_price"] = list_price
    fact["on_invoice_discount"] = on_invoice_discount
    fact["invoice_price"] = invoice_price
    fact["off_invoice_rebate"] = off_invoice_rebate
    fact["payment_term_cost"] = payment_term_cost
    fact["freight_service_cost"] = freight_service_cost
    fact["pocket_price"] = pocket_price
    fact["unit_variable_cost"] = unit_cost
    fact["competitor_price"] = np.round(competitor, 6)
    fact["list_revenue"] = volume * list_price
    fact["on_invoice_discount_amount"] = volume * on_invoice_discount
    fact["invoice_revenue"] = volume * invoice_price
    fact["off_invoice_rebate_amount"] = volume * off_invoice_rebate
    fact["payment_term_cost_amount"] = volume * payment_term_cost
    fact["freight_service_cost_amount"] = volume * freight_service_cost
    fact["pocket_revenue"] = volume * pocket_price
    fact["variable_cost"] = volume * unit_cost
    fact["gross_profit"] = fact["pocket_revenue"] - fact["variable_cost"]
    return {
        "dim_customer_segment": segment_dim,
        "dim_discount_policy": policy_dim,
        "fact_pricing": fact,
    }


def generate_full_bundle(
    generator_config: GeneratorConfig, pricing_config: PricingConfig
) -> dict[str, pd.DataFrame]:
    """Market star schema plus the focus-company pricing tables, ready for validation and DuckDB."""

    market = generate_synthetic_data(generator_config)
    pricing = generate_pricing_data(market, pricing_config, generator_config.seed)
    return {**market, **pricing}
