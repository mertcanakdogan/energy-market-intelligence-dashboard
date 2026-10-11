"""Smoke tests: every Streamlit page runs against a freshly built database without errors."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import dashboard_support

TIMEOUT = 180
PAGES = [spec.path for spec in dashboard_support.PAGE_SPECS if not spec.path.endswith("home.py")]


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
    assert app.title or app.header or app.markdown
    assert not app.subheader, "section headings are h2 (st.header) right after the h1"


def test_landing_page_leads_with_the_thesis_and_the_bill(project_root: Path) -> None:
    app = AppTest.from_file(str(project_root / "app.py"), default_timeout=TIMEOUT).run()
    assert not app.exception, [item.value for item in app.exception]
    assert re.fullmatch(
        r"Of every TRY\xa0100 at list price, the company keeps TRY\xa0\d+\.\d and "
        r":red\[TRY\xa0\d+\.\d\] leaks away\.",
        app.title[0].value,
    )
    text = " ".join(item.value for item in app.markdown)
    assert "PRICE BREAKDOWN" in text
    assert "Leakage rate:" in text
    assert "fictional" in text and "synthetic" in text and "constant 2025 prices" in text
    assert "Pocket price" in text
    assert "day-ahead market price" in text
    headers = [item.value for item in app.header]
    assert "Why can you trust the model?" in headers
    assert not app.subheader, "sections are h2 straight after the h1; no h3 jump"
    # The generic metric-card row is gone; every number on the page is part of the story.
    assert not app.metric


def test_landing_page_compares_segments_instead_of_offering_a_scope_control(
    project_root: Path,
) -> None:
    app = AppTest.from_file(str(project_root / "app.py"), default_timeout=TIMEOUT).run()
    assert not app.exception, [item.value for item in app.exception]
    assert not app.get("button_group"), "the scope control lives on the price leakage page only"
    text = " ".join(item.value for item in app.markdown)
    assert "Whole portfolio · TRY/MWh" in text
    assert "Where leakage differs" in text
    for segment in ("Residential", "Commercial (SME)", "Industrial"):
        assert segment in text
    assert "What it means" in text and "Finding" in text and "Action" in text
    assert "The same test works for the promotion" in text
    assert "Built by" in text and "Synthetic data and a fictional company" in " ".join(
        item.value for item in app.caption
    )
    assert "redesigned" not in text
    assert [link.label for link in app.get("page_link")][:1] == ["What should the company do?"]


def test_navigation_is_one_flat_list_of_six_pricing_pages(project_root: Path) -> None:
    specs = dashboard_support.PAGE_SPECS
    assert [spec.title for spec in specs] == [
        "Overview",
        "Price leakage",
        "Revenue bridge",
        "Price sensitivity",
        "Promotion impact",
        "Price recommendation",
    ]
    assert [spec.url_path for spec in specs] == [
        "overview",
        "price-leakage",
        "revenue-bridge",
        "price-sensitivity",
        "promotion-impact",
        "price-recommendation",
    ]
    assert specs[0].path == "views/home.py" and specs[0].question == ""
    assert not hasattr(specs[0], "section")
    for spec in specs:
        assert (project_root / spec.path).is_file()
        if spec.question:
            assert spec.question.endswith("?"), spec.question
    assert sorted(path.name for path in (project_root / "views").glob("*.py")) == sorted(
        Path(spec.path).name for spec in specs
    ), "every view file is a page and every page has a view file"
    assert not (project_root / "pages").exists(), "legacy pages/ directory must not return"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_asks_a_question_explains_itself_and_gives_a_takeaway(
    project_root: Path, page: str
) -> None:
    app = AppTest.from_file(str(project_root / page), default_timeout=TIMEOUT).run()
    assert not app.exception
    assert app.title[0].value == dashboard_support.page_spec(page).question
    text = " ".join(item.value for item in app.markdown)
    assert "What this page shows" in text
    assert "What it means" in text


def test_price_leakage_page_filters_by_province(project_root: Path) -> None:
    app = AppTest.from_file(
        str(project_root / "views/price_waterfall.py"), default_timeout=TIMEOUT
    ).run()
    province = app.sidebar.selectbox[0]
    assert province.label == "Province"
    assert province.value == "All provinces"
    assert "Istanbul" in province.options
    portfolio_price = app.metric[1].value
    province.set_value("Istanbul").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.metric[1].value != portfolio_price


def test_price_recommendation_page_reacts_to_the_limits(project_root: Path) -> None:
    app = AppTest.from_file(
        str(project_root / "views/price_recommendation.py"), default_timeout=TIMEOUT
    ).run()
    step = next(slider for slider in app.select_slider if slider.label == "Largest price step")
    step.set_value(2.0).run()
    assert not app.exception, [item.value for item in app.exception]
    text = " ".join(item.value for item in app.markdown)
    assert "What it means" in text and "TRY" in text


def test_tables_show_try_millions_and_gigawatt_hours() -> None:
    assert dashboard_support._table_rule("gross_profit", set()) == (1e6, 2, False, "(TRY m)")
    assert dashboard_support._table_rule("volume_mwh", set()) == (1e3, 1, False, "(GWh)")
    assert dashboard_support._table_rule("list_price", set()) == (1.0, 0, False, None)


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


def test_database_from_an_earlier_dataset_version_is_rebuilt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from energy_market_intelligence.pipeline import dataset_is_current, dataset_stamp_path

    stale = tmp_path / "energy_market.duckdb"
    stale.write_bytes(b"left over from an earlier deployment")
    dataset_stamp_path(stale).write_text("1.0.0", encoding="utf-8")
    monkeypatch.delenv(dashboard_support.DATABASE_ENV_VAR, raising=False)
    monkeypatch.setattr(dashboard_support, "DATABASE_PATH", stale)
    dashboard_support.ensure_database.clear()
    try:
        assert not dataset_is_current(stale)
        assert Path(dashboard_support.ensure_database()) == stale
        assert dataset_is_current(stale)
    finally:
        dashboard_support.ensure_database.clear()


def test_unknown_view_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown analytical view"):
        dashboard_support.load_view.__wrapped__("fact_pricing; DROP TABLE x")
