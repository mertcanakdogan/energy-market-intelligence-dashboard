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
    assert app.title or app.subheader or app.markdown


def test_landing_page_leads_with_the_thesis_and_the_bill(project_root: Path) -> None:
    app = AppTest.from_file(str(project_root / "app.py"), default_timeout=TIMEOUT).run()
    assert not app.exception, [item.value for item in app.exception]
    assert re.fullmatch(
        r"Liste fiyatının :red\[%\d+,\d'\w+\] müşteriye ulaşmadan kayboluyor\.", app.title[0].value
    )
    text = " ".join(item.value for item in app.markdown)
    assert "FATURA DÖKÜMÜ" in text
    assert "Kaçak oranı:" in text
    assert "kurgusal" in text and "sentetik" in text and "sabit 2025 fiyatlarıyla" in text
    assert "Net (cebe kalan) fiyat" in text
    subheaders = [item.value for item in app.subheader]
    assert "Modele neden güvenebilirsiniz?" in subheaders
    # The generic metric-card row is gone; every number on the page is part of the story.
    assert not app.metric


def test_landing_page_bill_follows_the_segment_selector(project_root: Path) -> None:
    app = AppTest.from_file(str(project_root / "app.py"), default_timeout=TIMEOUT).run()
    app.get("button_group")[0].set_value("Sanayi").run()
    assert not app.exception, [item.value for item in app.exception]
    text = " ".join(item.value for item in app.markdown)
    assert "Sanayi · TL/MWh" in text


def test_navigation_has_two_named_sections_in_order(project_root: Path) -> None:
    specs = dashboard_support.PAGE_SPECS
    sections = list(dict.fromkeys(spec.section for spec in specs))
    assert sections == ["", "Fiyatlama", "Pazar"]
    assert specs[0].path == "views/home.py"
    assert len({spec.title for spec in specs}) == len(specs)
    assert len({spec.url_path for spec in specs}) == len(specs)
    for spec in specs:
        assert (project_root / spec.path).is_file()
        assert spec.title and "_" not in spec.title and not spec.title.endswith(".py")
        if spec.section:
            assert spec.question.endswith("?"), spec.question
    assert not (project_root / "pages").exists(), "legacy pages/ directory must not return"


@pytest.mark.parametrize("page", PAGES)
def test_every_page_asks_a_question_explains_itself_and_gives_a_takeaway(
    project_root: Path, page: str
) -> None:
    app = AppTest.from_file(str(project_root / page), default_timeout=TIMEOUT).run()
    assert not app.exception
    assert app.title[0].value == dashboard_support.page_spec(page).question
    text = " ".join(item.value for item in app.markdown)
    assert "Bu sayfa ne gösteriyor?" in text
    if not page.endswith("scenario_analysis.py"):
        assert "Ne anlama geliyor?" in text


def test_scenario_page_supports_manual_override(project_root: Path) -> None:
    app = AppTest.from_file(
        str(project_root / "views/scenario_analysis.py"), default_timeout=TIMEOUT
    ).run()
    assert not app.exception
    app.radio[0].set_value("Elle girilen").run()
    assert not app.exception
    assert any("elle girilen" in slider.label for slider in app.slider)


def test_scenario_page_uses_estimated_elasticity_by_default(project_root: Path) -> None:
    app = AppTest.from_file(
        str(project_root / "views/scenario_analysis.py"), default_timeout=TIMEOUT
    ).run()
    price_slider = next(slider for slider in app.slider if slider.label == "Fiyat değişimi (%)")
    price_slider.set_value(5.0).run()
    assert not app.exception
    captions = " ".join(item.value for item in app.caption)
    assert "hacim tepkisi -" in captions
    text = " ".join(item.value for item in app.markdown)
    assert "Ne anlama geliyor?" in text


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
