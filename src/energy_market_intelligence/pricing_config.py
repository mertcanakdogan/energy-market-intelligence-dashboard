"""Typed access to the ``pricing:`` section of the project configuration.

The section doubles as the documented *ground truth* of the synthetic pricing data: elasticities,
promotion uplift and list-price increases that the generator uses are the same values that the
estimators are later compared with.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SegmentSpec:
    """Commercial and demand parameters of one customer segment."""

    name: str
    name_en: str
    true_elasticity: float
    base_discount_pct: float
    policy_max_discount_pct: float
    rebate_pct: float
    payment_terms_days: int
    freight_service_per_mwh: float
    unit_cost_factor: float
    volume_share: float


@dataclass(frozen=True)
class PriceIncrease:
    """One staggered list-price increase for a cohort of regions."""

    month_id: int
    pct: float
    regions: tuple[str, ...]


@dataclass(frozen=True)
class PromotionSpec:
    """Discount campaign with a known incremental volume uplift."""

    treated_regions: tuple[str, ...]
    start_month_id: int
    end_month_id: int
    promo_discount_pct: float
    true_volume_uplift: float


@dataclass(frozen=True)
class RecommendationSpec:
    """Guard rails for the price-recommendation decision aid."""

    max_price_step_pct: float
    margin_floor_pct: float
    max_volume_loss_pct: float


@dataclass(frozen=True)
class PricingConfig:
    """Everything the pricing generator and analytics need from ``config/default.yaml``."""

    product_reference_price: dict[str, float]
    product_unit_cost: dict[str, float]
    list_price_premium: float
    cost_inflation_per_month: float
    cost_of_capital_annual: float
    seasonality: tuple[float, ...]
    segments: tuple[SegmentSpec, ...]
    cross_elasticity: float
    demand_trend_per_month: float
    demand_noise_sd: float
    discount_noise_sd: float
    leakage_regions: dict[str, float]
    list_price_increases: tuple[PriceIncrease, ...]
    promotion: PromotionSpec
    recommendation: RecommendationSpec

    @property
    def true_elasticities(self) -> dict[str, float]:
        """Ground-truth own-price elasticity by customer segment."""

        return {segment.name: segment.true_elasticity for segment in self.segments}

    @property
    def policy_max_discount(self) -> dict[str, float]:
        """Policy discount-depth threshold by customer segment."""

        return {segment.name: segment.policy_max_discount_pct for segment in self.segments}

    @classmethod
    def from_mapping(cls, section: Mapping[str, Any]) -> PricingConfig:
        """Build and sanity-check the configuration from the parsed YAML ``pricing`` mapping."""

        products = section["products"]
        seasonality = tuple(float(value) for value in section["seasonality"])
        if len(seasonality) != 12:
            raise ValueError("pricing.seasonality must contain 12 monthly factors")
        segments = tuple(SegmentSpec(**dict(item)) for item in section["segments"])
        if abs(sum(segment.volume_share for segment in segments) - 1.0) > 1e-9:
            raise ValueError("pricing.segments volume_share values must sum to 1")
        if not any(s.true_elasticity < -1 for s in segments) or not any(
            s.true_elasticity > -1 for s in segments
        ):
            raise ValueError("pricing.segments must include an elastic and an inelastic segment")
        promo = section["promotion"]
        promotion = PromotionSpec(
            treated_regions=tuple(promo["treated_regions"]),
            start_month_id=int(promo["start_month_id"]),
            end_month_id=int(promo["end_month_id"]),
            promo_discount_pct=float(promo["promo_discount_pct"]),
            true_volume_uplift=float(promo["true_volume_uplift"]),
        )
        if promotion.end_month_id < promotion.start_month_id:
            raise ValueError("pricing.promotion window is empty")
        recommendation = RecommendationSpec(
            max_price_step_pct=float(section["recommendation"]["max_price_step_pct"]),
            margin_floor_pct=float(section["recommendation"]["margin_floor_pct"]),
            max_volume_loss_pct=float(section["recommendation"]["max_volume_loss_pct"]),
        )
        return cls(
            product_reference_price={k: float(v["reference_price"]) for k, v in products.items()},
            product_unit_cost={k: float(v["unit_cost"]) for k, v in products.items()},
            list_price_premium=float(section["list_price_premium"]),
            cost_inflation_per_month=float(section["cost_inflation_per_month"]),
            cost_of_capital_annual=float(section["cost_of_capital_annual"]),
            seasonality=seasonality,
            segments=segments,
            cross_elasticity=float(section["cross_elasticity"]),
            demand_trend_per_month=float(section["demand_trend_per_month"]),
            demand_noise_sd=float(section["demand_noise_sd"]),
            discount_noise_sd=float(section["discount_noise_sd"]),
            leakage_regions={k: float(v) for k, v in section["leakage_regions"].items()},
            list_price_increases=tuple(
                PriceIncrease(
                    month_id=int(item["month_id"]),
                    pct=float(item["pct"]),
                    regions=tuple(item["regions"]),
                )
                for item in section["list_price_increases"]
            ),
            promotion=promotion,
            recommendation=recommendation,
        )


def load_pricing_config(config_path: Path) -> PricingConfig:
    """Read ``config_path`` and return its parsed ``pricing`` section."""

    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return PricingConfig.from_mapping(config["pricing"])
