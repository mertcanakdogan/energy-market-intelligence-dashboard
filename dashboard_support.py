"""Thin Streamlit adapters; analytical business logic remains in the package."""

from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from energy_market_intelligence.database import query_dataframe
from energy_market_intelligence.elasticity import estimate_segment_elasticities
from energy_market_intelligence.localization import COLUMN_LABELS, localize_frame
from energy_market_intelligence.pipeline import PipelinePaths, build_dataset
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.promotion import estimate_promo_uplift, treated_control_trend

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


# Navigation: (section, file, title, icon, url path). The first section has no header.
PAGE_SPECS = (
    ("", "views/home.py", "Genel Bakış", ":material/home:", "genel-bakis"),
    (
        "Fiyatlama / Pricing",
        "views/price_waterfall.py",
        "Fiyat Şelalesi",
        ":material/waterfall_chart:",
        "fiyat-selalesi",
    ),
    (
        "Fiyatlama / Pricing",
        "views/pvm_bridge.py",
        "Gelir Köprüsü (PVM)",
        ":material/swap_vert:",
        "gelir-koprusu",
    ),
    (
        "Fiyatlama / Pricing",
        "views/elasticity.py",
        "Fiyat Esnekliği",
        ":material/trending_down:",
        "fiyat-esnekligi",
    ),
    (
        "Fiyatlama / Pricing",
        "views/promotion_impact.py",
        "Kampanya Etkisi",
        ":material/campaign:",
        "kampanya-etkisi",
    ),
    (
        "Fiyatlama / Pricing",
        "views/price_recommendation.py",
        "Fiyat Önerisi",
        ":material/price_check:",
        "fiyat-onerisi",
    ),
    (
        "Fiyatlama / Pricing",
        "views/scenario_analysis.py",
        "Senaryo Analizi",
        ":material/tune:",
        "senaryo-analizi",
    ),
    (
        "Pazar / Market",
        "views/executive_summary.py",
        "Yönetici Özeti",
        ":material/dashboard:",
        "yonetici-ozeti",
    ),
    (
        "Pazar / Market",
        "views/market_performance.py",
        "Pazar Performansı",
        ":material/show_chart:",
        "pazar-performansi",
    ),
    (
        "Pazar / Market",
        "views/competitive_intelligence.py",
        "Rekabet Analizi",
        ":material/groups:",
        "rekabet-analizi",
    ),
    (
        "Pazar / Market",
        "views/profitability.py",
        "Kârlılık",
        ":material/payments:",
        "karlilik",
    ),
    (
        "Pazar / Market",
        "views/regional_opportunity.py",
        "Bölgesel Fırsat",
        ":material/map:",
        "bolgesel-firsat",
    ),
)


def page_intro(title: str, what: str) -> None:
    """Page heading with the plain-language "Bu sayfa ne gösteriyor?" note."""

    st.title(title)
    st.info(f"**Bu sayfa ne gösteriyor?** {what}", icon=":material/help:")


def takeaway(text: str) -> None:
    """Data-driven "Ne anlama geliyor?" box, computed from the numbers on the page."""

    st.success(f"**Ne anlama geliyor?** {text}", icon=":material/lightbulb:")


def _table_rule(column: str, fractions: set[str]) -> tuple[float, str, str | None]:
    """Display scale, number format and unit suffix replacement for one numeric column."""

    label = COLUMN_LABELS.get(column, column)
    if column in fractions:
        return 1.0, "percent", None
    if label.endswith("(TL)"):
        return 1e6, "%.2f", "(mn TL)"
    if label.endswith("(MWh)"):
        return 1e3, "%.1f", "(GWh)"
    if label.endswith("(TL/MWh)"):
        return 1.0, "%.0f", None
    if label.endswith("(puan)"):
        return 1.0, "%.2f", None
    if column == "hhi":
        return 1.0, "%.3f", None
    return 1.0, "%.2f", None


def show_table(frame: pd.DataFrame, *, fractions: set[str] | frozenset[str] = frozenset()) -> None:
    """Show a table with Turkish headers, translated codes and readable units.

    TL amounts are shown in million TL and MWh volumes in GWh. Columns named in ``fractions``
    hold shares between 0 and 1 and are shown as percentages.
    """

    display = frame.copy()
    config = {}
    rename = {}
    for column in frame.columns:
        if not pd.api.types.is_numeric_dtype(display[column]) or pd.api.types.is_bool_dtype(
            display[column]
        ):
            continue
        if column in {"month_id", "n_obs", "momentum_rank", "company_rank", "opportunity_rank"}:
            continue
        scale, number_format, unit = _table_rule(column, set(fractions))
        display[column] = display[column] / scale
        label = COLUMN_LABELS.get(column, column)
        if unit:
            label = label.rsplit("(", 1)[0] + unit
        rename[column] = label
        config[label] = st.column_config.NumberColumn(label, format=number_format)
    localized = localize_frame(display.rename(columns=rename).rename(columns=COLUMN_LABELS))
    st.dataframe(localized, hide_index=True, width="stretch", column_config=config)


def select_regions(frame: pd.DataFrame, *, key: str) -> list[str]:
    """Provide a reusable multi-region sidebar filter."""

    options = sorted(frame["region_name"].dropna().unique().tolist())
    return st.sidebar.multiselect("Bölgeler", options, default=options, key=key)
