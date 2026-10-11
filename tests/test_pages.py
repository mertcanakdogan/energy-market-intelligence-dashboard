"""Smoke tests: every Streamlit page runs against a freshly built database without errors."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import dashboard_support

TIMEOUT = 180
PAGES = [
    "app.py",
    "pages/01_price_waterfall.py",
    "pages/02_pvm_bridge.py",
    "pages/03_elasticity.py",
    "pages/04_promotion_impact.py",
    "pages/05_price_recommendation.py",
    "pages/scenario_analysis.py",
    "pages/executive_summary.py",
    "pages/market_performance.py",
    "pages/competitive_intelligence.py",
    "pages/profitability.py",
    "pages/regional_opportunity.py",
]


@pytest.fixture(scope="module", autouse=True)
def database_env(analytics_db: Path):
    """Point the app at the shared test database and reset Streamlit caches around the module."""

    mp = pytest.MonkeyPatch()
    mp.setenv(dashboard_support.DATABASE_ENV_VAR, str(analytics_db))
    dashboard_support.ensure_database.clear()
    dashboard_support.load_view.clear()
    yield
    dashboard_support.ensure_database.clear()
    dashboard_support.load_view.clear()
    mp.undo()


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_without_exception(project_root: Path, page: str) -> None:
    app = AppTest.from_file(str(project_root / page), default_timeout=TIMEOUT).run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.title or app.subheader or app.markdown


def test_landing_page_leads_with_the_pricing_story(project_root: Path) -> None:
    app = AppTest.from_file(str(project_root / "app.py"), default_timeout=TIMEOUT).run()
    assert "Pricing" in app.title[0].value
    labels = [metric.label for metric in app.metric]
    assert "Price realization" in labels


def test_scenario_page_supports_manual_override(project_root: Path) -> None:
    app = AppTest.from_file(
        str(project_root / "pages/scenario_analysis.py"), default_timeout=TIMEOUT
    ).run()
    assert not app.exception
    app.radio[0].set_value("Manual override").run()
    assert not app.exception
    assert any("user-defined" in slider.label for slider in app.slider)


def test_scenario_page_uses_estimated_elasticity_by_default(project_root: Path) -> None:
    app = AppTest.from_file(
        str(project_root / "pages/scenario_analysis.py"), default_timeout=TIMEOUT
    ).run()
    price_slider = next(slider for slider in app.slider if slider.label == "Price change %")
    price_slider.set_value(5.0).run()
    assert not app.exception
    captions = " ".join(item.value for item in app.caption)
    assert "implies a volume response of -" in captions


def test_missing_database_is_built_on_first_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    target = tmp_path / "fresh" / "energy_market.duckdb"
    monkeypatch.setenv(dashboard_support.DATABASE_ENV_VAR, str(target))
    dashboard_support.ensure_database.clear()
    try:
        assert not target.exists()
        built = dashboard_support.ensure_database()
        assert Path(built) == target
        assert target.exists()
    finally:
        dashboard_support.ensure_database.clear()


def test_unknown_view_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown analytical view"):
        dashboard_support.load_view.__wrapped__("fact_pricing; DROP TABLE x")
