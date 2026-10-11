"""Display conventions shared by charts, the Streamlit app and the pipeline outputs.

Convention used throughout the project:

* Entity names in the data are English or Turkish place names and fictional (companies, products,
  customer segments and the 18 provinces that serve as sales areas).
* Enumerated codes produced by SQL or the estimators (for example ``Gaining`` or ``elastic``) are
  turned into readable labels here at display time.
* All money is in Turkish lira (TRY) at constant (real) 2025 prices. Numbers use English
  separators: ``,`` groups thousands and ``.`` marks decimals (``3,100 TRY/MWh``, ``85.2%``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import pandas as pd

CURRENCY = "TRY"
PRICE_BASIS = "constant 2025 prices"

# Display order of the customer segments (the order of ``pricing.segments`` in the config).
SEGMENT_ORDER = ("Residential", "Commercial (SME)", "Industrial")

MISSING = "–"


def format_number(value: float, decimals: int = 0, *, signed: bool = False) -> str:
    """Format ``value`` with English separators, e.g. ``1,234.5``."""

    if value is None or not math.isfinite(value):
        return MISSING
    value = round(float(value), decimals)
    if value == 0:
        value = 0.0
    text = f"{abs(value):,.{decimals}f}"
    if value < 0:
        return f"-{text}"
    return f"+{text}" if signed and value > 0 else text


def format_pct(fraction: float, decimals: int = 1, *, signed: bool = False) -> str:
    """Format a fraction as a percentage: ``0.852`` becomes ``85.2%``, ``0.043`` ``+4.3%``."""

    if fraction is None or not math.isfinite(fraction):
        return MISSING
    return f"{format_number(fraction * 100, decimals, signed=signed)}%"


def format_pp(value: float, decimals: int = 2) -> str:
    """Format a change in percentage points: ``+0.55 pp``."""

    return f"{format_number(value, decimals, signed=True)} pp"


def format_try(value: float, *, signed: bool = False) -> str:
    """Compact money amount: ``TRY 4.54bn``, ``TRY 21.4m``, ``TRY 128k`` or ``TRY 950``."""

    if value is None or not math.isfinite(value):
        return MISSING
    magnitude = abs(value)
    if magnitude >= 1e9:
        scaled, decimals, unit = value / 1e9, 2, "bn"
    elif magnitude >= 1e6:
        scaled = value / 1e6
        decimals, unit = (1 if abs(scaled) >= 10 else 2), "m"
    elif magnitude >= 1e3:
        scaled = value / 1e3
        decimals, unit = (0 if abs(scaled) >= 100 else 1), "k"
    else:
        scaled, decimals, unit = value, 0, ""
    text = format_number(scaled, decimals, signed=signed)
    sign = text[0] if text[0] in "+-" else ""
    return f"{sign}{CURRENCY} {text[len(sign) :]}{unit}"


def format_try_per_mwh(value: float, decimals: int = 0, *, signed: bool = False) -> str:
    """Unit price: ``3,100 TRY/MWh``."""

    return f"{format_number(value, decimals, signed=signed)} {CURRENCY}/MWh"


def format_volume(mwh: float, *, signed: bool = False) -> str:
    """Energy volume with an energy-natural unit: ``1.45 TWh``, ``820 GWh`` or ``950 MWh``."""

    if mwh is None or not math.isfinite(mwh):
        return MISSING
    magnitude = abs(mwh)
    if magnitude >= 1e6:
        return f"{format_number(mwh / 1e6, 2, signed=signed)} TWh"
    if magnitude >= 1e3:
        scaled = mwh / 1e3
        return f"{format_number(scaled, 0 if abs(scaled) >= 100 else 1, signed=signed)} GWh"
    return f"{format_number(mwh, 0, signed=signed)} MWh"


# ---------------------------------------------------------------------------------------------
# Labels for table columns and enumerated values
# ---------------------------------------------------------------------------------------------

COLUMN_LABELS: dict[str, str] = {
    "region_name": "Province",
    "product_name": "Product",
    "customer_segment_name": "Customer segment",
    "company_name": "Company",
    "product_segment": "Product family",
    "date": "Month",
    "month_id": "Month no.",
    "volume_mwh": "Volume (MWh)",
    "baseline_volume_mwh": "Current volume (MWh)",
    "list_price": "List price (TRY/MWh)",
    "pocket_price": "Pocket price (TRY/MWh)",
    "current_pocket_price": "Current pocket price (TRY/MWh)",
    "recommended_pocket_price": "Recommended pocket price (TRY/MWh)",
    "unit_variable_cost": "Unit cost (TRY/MWh)",
    "list_revenue": "Revenue at list price (TRY)",
    "pocket_revenue": "Pocket revenue (TRY)",
    "gross_profit": "Gross profit (TRY)",
    "revenue": "Revenue (TRY)",
    "on_invoice_discount_pct": "On-invoice discount (% of list price)",
    "policy_max_discount_pct": "Policy limit",
    "excess_discount_pp": "Excess over limit (pp)",
    "revenue_leakage_above_policy": "Discount above policy (TRY)",
    "exceeds_policy": "Above the limit?",
    "pocket_margin_pct": "Pocket margin",
    "current_margin_pct": "Current margin",
    "new_margin_pct": "New margin",
    "prior_volume": "Prior-year volume (MWh)",
    "current_volume": "Latest-year volume (MWh)",
    "prior_price": "Prior-year price (TRY/MWh)",
    "current_price": "Latest-year price (TRY/MWh)",
    "volume_effect": "Volume effect (TRY)",
    "mix_effect": "Mix effect (TRY)",
    "price_effect": "Price effect (TRY)",
    "total_revenue_change": "Revenue change (TRY)",
    "gp_cost_effect": "Cost effect (TRY)",
    "total_gp_change": "Gross profit change (TRY)",
    "reconciliation_gap": "Reconciliation gap (TRY)",
    "elasticity": "Elasticity",
    "std_error": "Standard error",
    "ci_low": "95% CI low",
    "ci_high": "95% CI high",
    "true_elasticity": "True elasticity",
    "abs_error": "Absolute error",
    "truth_in_ci": "True value inside the interval?",
    "cross_elasticity": "Competitor-price elasticity",
    "classification": "Class",
    "n_obs": "Observations",
    "method": "Method",
    "uplift": "Estimated effect",
    "true_uplift": "True effect",
    "std_error_log": "Standard error (log)",
    "treated_regions": "Promotion provinces",
    "control_regions": "Control provinces",
    "price_change_pct": "Price change",
    "expected_volume_change_pct": "Expected volume change",
    "expected_gross_profit_change": "Expected gross profit change (TRY)",
    "gross_profit_change_low": "Gross profit change, low (TRY)",
    "gross_profit_change_high": "Gross profit change, high (TRY)",
    "baseline_gross_profit": "Current gross profit (TRY)",
    "binding_constraint": "Deciding rule",
    "momentum_rank": "Rank",
    "current_share": "Current share",
    "prior_share": "Prior share",
    "share_change_pp": "Share change (pp)",
    "momentum_signal": "Trend",
    "company_rank": "Rank in province",
    "market_share": "Market share",
    "market_yoy_growth": "Market growth (yearly)",
    "hhi": "HHI (concentration)",
    "concentration_classification": "Concentration level",
    "opportunity_rank": "Rank",
    "opportunity_score": "Opportunity score",
    "market_growth": "Market growth (yearly)",
    "focus_share": "Company share",
    "share_momentum": "Share trend",
    "gross_margin_pct": "Gross margin",
    "market_volume": "Market volume (MWh)",
    "market_volume_mwh": "Market volume (MWh)",
    "focus_volume_mwh": "Company volume (MWh)",
    "focus_market_share": "Company share",
    "market_size_score": "Market size score",
    "market_growth_score": "Growth score",
    "share_gap_score": "Share gap score",
    "momentum_score": "Trend score",
    "margin_score": "Margin score",
    "competition_score": "Competition score",
    "variable_cost": "Variable cost (TRY)",
}

VALUE_LABELS: dict[str, str] = {
    # estimators
    "elastic": "Elastic (price-sensitive)",
    "inelastic": "Inelastic (less price-sensitive)",
    "naive": "Simple comparison",
    "price_adjusted": "Price-adjusted",
    # SQL classifications (codes that already read well, such as "Stable", pass through)
    "Gaining": "Gaining share",
    "Losing": "Losing share",
    # price recommendation rules
    "step cap": "Price step cap",
    "volume-loss guard": "Volume-loss limit",
    "profit-maximising price": "Profit-maximising price",
    "inelastic demand: raise to the step cap": "Inelastic demand: raise to the step cap",
    "margin floor": "Margin floor",
    "margin floor (not reachable in one step)": "Margin floor (not reachable in one step)",
    # booleans
    "True": "Yes",
    "False": "No",
}


def translate_value(value: object) -> object:
    """Translate one enumerated code (booleans included); unknown values pass through."""

    return VALUE_LABELS.get(str(value), value)


def localize_frame(frame: pd.DataFrame, *, translate_values: bool = True) -> pd.DataFrame:
    """Return a display copy with readable column headers and translated enumerated codes."""

    result = frame.copy()
    if translate_values:
        for column in result.columns:
            series = result[column]
            if pd.api.types.is_bool_dtype(series) or pd.api.types.is_object_dtype(series):
                result[column] = series.map(translate_value)
    return result.rename(columns=COLUMN_LABELS)


def order_segments(frame: pd.DataFrame, column: str = "customer_segment_name") -> pd.DataFrame:
    """Sort rows into the display order Residential, Commercial (SME), Industrial."""

    rank = {name: position for position, name in enumerate(SEGMENT_ORDER)}
    order = frame[column].map(rank).fillna(len(rank))
    return frame.assign(_order=order).sort_values("_order", kind="stable").drop(columns="_order")


def label_map(mapping: Mapping[str, str], keys: list[str]) -> dict[str, str]:
    """Subset of ``mapping`` for the given keys (used for chart axis labels)."""

    return {key: mapping[key] for key in keys if key in mapping}
