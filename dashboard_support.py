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
    "vw_northstar_profitability_monthly",
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


@st.cache_resource(show_spinner="Building the synthetic analytical database (first start only)...")
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


@st.cache_data(show_spinner="Estimating segment elasticities...")
def load_elasticities() -> pd.DataFrame:
    """Own-price elasticity by customer segment with the known true values attached."""

    return estimate_segment_elasticities(
        load_view("vw_pricing_regression_input"), load_pricing_config().true_elasticities
    )


@st.cache_data(show_spinner="Estimating promotion uplift...")
def load_promotion_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    """DiD estimates and the treated-vs-control volume index."""

    frame = load_view("vw_pricing_regression_input")
    estimates = estimate_promo_uplift(frame, load_pricing_config().promotion.true_volume_uplift)
    return estimates, treated_control_trend(frame)


def page_intro(title: str, description: str) -> None:
    """Render a consistent management-facing page heading."""

    st.title(title)
    st.caption(description)


def format_compact(value: float) -> str:
    """Format large values for KPI cards without hiding their scale."""

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.1f}K"
    return f"{value:,.1f}"


def select_regions(frame: pd.DataFrame, *, key: str) -> list[str]:
    """Provide a reusable multi-region sidebar filter."""

    options = sorted(frame["region_name"].dropna().unique().tolist())
    return st.sidebar.multiselect("Regions", options, default=options, key=key)
