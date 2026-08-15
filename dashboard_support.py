"""Thin Streamlit adapters; analytical business logic remains in the package."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from energy_market_intelligence.database import query_dataframe

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "data" / "energy_market.duckdb"
CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"

ALLOWED_VIEWS = {
    "vw_company_monthly",
    "vw_competitor_momentum",
    "vw_executive_kpis",
    "vw_growth_analysis",
    "vw_market_metrics",
    "vw_northstar_profitability_monthly",
    "vw_profitability_summary",
    "vw_regional_company_ranking",
    "vw_regional_concentration",
    "vw_regional_opportunity_inputs",
    "vw_regional_share_change",
    "vw_revenue_bridge",
}


def require_database() -> None:
    """Stop a page with an actionable message when pipeline artifacts are absent."""

    if not DATABASE_PATH.exists():
        st.error("The local analytical database has not been generated yet.")
        st.code("python -m energy_market_intelligence.pipeline")
        st.stop()


@st.cache_data(show_spinner=False)
def load_view(view_name: str) -> pd.DataFrame:
    """Load one allow-listed SQL view from the read-only local database."""

    if view_name not in ALLOWED_VIEWS:
        raise ValueError(f"Unknown analytical view: {view_name}")
    require_database()
    return query_dataframe(DATABASE_PATH, f"SELECT * FROM {view_name}")


@st.cache_data(show_spinner=False)
def load_config() -> dict:
    """Load public-demo configuration."""

    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


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
