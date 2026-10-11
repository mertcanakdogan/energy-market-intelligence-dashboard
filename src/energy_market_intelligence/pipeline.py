"""Reproducible end-to-end build for synthetic data, SQL models, analyses, and example outputs."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from energy_market_intelligence.database import build_database, query_dataframe
from energy_market_intelligence.elasticity import estimate_segment_elasticities
from energy_market_intelligence.opportunity import calculate_opportunity_scores
from energy_market_intelligence.powerbi_export import export_powerbi_star_schema
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.pricing_data import generate_full_bundle
from energy_market_intelligence.pricing_visualization import (
    elasticity_recovery_figure,
    price_recommendation_figure,
    price_waterfall_figure,
    promo_did_figure,
    pvm_bridge_figure,
    segment_waterfall_table,
)
from energy_market_intelligence.promotion import estimate_promo_uplift, treated_control_trend
from energy_market_intelligence.synthetic_data import GeneratorConfig
from energy_market_intelligence.validation import validate_bundle, validate_pricing_bundle
from energy_market_intelligence.visualization import (
    competitor_change_figure,
    gross_margin_trend_figure,
    market_share_trend_figure,
    opportunity_matrix_figure,
    profit_bridge_figure,
    write_png,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelinePaths:
    """All read/write locations used by one pipeline run."""

    project_root: Path
    config_path: Path
    sql_dir: Path
    raw_dir: Path
    database_path: Path
    output_dir: Path
    powerbi_dir: Path

    @classmethod
    def for_root(cls, project_root: Path, runtime_root: Path | None = None) -> PipelinePaths:
        runtime = runtime_root or project_root
        return cls(
            project_root=project_root,
            config_path=project_root / "config" / "default.yaml",
            sql_dir=project_root / "sql",
            raw_dir=runtime / "data" / "generated",
            database_path=runtime / "data" / "energy_market.duckdb",
            output_dir=runtime / "outputs" / "examples",
            powerbi_dir=runtime / "powerbi" / "data",
        )


@dataclass(frozen=True)
class Dataset:
    """Configuration, validated bundle and executed SQL scripts of one build."""

    config: dict[str, Any]
    pricing_config: PricingConfig
    generator_config: GeneratorConfig
    bundle: dict[str, pd.DataFrame]
    executed_scripts: list[str]


def _load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration must be a mapping: {path}")
    return config


def _write_raw_tables(bundle: dict[str, pd.DataFrame], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for table_name, frame in bundle.items():
        frame.to_csv(directory / f"{table_name}.csv", index=False)


def _fingerprint(frame: pd.DataFrame) -> str:
    hashes = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    return hashlib.sha256(hashes).hexdigest()


def _export_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, float_format="%.6f")


def build_dataset(paths: PipelinePaths, *, write_raw: bool = True) -> Dataset:
    """Generate, validate and load the synthetic data into DuckDB (no analysis outputs).

    This is also what the Streamlit app calls on first start when no database exists.
    """

    config = _load_config(paths.config_path)
    project_config = config["project"]
    generator_config = GeneratorConfig(
        seed=int(project_config["random_seed"]),
        start_month=str(project_config["start_month"]),
        months=int(project_config["months"]),
    )
    pricing_config = PricingConfig.from_mapping(config["pricing"])
    LOGGER.info("Generating deterministic synthetic star-schema data")
    bundle = generate_full_bundle(generator_config, pricing_config)
    validate_bundle(bundle, tolerance=float(config["validation"]["financial_tolerance"]))
    validate_pricing_bundle(bundle)
    if write_raw:
        _write_raw_tables(bundle, paths.raw_dir)
    executed = build_database(bundle, paths.database_path, paths.sql_dir)
    return Dataset(config, pricing_config, generator_config, bundle, executed)


def _query_outputs(database_path: Path, weights: dict[str, float]) -> dict[str, pd.DataFrame]:
    outputs = {
        "executive_kpis": query_dataframe(database_path, "SELECT * FROM vw_executive_kpis"),
        "competitor_momentum": query_dataframe(
            database_path, "SELECT * FROM vw_competitor_momentum ORDER BY momentum_rank"
        ),
        "profitability_summary": query_dataframe(
            database_path,
            "SELECT * FROM vw_profitability_summary ORDER BY gross_profit DESC",
        ),
        "market_share_trend": query_dataframe(
            database_path, "SELECT * FROM vw_growth_analysis ORDER BY date"
        ),
        "profit_bridge": query_dataframe(database_path, "SELECT * FROM vw_revenue_bridge"),
        "profitability_monthly": query_dataframe(
            database_path, "SELECT * FROM vw_focus_profitability_monthly ORDER BY date"
        ),
    }
    opportunity_inputs = query_dataframe(
        database_path, "SELECT * FROM vw_regional_opportunity_inputs ORDER BY region_name"
    )
    outputs["regional_opportunity"] = calculate_opportunity_scores(opportunity_inputs, weights)
    share_change = query_dataframe(
        database_path, "SELECT * FROM vw_regional_share_change ORDER BY share_change_pp DESC"
    )
    kpis = outputs["executive_kpis"].copy()
    kpis["largest_share_gain_region"] = share_change.iloc[0]["region_name"]
    kpis["largest_share_loss_region"] = share_change.iloc[-1]["region_name"]
    kpis["highest_opportunity_region"] = outputs["regional_opportunity"].iloc[0]["region_name"]
    outputs["executive_kpis"] = kpis
    return outputs


def _pricing_outputs(database_path: Path, pricing: PricingConfig) -> dict[str, pd.DataFrame]:
    """Run the SQL-backed waterfall/PVM views and the Python estimators."""

    waterfall = query_dataframe(database_path, "SELECT * FROM vw_price_waterfall")
    regression_input = query_dataframe(database_path, "SELECT * FROM vw_pricing_regression_input")
    elasticity = estimate_segment_elasticities(regression_input, pricing.true_elasticities)
    promo = estimate_promo_uplift(regression_input, pricing.promotion.true_volume_uplift)
    recommendation_spec = pricing.recommendation
    recommendation_args = (
        recommendation_spec.max_price_step_pct,
        recommendation_spec.margin_floor_pct,
    )
    guard = recommendation_spec.max_volume_loss_pct
    return {
        "price_waterfall_detail": waterfall,
        "price_waterfall": segment_waterfall_table(waterfall),
        "discount_policy_flags": query_dataframe(
            database_path,
            "SELECT * FROM vw_discount_policy_flags "
            "ORDER BY revenue_leakage_above_policy DESC, customer_segment_name, region_name",
        ),
        "pvm_bridge": query_dataframe(
            database_path,
            "SELECT * FROM vw_pvm_bridge ORDER BY product_name, customer_segment_name",
        ),
        "pvm_bridge_summary": query_dataframe(database_path, "SELECT * FROM vw_pvm_bridge_summary"),
        "elasticity_recovery": elasticity,
        "promo_did": promo,
        "promo_trend": treated_control_trend(regression_input),
        "price_recommendation": recommend_prices(
            waterfall,
            elasticity,
            *recommendation_args,
            group_columns=("customer_segment_name",),
            max_volume_loss=guard,
        ),
        "price_recommendation_by_region": recommend_prices(
            waterfall,
            elasticity,
            *recommendation_args,
            group_columns=("customer_segment_name", "region_name"),
            max_volume_loss=guard,
        ),
    }


def _write_charts(outputs: dict[str, pd.DataFrame], directory: Path, pricing: PricingConfig):
    promo = pricing.promotion
    figures = {
        "market_share_trend.png": market_share_trend_figure(outputs["market_share_trend"]),
        "regional_opportunity_matrix.png": opportunity_matrix_figure(
            outputs["regional_opportunity"]
        ),
        "competitor_share_change.png": competitor_change_figure(outputs["competitor_momentum"]),
        "gross_margin_trend.png": gross_margin_trend_figure(outputs["profitability_monthly"]),
        "profit_bridge.png": profit_bridge_figure(outputs["profit_bridge"]),
        "price_waterfall.png": price_waterfall_figure(outputs["price_waterfall_detail"]),
        "pvm_bridge.png": pvm_bridge_figure(outputs["pvm_bridge_summary"]),
        "elasticity_recovery.png": elasticity_recovery_figure(outputs["elasticity_recovery"]),
        "promo_did.png": promo_did_figure(
            outputs["promo_did"],
            outputs["promo_trend"],
            (promo.start_month_id, promo.end_month_id),
        ),
        "price_recommendation.png": price_recommendation_figure(outputs["price_recommendation"]),
    }
    for filename, figure in figures.items():
        write_png(figure, directory / filename)


def _pricing_headlines(outputs: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Compact, machine-readable headline numbers for run_metadata.json and the README."""

    waterfall = outputs["price_waterfall_detail"]
    flags = outputs["discount_policy_flags"]
    pvm = outputs["pvm_bridge_summary"].iloc[0]
    recommendation = outputs["price_recommendation"]
    list_revenue = float(waterfall["list_revenue"].sum())
    pocket_revenue = float(waterfall["pocket_revenue"].sum())
    breaches = flags[flags["exceeds_policy"]]
    return {
        "list_revenue_12m": round(list_revenue, 2),
        "pocket_revenue_12m": round(pocket_revenue, 2),
        "price_realization_pct": round(pocket_revenue / list_revenue, 6),
        "pocket_margin_pct": round(float(waterfall["gross_profit"].sum()) / pocket_revenue, 6),
        "region_segment_policy_breaches": int(len(breaches)),
        "breaching_regions": sorted(breaches["region_name"].unique().tolist()),
        "revenue_leakage_above_policy": round(
            float(flags["revenue_leakage_above_policy"].sum()), 2
        ),
        "pvm_total_revenue_change": round(float(pvm["total_revenue_change"]), 2),
        "pvm_price_effect": round(float(pvm["price_effect"]), 2),
        "pvm_volume_effect": round(float(pvm["volume_effect"]), 2),
        "pvm_mix_effect": round(float(pvm["mix_effect"]), 2),
        "pvm_gp_change": round(float(pvm["total_gp_change"]), 2),
        "pvm_gp_cost_effect": round(float(pvm["gp_cost_effect"]), 2),
        "pvm_max_abs_reconciliation_gap": float(
            outputs["pvm_bridge"][["reconciliation_gap", "gp_reconciliation_gap"]].abs().max().max()
        ),
        "elasticity": {
            row.customer_segment_name: {
                "estimate": round(float(row.elasticity), 4),
                "ci_low": round(float(row.ci_low), 4),
                "ci_high": round(float(row.ci_high), 4),
                "true": float(row.true_elasticity),
                "truth_in_ci": bool(row.truth_in_ci),
            }
            for row in outputs["elasticity_recovery"].itertuples(index=False)
        },
        "promo_uplift": {
            row.method: {
                "estimate": round(float(row.uplift), 4),
                "ci_low": round(float(row.ci_low), 4),
                "ci_high": round(float(row.ci_high), 4),
                "true": float(row.true_uplift),
                "truth_in_ci": bool(row.truth_in_ci),
            }
            for row in outputs["promo_did"].itertuples(index=False)
        },
        "recommended_gross_profit_change": round(
            float(recommendation["expected_gross_profit_change"].sum()), 2
        ),
        "recommended_gross_profit_change_pct": round(
            float(recommendation["expected_gross_profit_change"].sum())
            / float(recommendation["baseline_gross_profit"].sum()),
            6,
        ),
    }


