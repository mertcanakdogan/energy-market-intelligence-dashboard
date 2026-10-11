"""Thin Streamlit adapters; analytical business logic remains in the package."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

import dashboard_style as style
from energy_market_intelligence.database import query_dataframe
from energy_market_intelligence.elasticity import estimate_segment_elasticities
from energy_market_intelligence.localization import (
    COLUMN_LABELS,
    format_number,
    format_pct,
    localize_frame,
)
from energy_market_intelligence.pipeline import PipelinePaths, build_dataset
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.promotion import estimate_promo_uplift, treated_control_trend
from energy_market_intelligence.visualization import turkish_axes

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "data" / "energy_market.duckdb"
CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"
DATABASE_ENV_VAR = "EMID_DATABASE_PATH"

ALLOWED_VIEWS = {
    "vw_company_monthly",
    "vw_competitor_momentum",
    "vw_discount_policy_flags",
    "vw_executive_kpis",
    "vw_growth_analysis",
    "vw_market_metrics",
    "vw_focus_profitability_monthly",
    "vw_price_waterfall",
    "vw_pricing_detail",
    "vw_pricing_regression_input",
    "vw_profitability_summary",
    "vw_pvm_bridge",
    "vw_pvm_bridge_summary",
    "vw_regional_company_ranking",
    "vw_regional_concentration",
    "vw_regional_opportunity_inputs",
    "vw_regional_share_change",
    "vw_revenue_bridge",
}


def configured_database_path() -> Path:
    """Database location: ``EMID_DATABASE_PATH`` if set, otherwise ``data/energy_market.duckdb``."""

    override = os.environ.get(DATABASE_ENV_VAR)
    return Path(override) if override else DATABASE_PATH


@st.cache_resource(
    show_spinner="Sentetik veri tabanı oluşturuluyor (yalnızca ilk açılışta, yaklaşık 30 sn)..."
)
def ensure_database() -> str:
    """Return the database path, generating the synthetic data first if it does not exist.

    Local use after running the pipeline is unchanged. On a fresh deployment (for example
    Streamlit Community Cloud) the deterministic dataset is built once at first start; if the
    repository directory is read-only the database is placed in the system temp directory.
    """

    primary = configured_database_path()
    if primary.exists():
        return str(primary)
    fallback = Path(tempfile.gettempdir()) / "energy_market_intelligence" / primary.name
    if fallback.exists():
        return str(fallback)
    paths = PipelinePaths.for_root(PROJECT_ROOT)
    last_error: OSError | None = None
    for candidate in (primary, fallback):
        try:
            build_dataset(replace(paths, database_path=candidate), write_raw=False)
        except OSError as error:
            candidate.unlink(missing_ok=True)
            last_error = error
            continue
        return str(candidate)
    raise RuntimeError(f"Could not create the analytical database: {last_error}")


@st.cache_data(show_spinner=False)
def load_view(view_name: str) -> pd.DataFrame:
    """Load one allow-listed SQL view from the read-only local database."""

    if view_name not in ALLOWED_VIEWS:
        raise ValueError(f"Unknown analytical view: {view_name}")
    return query_dataframe(Path(ensure_database()), f"SELECT * FROM {view_name}")


@st.cache_data(show_spinner=False)
def load_config() -> dict:
    """Load public-demo configuration."""

    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_pricing_config() -> PricingConfig:
    """Typed view of the ``pricing`` configuration section (including the ground truth)."""

    return PricingConfig.from_mapping(load_config()["pricing"])


@st.cache_data(show_spinner="Fiyat esneklikleri tahmin ediliyor...")
def load_elasticities() -> pd.DataFrame:
    """Own-price elasticity by customer segment with the known true values attached."""

    return estimate_segment_elasticities(
        load_view("vw_pricing_regression_input"), load_pricing_config().true_elasticities
    )


@st.cache_data(show_spinner="Kampanya etkisi tahmin ediliyor...")
def load_promotion_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    """DiD estimates and the treated-vs-control volume index."""

    frame = load_view("vw_pricing_regression_input")
    estimates = estimate_promo_uplift(frame, load_pricing_config().promotion.true_volume_uplift)
    return estimates, treated_control_trend(frame)


class PageSpec(NamedTuple):
    """One page of the app: its sidebar section and label, the H1 question and the URL slug."""

    section: str  # sidebar section; the empty string is the headerless first group
    path: str
    title: str  # short noun used in the sidebar
    question: str  # H1 of the page ("" for the landing page, which leads with its thesis)
    url_path: str


PRICING = "Fiyatlama"
MARKET = "Pazar"
PAGE_SPECS = (
    PageSpec("", "views/home.py", "Genel bakış", "", "genel-bakis"),
    PageSpec(
        PRICING, "views/price_waterfall.py", "Fiyat kaçağı", "Fiyat nerede kaçıyor?", "fiyat-kacagi"
    ),
    PageSpec(PRICING, "views/pvm_bridge.py", "Ciro köprüsü", "Ciro neden değişti?", "ciro-koprusu"),
    PageSpec(
        PRICING,
        "views/elasticity.py",
        "Fiyat duyarlılığı",
        "Müşteri fiyata ne kadar duyarlı?",
        "fiyat-duyarliligi",
    ),
    PageSpec(
        PRICING,
        "views/promotion_impact.py",
        "Kampanya etkisi",
        "Kampanya gerçekten işe yaradı mı?",
        "kampanya-etkisi",
    ),
    PageSpec(
        PRICING,
        "views/price_recommendation.py",
        "Fiyat önerisi",
        "Hangi fiyat adımı değer?",
        "fiyat-onerisi",
    ),
    PageSpec(
        PRICING, "views/scenario_analysis.py", "Senaryo", "Fiyatı değiştirirsem ne olur?", "senaryo"
    ),
    PageSpec(
        MARKET,
        "views/executive_summary.py",
        "Yönetici özeti",
        "Pazarda ve şirkette ne değişti?",
        "yonetici-ozeti",
    ),
    PageSpec(
        MARKET,
        "views/market_performance.py",
        "Pazar performansı",
        "Pazar nerede büyüyor?",
        "pazar-performansi",
    ),
    PageSpec(
        MARKET,
        "views/competitive_intelligence.py",
        "Rekabet analizi",
        "Rakipler pay kazanıyor mu?",
        "rekabet-analizi",
    ),
    PageSpec(
        MARKET, "views/profitability.py", "Kârlılık", "Hacim kâr da getiriyor mu?", "karlilik"
    ),
    PageSpec(
        MARKET,
        "views/regional_opportunity.py",
        "Bölgesel fırsat",
        "Önce hangi bölgeye gidilmeli?",
        "bolgesel-firsat",
    ),
)


def page_spec(path: str) -> PageSpec:
    """The navigation entry of a page file such as ``views/price_waterfall.py``."""

    return next(spec for spec in PAGE_SPECS if spec.path == path)


def page_intro(path: str, what: str) -> None:
    """H1 question of the page and the plain-language "Bu sayfa ne gösteriyor?" line."""

    st.title(page_spec(path).question)
    style.intro("Bu sayfa ne gösteriyor?", what)


def takeaway(text: str) -> None:
    """Data-driven "Ne anlama geliyor?" callout, computed from the numbers on the page."""

    style.callout("takeaway", "Ne anlama geliyor?", text)


def note(text: str, label: str = "Not") -> None:
    """Neutral caveat or method note (grey rule)."""

    style.callout("note", label, text)


def breach(text: str, label: str = "Politika aşımı") -> None:
    """Policy breach or leakage finding (red rule, only for real breaches)."""

    style.callout("breach", label, text)


def positive(text: str, label: str = "Doğrulama") -> None:
    """Positive outcome (green rule)."""

    style.callout("gain", label, text)


def show_chart(figure: go.Figure, *, alt: str | None = None) -> None:
    """Render a Plotly figure with the shared template (Streamlit's own chart theme is off).

    The title is shown as a regular heading above the chart so that it wraps on narrow screens;
    the PNG exports keep the title inside the figure.
    """

    # Backgrounds are set on the figure itself: the frontend would otherwise fill the plot area
    # with its secondary background colour instead of the template's transparent one.
    figure = turkish_axes(go.Figure(figure))
    figure.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    title = figure.layout.title.text
    if title:
        plain = re.sub(r"<[^>]+>", " ", title)
        style.chart_title(plain)
        top = figure.layout.margin.t
        figure.update_layout(title=None, margin={"t": 44 if top is None else max(top - 40, 30)})
        alt = alt or plain
    st.plotly_chart(
        figure,
        theme=None,
        width="stretch",
        alt=alt,
        config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )


def _table_rule(column: str, fractions: set[str]) -> tuple[float, int, bool, str | None]:
    """Display scale, decimals, percent flag and unit suffix replacement for one numeric column."""

    label = COLUMN_LABELS.get(column, column)
    if column in fractions:
        return 1.0, 2, True, None
    if label.endswith("(TL)"):
        return 1e6, 2, False, "(mn TL)"
    if label.endswith("(MWh)"):
        return 1e3, 1, False, "(GWh)"
    if label.endswith("(TL/MWh)"):
        return 1.0, 0, False, None
    if column == "hhi":
        return 1.0, 3, False, None
    return 1.0, 2, False, None


def turkish_formatter(decimals: int, *, percent: bool = False) -> Callable[[object], str]:
    """Cell formatter with Turkish separators (``1.234,56``, ``%9,28``); blanks become a dash."""

    def render(value: object) -> str:
        if value is None or pd.isna(value):
            return "–"
        if percent:
            return format_pct(float(value), decimals)
        return format_number(float(value), decimals)

    return render


def show_dataframe(frame: pd.DataFrame, formats: dict[str, Callable[[object], str]]) -> None:
    """Render a table whose numbers read the Turkish way whatever the browser locale is.

    The Styler only changes the displayed text, so column sorting still uses the raw values.
    """

    st.dataframe(frame.style.format(formats), hide_index=True, width="stretch")


def show_table(frame: pd.DataFrame, *, fractions: set[str] | frozenset[str] = frozenset()) -> None:
    """Show a table with Turkish headers, translated codes and readable units.

    TL amounts are shown in million TL and MWh volumes in GWh. Columns named in ``fractions``
    hold shares between 0 and 1 and are shown as percentages.
    """

    display = frame.copy()
    formats = {}
    rename = {}
    for column in frame.columns:
        if not pd.api.types.is_numeric_dtype(display[column]) or pd.api.types.is_bool_dtype(
            display[column]
        ):
            continue
        if column in {"month_id", "n_obs", "momentum_rank", "company_rank", "opportunity_rank"}:
            continue
        scale, decimals, percent, unit = _table_rule(column, set(fractions))
        display[column] = display[column] / scale
        label = COLUMN_LABELS.get(column, column)
        if unit:
            label = label.rsplit("(", 1)[0] + unit
        rename[column] = label
        formats[label] = turkish_formatter(decimals, percent=percent)
    localized = localize_frame(display.rename(columns=rename).rename(columns=COLUMN_LABELS))
    show_dataframe(localized, formats)


def percent_slider(
    label: str,
    low: float,
    high: float,
    value: float,
    *,
    step: float = 0.5,
    signed: bool = True,
    sidebar: bool = False,
    help: str | None = None,
) -> float:
    """Slider over percentage points whose labels read the Turkish way (``+%2,5``)."""

    count = round((high - low) / step)
    options = [round(low + i * step, 4) for i in range(count + 1)]
    start = min(options, key=lambda option: abs(option - value))
    host = st.sidebar if sidebar else st
    return host.select_slider(
        label,
        options=options,
        value=start,
        format_func=lambda option: format_pct(option / 100, 1, signed=signed and option != 0),
        help=help,
    )


def select_regions(frame: pd.DataFrame, *, key: str) -> list[str]:
    """Provide a reusable multi-region sidebar filter."""

    options = sorted(frame["region_name"].dropna().unique().tolist())
    return st.sidebar.multiselect("Bölgeler", options, default=options, key=key)
