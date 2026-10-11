from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb

from energy_market_intelligence.pipeline import PipelinePaths, build_dataset, run_pipeline


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pipeline_creates_expected_artifacts(tmp_path: Path, project_root: Path) -> None:
    paths = PipelinePaths.for_root(project_root, runtime_root=tmp_path)
    metadata = run_pipeline(paths=paths)
    expected = {
        "executive_kpis.csv",
        "regional_opportunity.csv",
        "competitor_momentum.csv",
        "profitability_summary.csv",
        "market_share_trend.csv",
        "run_metadata.json",
        "market_share_trend.png",
        "regional_opportunity_matrix.png",
        "competitor_share_change.png",
        "gross_margin_trend.png",
        "profit_bridge.png",
        "price_waterfall.csv",
        "price_waterfall.png",
        "discount_policy_flags.csv",
        "pvm_bridge.csv",
        "pvm_bridge.png",
        "elasticity_recovery.csv",
        "elasticity_recovery.png",
        "promo_did.csv",
        "promo_did.png",
        "price_recommendation.csv",
        "price_recommendation.png",
        "price_recommendation_by_region.csv",
    }
    assert expected.issubset({path.name for path in paths.output_dir.iterdir()})
    assert metadata["fact_row_count"] == 36 * 18 * 7 * 4
    assert metadata["pricing_fact_row_count"] == 36 * 18 * 4 * 3
    assert "09_pvm_bridge.sql" in metadata["sql_scripts"]
    powerbi_files = {path.name for path in paths.powerbi_dir.iterdir()}
    assert {"fact_pricing.csv", "dim_customer_segment.csv", "dim_date.csv"}.issubset(powerbi_files)


def test_pipeline_is_deterministic_and_idempotent(tmp_path: Path, project_root: Path) -> None:
    paths = PipelinePaths.for_root(project_root, runtime_root=tmp_path)
    first = run_pipeline(paths=paths, export_charts=False)
    first_hash = file_hash(paths.output_dir / "regional_opportunity.csv")
    second = run_pipeline(paths=paths, export_charts=False)
    assert first_hash == file_hash(paths.output_dir / "regional_opportunity.csv")
    assert first["dataset_fingerprint"] == second["dataset_fingerprint"]


def test_pipeline_metadata_is_machine_readable(tmp_path: Path, project_root: Path) -> None:
    paths = PipelinePaths.for_root(project_root, runtime_root=tmp_path)
    run_pipeline(paths=paths, export_charts=False)
    metadata = json.loads((paths.output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["synthetic_data_only"] is True
    assert metadata["months"] == 36
    assert metadata["regions"] == 18
    assert "generated_at_utc" in metadata


def test_pipeline_database_rebuild_has_no_duplicate_fact_rows(
    tmp_path: Path, project_root: Path
) -> None:
    paths = PipelinePaths.for_root(project_root, runtime_root=tmp_path)
    run_pipeline(paths=paths, export_charts=False)
    run_pipeline(paths=paths, export_charts=False)
    with duckdb.connect(str(paths.database_path), read_only=True) as connection:
        count, distinct_count = connection.execute(
            "SELECT COUNT(*), "
            "COUNT(DISTINCT (month_id, region_id, company_id, product_id)) "
            "FROM fact_sales"
        ).fetchone()
    assert count == distinct_count == 36 * 18 * 7 * 4


def test_pipeline_pricing_metadata_matches_ground_truth(tmp_path: Path, project_root: Path) -> None:
    paths = PipelinePaths.for_root(project_root, runtime_root=tmp_path)
    run_pipeline(paths=paths, export_charts=False)
    metadata = json.loads((paths.output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    pricing = metadata["pricing"]
    assert pricing["pvm_max_abs_reconciliation_gap"] < 1e-6
    assert all(item["truth_in_ci"] for item in pricing["elasticity"].values())
    assert pricing["promo_uplift"]["price_adjusted"]["truth_in_ci"]
    assert 0.7 < pricing["price_realization_pct"] < 1
    assert pricing["recommended_gross_profit_change"] > 0
    assert set(pricing["breaching_regions"]) == {
        "Ege Kuzey",
        "Batı Akdeniz",
        "Doğu Akdeniz",
        "Doğu Anadolu Kuzey",
    }


def test_pricing_outputs_are_deterministic(tmp_path: Path, project_root: Path) -> None:
    paths = PipelinePaths.for_root(project_root, runtime_root=tmp_path)
    run_pipeline(paths=paths, export_charts=False)
    first = {
        name: file_hash(paths.output_dir / name)
        for name in ("elasticity_recovery.csv", "promo_did.csv", "price_recommendation.csv")
    }
    run_pipeline(paths=paths, export_charts=False)
    for name, digest in first.items():
        assert digest == file_hash(paths.output_dir / name)


def test_build_dataset_creates_database_without_analysis_outputs(
    tmp_path: Path, project_root: Path
) -> None:
    paths = PipelinePaths.for_root(project_root, runtime_root=tmp_path)
    dataset = build_dataset(paths, write_raw=False)
    assert paths.database_path.exists()
    assert not paths.output_dir.exists()
    assert not paths.raw_dir.exists()
    assert "fact_pricing" in dataset.bundle