def run_pipeline(
    paths: PipelinePaths | None = None, *, export_charts: bool = True
) -> dict[str, Any]:
    """Generate, validate, model, export, and document one deterministic demo run."""

    project_root = Path(__file__).resolve().parents[2]
    paths = paths or PipelinePaths.for_root(project_root)
    dataset = build_dataset(paths)
    bundle, config = dataset.bundle, dataset.config
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = _query_outputs(paths.database_path, config["opportunity_weights"])
    outputs.update(_pricing_outputs(paths.database_path, dataset.pricing_config))
    export_names = (
        "executive_kpis",
        "regional_opportunity",
        "competitor_momentum",
        "profitability_summary",
        "market_share_trend",
        "price_waterfall",
        "discount_policy_flags",
        "pvm_bridge",
        "elasticity_recovery",
        "promo_did",
        "price_recommendation",
        "price_recommendation_by_region",
    )
    for name in export_names:
        _export_csv(outputs[name], paths.output_dir / f"{name}.csv")
    export_powerbi_star_schema(bundle, paths.powerbi_dir)
    if export_charts:
        _write_charts(outputs, paths.output_dir, dataset.pricing_config)

    kpis = outputs["executive_kpis"].iloc[0]
    concentration = query_dataframe(
        paths.database_path, "SELECT AVG(hhi) AS average_hhi FROM vw_regional_concentration"
    )
    metadata: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "synthetic_data_only": True,
        "seed": dataset.generator_config.seed,
        "months": len(bundle["dim_date"]),
        "regions": len(bundle["dim_region"]),
        "companies": len(bundle["dim_company"]),
        "products": len(bundle["dim_product"]),
        "customer_segments": len(bundle["dim_customer_segment"]),
        "fact_row_count": len(bundle["fact_sales"]),
        "pricing_fact_row_count": len(bundle["fact_pricing"]),
        "dataset_fingerprint": _fingerprint(bundle["fact_sales"]),
        "pricing_dataset_fingerprint": _fingerprint(bundle["fact_pricing"]),
        "sql_scripts": dataset.executed_scripts,
        "final_period_focus_share": round(float(kpis["focus_market_share"]), 6),
        "market_yoy_growth": round(float(kpis["market_yoy_growth"]), 6),
        "focus_yoy_growth": round(float(kpis["focus_yoy_growth"]), 6),
        "gross_margin_pct": round(float(kpis["gross_margin_pct"]), 6),
        "gross_margin_change_pp": round(float(kpis["gross_margin_change_pp"]), 6),
        "highest_opportunity_region": str(kpis["highest_opportunity_region"]),
        "average_hhi": round(float(concentration.iloc[0]["average_hhi"]), 6),
        "pricing": _pricing_headlines(outputs),
    }
    (paths.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    LOGGER.info("Pipeline complete: %s fact rows", metadata["fact_row_count"])
    return metadata


def main() -> None:
    """CLI entry point."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("choreographer").setLevel(logging.WARNING)
    logging.getLogger("kaleido").setLevel(logging.WARNING)
    run_pipeline()


if __name__ == "__main__":  # pragma: no cover
    main()
