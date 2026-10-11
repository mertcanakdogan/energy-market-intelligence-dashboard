"""Thin Streamlit adapters; analytical business logic remains in the package."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable, Sequence
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
from energy_market_intelligence.pipeline import PipelinePaths, build_dataset, dataset_is_current
from energy_market_intelligence.pricing_config import PricingConfig
from energy_market_intelligence.promotion import estimate_promo_uplift, treated_control_trend
from energy_market_intelligence.visualization import format_axes

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "data" / "energy_market.duckdb"
CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"
DATABASE_ENV_VAR = "EMID_DATABASE_PATH"

ALLOWED_VIEWS = {
    "vw_discount_policy_flags",
    "vw_price_waterfall",
    "vw_pricing_regression_input",
    "vw_pvm_bridge",
    "vw_pvm_bridge_summary",
}


def configured_database_path() -> Path:
    """Database location: ``EMID_DATABASE_PATH`` if set, otherwise ``data/energy_market.duckdb``."""

    override = os.environ.get(DATABASE_ENV_VAR)
    return Path(override) if override else DATABASE_PATH


@st.cache_resource(
    show_spinner="Building the synthetic database (first start only, about 30 seconds)..."
)
def ensure_database() -> str:
    """Return the database path, generating the synthetic data first if needed.

    Local use after running the pipeline is unchanged. On a fresh deployment (for example
    Streamlit Community Cloud) the deterministic dataset is built once at first start; if the
    repository directory is read-only the database is placed in the system temp directory. A
    database built from an earlier dataset version is rebuilt, because a deployment keeps its
    files between commits. A path set through ``EMID_DATABASE_PATH`` is used as it is.
    """

    primary = configured_database_path()
    if os.environ.get(DATABASE_ENV_VAR) and primary.exists():
        return str(primary)
    fallback = Path(tempfile.gettempdir()) / "energy_market_intelligence" / primary.name
    for candidate in (primary, fallback):
        if dataset_is_current(candidate):
            return str(candidate)
    paths = PipelinePaths.for_root(PROJECT_ROOT)
    last_error: OSError | None = None
    for candidate in (primary, fallback):
        try:
            candidate.unlink(missing_ok=True)  # generated file from an earlier dataset version
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


@st.cache_data(show_spinner="Estimating price elasticities...")
def load_elasticities() -> pd.DataFrame:
    """Own-price elasticity by customer segment with the known true values attached."""

    return estimate_segment_elasticities(
        load_view("vw_pricing_regression_input"), load_pricing_config().true_elasticities
    )


@st.cache_data(show_spinner="Estimating the promotion effect...")
def load_promotion_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Difference-in-differences estimates and the treated-vs-control volume index."""

    frame = load_view("vw_pricing_regression_input")
    estimates = estimate_promo_uplift(frame, load_pricing_config().promotion.true_volume_uplift)
    return estimates, treated_control_trend(frame)


class PageSpec(NamedTuple):
    """One page of the app: its sidebar label, the H1 question and the URL slug."""

    path: str
    title: str  # short noun used in the sidebar
    question: str  # H1 of the page ("" for the landing page, which leads with its thesis)
    url_path: str


PAGE_SPECS = (
    PageSpec("views/home.py", "Overview", "", "overview"),
    PageSpec(
        "views/price_waterfall.py", "Price leakage", "Where does price leak?", "price-leakage"
    ),
    PageSpec("views/pvm_bridge.py", "Revenue bridge", "Why did revenue change?", "revenue-bridge"),
    PageSpec(
        "views/elasticity.py",
        "Price sensitivity",
        "How sensitive are customers to price?",
        "price-sensitivity",
    ),
    PageSpec(
        "views/promotion_impact.py",
        "Promotion impact",
        "Did the promotion really work?",
        "promotion-impact",
    ),
    PageSpec(
        "views/price_recommendation.py",
        "Price recommendation",
        "Which price step is worth taking?",
        "price-recommendation",
    ),
)


def page_spec(path: str) -> PageSpec:
    """The navigation entry of a page file such as ``views/price_waterfall.py``."""

    return next(spec for spec in PAGE_SPECS if spec.path == path)


def page_intro(path: str, what: str) -> None:
    """H1 question of the page and the plain-language "What this page shows" line."""

    st.title(page_spec(path).question)
    style.intro("What this page shows", what)


def takeaway(text: str | Sequence[tuple[str, str]]) -> None:
    """Data-driven "What it means" callout, computed from the numbers on the page.

    ``text`` is one sentence or a sequence of ``(lead, sentence)`` lines.
    """

    style.callout("takeaway", "What it means", text)


def note(text: str, label: str = "Note") -> None:
    """Neutral caveat or method note (grey rule)."""

    style.callout("note", label, text)


def breach(text: str, label: str = "Policy breach") -> None:
    """Policy breach or leakage finding (red rule, only for real breaches)."""

    style.callout("breach", label, text)


def positive(text: str, label: str = "Check") -> None:
    """Positive outcome (green rule)."""

    style.callout("gain", label, text)


def show_chart(figure: go.Figure, *, alt: str | None = None) -> None:
    """Render a Plotly figure with the shared template (Streamlit's own chart theme is off).

    The title is shown as a regular heading above the chart so that it wraps on narrow screens;
    the PNG exports keep the title inside the figure.
    """

    # Backgrounds are set on the figure itself: the frontend would otherwise fill the plot area
    # with its secondary background colour instead of the template's transparent one.
    figure = format_axes(go.Figure(figure))
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
    if label.endswith("(TRY)"):
        return 1e6, 2, False, "(TRY m)"
    if label.endswith("(MWh)"):
        return 1e3, 1, False, "(GWh)"
    if label.endswith("(TRY/MWh)"):
        return 1.0, 0, False, None
    if column == "hhi":
        return 1.0, 3, False, None
    return 1.0, 2, False, None


def cell_formatter(decimals: int, *, percent: bool = False) -> Callable[[object], str]:
    """Cell formatter with English separators (``1,234.56``, ``9.28%``); blanks become a dash."""

    def render(value: object) -> str:
        if value is None or pd.isna(value):
            return "–"
        if percent:
            return format_pct(float(value), decimals)
        return format_number(float(value), decimals)

    return render


def show_dataframe(frame: pd.DataFrame, formats: dict[str, Callable[[object], str]]) -> None:
    """Render a table whose numbers use English formats whatever the browser locale is.

    The Styler only changes the displayed text, so column sorting still uses the raw values.
    """

    st.dataframe(frame.style.format(formats), hide_index=True, width="stretch")


def show_table(frame: pd.DataFrame, *, fractions: set[str] | frozenset[str] = frozenset()) -> None:
    """Show a table with readable headers, translated codes and readable units.

    TRY amounts are shown in TRY million and MWh volumes in GWh. Columns named in ``fractions``
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
        formats[label] = cell_formatter(decimals, percent=percent)
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
    """Slider over percentage points whose labels use English formats (``+2.5%``)."""

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
    """Sidebar filter over the provinces (stored in the ``region_name`` column)."""

    options = sorted(frame["region_name"].dropna().unique().tolist())
    return st.sidebar.multiselect("Provinces", options, default=options, key=key)
