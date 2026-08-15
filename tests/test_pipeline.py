from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb

from energy_market_intelligence.pipeline import PipelinePaths, run_pipeline


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
    }
    assert expected.issubset({path.name for path in paths.output_dir.iterdir()})
    assert metadata["fact_row_count"] == 36 * 18 * 7 * 4


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
