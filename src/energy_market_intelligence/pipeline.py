"""Reproducible end-to-end build for synthetic data, SQL models, and example outputs."""

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
from energy_market_intelligence.opportunity import calculate_opportunity_scores
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.pricing_data import generate_full_bundle
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
        )


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
            database_path, "SELECT * FROM vw_northstar_profitability_monthly ORDER BY date"
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


def _write_charts(outputs: dict[str, pd.DataFrame], directory: Path) -> None:
    figures = {
        "market_share_trend.png": market_share_trend_figure(outputs["market_share_trend"]),
        "regional_opportunity_matrix.png": opportunity_matrix_figure(
            outputs["regional_opportunity"]
        ),
        "competitor_share_change.png": competitor_change_figure(outputs["competitor_momentum"]),
        "gross_margin_trend.png": gross_margin_trend_figure(outputs["profitability_monthly"]),
        "profit_bridge.png": profit_bridge_figure(outputs["profit_bridge"]),
    }
    for filename, figure in figures.items():
        write_png(figure, directory / filename)


def run_pipeline(
    paths: PipelinePaths | None = None, *, export_charts: bool = True
) -> dict[str, Any]:
    """Generate, validate, model, export, and document one deterministic demo run."""

    project_root = Path(__file__).resolve().parents[2]
    paths = paths or PipelinePaths.for_root(project_root)
    config = _load_config(paths.config_path)
    project_config = config["project"]
    generator_config = GeneratorConfig(
        seed=int(project_config["random_seed"]),
        start_month=str(project_config["start_month"]),
        months=int(project_config["months"]),
    )
    LOGGER.info("Generating deterministic synthetic star-schema data")
    bundle = generate_full_bundle(generator_config, PricingConfig.from_mapping(config["pricing"]))
    validate_bundle(bundle, tolerance=float(config["validation"]["financial_tolerance"]))
    validate_pricing_bundle(bundle)
    _write_raw_tables(bundle, paths.raw_dir)
    executed_scripts = build_database(bundle, paths.database_path, paths.sql_dir)
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = _query_outputs(paths.database_path, config["opportunity_weights"])
    export_names = (
        "executive_kpis",
        "regional_opportunity",
        "competitor_momentum",
        "profitability_summary",
        "market_share_trend",
    )
    for name in export_names:
        _export_csv(outputs[name], paths.output_dir / f"{name}.csv")
    if export_charts:
        _write_charts(outputs, paths.output_dir)

    kpis = outputs["executive_kpis"].iloc[0]
    concentration = query_dataframe(
        paths.database_path, "SELECT AVG(hhi) AS average_hhi FROM vw_regional_concentration"
    )
    metadata: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "synthetic_data_only": True,
        "seed": generator_config.seed,
        "months": len(bundle["dim_date"]),
        "regions": len(bundle["dim_region"]),
        "companies": len(bundle["dim_company"]),
        "products": len(bundle["dim_product"]),
        "fact_row_count": len(bundle["fact_sales"]),
        "dataset_fingerprint": _fingerprint(bundle["fact_sales"]),
        "sql_scripts": executed_scripts,
        "final_period_northstar_share": round(float(kpis["northstar_market_share"]), 6),
        "market_yoy_growth": round(float(kpis["market_yoy_growth"]), 6),
        "northstar_yoy_growth": round(float(kpis["northstar_yoy_growth"]), 6),
        "gross_margin_pct": round(float(kpis["gross_margin_pct"]), 6),
        "gross_margin_change_pp": round(float(kpis["gross_margin_change_pp"]), 6),
        "highest_opportunity_region": str(kpis["highest_opportunity_region"]),
        "average_hhi": round(float(concentration.iloc[0]["average_hhi"]), 6),
    }
    (paths.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
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
