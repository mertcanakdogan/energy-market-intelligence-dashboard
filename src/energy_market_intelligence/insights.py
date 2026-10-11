"""Plain-language takeaways computed from the analytical tables.

Every sentence is built from calculated numbers (nothing is hard-coded), so the text on the app
pages always matches the data on the same page.
"""

from __future__ import annotations

import pandas as pd

from energy_market_intelligence.localization import (
    CURRENCY,
    format_number,
    format_pct,
    format_try,
    format_try_per_mwh,
    order_segments,
)
from energy_market_intelligence.pricing_visualization import (
    Bill,
    BillLine,
    segment_waterfall_table,
)

NBSP = chr(0xA0)  # non-breaking space


def _worst_row(frame: pd.DataFrame, column: str, *, largest: bool = True) -> pd.Series:
    return frame.loc[frame[column].idxmax() if largest else frame[column].idxmin()]


def _rose_or_fell(value: float) -> str:
    return "rose" if value >= 0 else "fell"


def _join(items: list[str]) -> str:
    """``a, b and c``."""

    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def price_waterfall_insight(waterfall: pd.DataFrame, flags: pd.DataFrame) -> str:
    """Realisation, the segment with the largest list-to-pocket gap and policy breaches."""

    table = segment_waterfall_table(waterfall)
    table = table.assign(gap=1 - table["pocket_price"] / table["list_price"])
    realization = waterfall["pocket_revenue"].sum() / waterfall["list_revenue"].sum()
    worst = _worst_row(table, "gap")
    text = (
        f"Of every {CURRENCY}{NBSP}100 of sales at list price, the company keeps "
        f"{CURRENCY}{NBSP}{format_number(realization * 100, 1)} on average. The gap is widest "
        f"in the {worst['customer_segment_name']} segment: list price "
        f"{format_try_per_mwh(worst['list_price'])}, pocket price "
        f"{format_try_per_mwh(worst['pocket_price'])} "
        f"({format_pct(worst['gap'])} lower)."
    )
    breaches = flags[flags["exceeds_policy"]]
    if breaches.empty:
        return text + " No province gives discounts above the policy limit."
    provinces = breaches.groupby("region_name")["revenue_leakage_above_policy"].sum()
    top = provinces.sort_values(ascending=False).head(3).index.tolist()
    return (
        text + f" In {breaches['region_name'].nunique()} provinces ({len(breaches)} province "
        "and segment combinations) the discount is above the policy limit; this extra "
        "discount costs "
        f"{format_try(breaches['revenue_leakage_above_policy'].sum())} a year "
        f"(most in {_join(top)})."
    )


def pvm_insight(summary: pd.DataFrame) -> str:
    """Why revenue and gross profit moved: price, volume, mix and unit cost."""

    row = summary.iloc[0]
    text = (
        f"Net revenue {_rose_or_fell(row['total_revenue_change'])} by "
        f"{format_try(abs(row['total_revenue_change']))} "
        f"(volume {format_try(row['volume_effect'], signed=True)}, "
        f"price {format_try(row['price_effect'], signed=True)}, "
        f"mix {format_try(row['mix_effect'], signed=True)}). "
        f"Gross profit {_rose_or_fell(row['total_gp_change'])} by "
        f"{format_try(abs(row['total_gp_change']))}; "
        f"the change in unit cost contributed {format_try(row['gp_cost_effect'], signed=True)}."
    )
    if row["gp_cost_effect"] < 0 and row["gp_price_effect"] > 0:
        recovery = row["gp_price_effect"] / -row["gp_cost_effect"]
        text += (
            f" Price increases made up for about {format_pct(recovery, 0)} of the cost increase."
        )
    return text


def elasticity_insight(table: pd.DataFrame, price_step: float = 0.05) -> str:
    """Per-segment elasticity in words and how many true values the intervals recover."""

    ordered = order_segments(table)
    estimates = ", ".join(
        f"{row.customer_segment_name} {format_number(row.elasticity, 2)}"
        for row in ordered.itertuples(index=False)
    )
    losses = _join(
        [
            format_pct(1 - (1 + price_step) ** row.elasticity, 1)
            for row in ordered.itertuples(index=False)
        ]
    )
    recovered = int(table["truth_in_ci"].sum()) if "truth_in_ci" in table else 0
    text = (
        f"Estimated elasticities: {estimates}. If prices rise {format_pct(price_step, 0)}, "
        f"volume falls about {losses} respectively: the most price-sensitive segment loses "
        "the most volume."
    )
    if "truth_in_ci" in table:
        text += (
            " The data are synthetic, so the true values are known: in "
            f"{recovered} of {len(table)} segments the true elasticity lies inside the 95% "
            "confidence interval of the estimate."
        )
    return text


def promo_insight(estimates: pd.DataFrame) -> str:
    """Compare the naive before/after reading with the price-adjusted promotion effect."""

    by_method = estimates.set_index("method")
    adjusted, naive = by_method.loc["price_adjusted"], by_method.loc["naive"]
    text = (
        f"The promotion added about {format_pct(adjusted['uplift'])} extra volume "
        f"(95% confidence interval: {format_pct(adjusted['ci_low'])} to "
        f"{format_pct(adjusted['ci_high'])}). "
        f"A simple before/after comparison shows {format_pct(naive['uplift'])}; "
        "the difference comes from the effect of the promotion discount and the list-price "
        "increases on volume."
    )
    if "true_uplift" in adjusted:
        text += (
            f" The true value set in the data generator is {format_pct(adjusted['true_uplift'])}: "
            "the price-adjusted estimate is close to it, the simple comparison overstates it."
        )
    return text


def recommendation_insight(table: pd.DataFrame) -> str:
    """Total expected gross-profit effect of the recommended price steps."""

    baseline = table["baseline_gross_profit"].sum()
    change = table["expected_gross_profit_change"].sum()
    volume_base = table["baseline_volume_mwh"].sum()
    volume_change = (
        table["expected_volume_change_pct"] * table["baseline_volume_mwh"]
    ).sum() / volume_base
    price_change = (table["price_change_pct"] * table["baseline_volume_mwh"]).sum() / volume_base
    direction = "rises" if change >= 0 else "falls"
    price_word = "rises" if price_change >= 0 else "falls"
    volume_word = "rises" if volume_change >= 0 else "falls"
    return (
        "If the recommended steps are applied, the pocket price "
        f"{price_word} by {format_pct(abs(price_change), 1)} on average, volume {volume_word} "
        f"by about {format_pct(abs(volume_change), 1)} and gross profit {direction} by "
        f"{format_try(abs(change))} a year ({format_pct(change / baseline, 1, signed=True)})."
    )


# ---------------------------------------------------------------------------------------------
# Landing page: the thesis and one-line answers to the three questions
# ---------------------------------------------------------------------------------------------


def leakage_thesis(leakage_rate: float, *, highlight: bool = False) -> str:
    """The hero sentence of the landing page.

    For example "Of every TRY 100 at list price, the company keeps TRY 85.2 and TRY 14.8 leaks
    away." The currency and its number are joined by a non-breaking space so that a line break
    never separates them. With ``highlight`` the leaked amount is wrapped in Streamlit's red
    text markup.
    """

    leaked = round(leakage_rate * 100, 1)
    kept = f"{CURRENCY}{NBSP}{format_number(100 - leaked, 1)}"
    lost = f"{CURRENCY}{NBSP}{format_number(leaked, 1)}"
    if highlight:
        lost = f":red[{lost}]"
    return (
        f"Of every {CURRENCY}{NBSP}100 at list price, the company keeps {kept} and {lost} "
        "leaks away."
    )


def _largest_deduction(bill: Bill) -> BillLine:
    deductions = [line for line in bill.lines if line.kind == "deduction"]
    return max(deductions, key=lambda line: line.amount)


def leakage_answer(bill: Bill, flags: pd.DataFrame) -> str:
    """Largest bill deduction and the number of province and customer segment combinations
    above the policy limit."""

    largest = _largest_deduction(bill)
    breaches = int(flags["exceeds_policy"].sum())
    return (
        f"The largest item is the {largest.label.lower()} "
        f"({format_pct(largest.share_of_list)} of the list price); {breaches} combinations of "
        "province and customer segment give discounts above the policy limit."
    )


def bridge_answer(summary: pd.DataFrame) -> str:
    """Why revenue and gross profit moved differently, in plain cause form."""

    row = summary.iloc[0]
    revenue, profit = row["total_revenue_change"], row["total_gp_change"]
    price_gain, cost_hit = row["gp_price_effect"], row["gp_cost_effect"]
    movement = (
        f"net revenue {_rose_or_fell(revenue)} by {format_try(abs(revenue))} "
        f"while gross profit {_rose_or_fell(profit)} by {format_try(abs(profit))}"
    )
    if revenue > 0 > profit and price_gain > 0 > cost_hit and -cost_hit > price_gain:
        return (
            f"Prices rose, but costs rose faster: {movement}. Price rises added "
            f"{format_try(price_gain)}; higher unit costs took {format_try(-cost_hit)}."
        )
    return (
        f"{movement[0].upper()}{movement[1:]}. Price changes {_added_or_took(price_gain)} "
        f"{format_try(abs(price_gain))}; unit costs {_added_or_took(cost_hit)} "
        f"{format_try(abs(cost_hit))}."
    )


def _added_or_took(value: float) -> str:
    return "added" if value >= 0 else "took"


def action_answer(table: pd.DataFrame) -> str:
    """Expected yearly gross-profit change of the recommended price steps."""

    change = table["expected_gross_profit_change"].sum()
    share = change / table["baseline_gross_profit"].sum()
    direction = "rise" if change >= 0 else "fall"
    return (
        f"With the recommended price steps, gross profit could {direction} by "
        f"{format_try(abs(change))} a year ({format_pct(share, 1, signed=True)})."
    )


def overview_takeaway(
    bill: Bill, waterfall: pd.DataFrame, recommendation: pd.DataFrame
) -> list[tuple[str, str]]:
    """The three lines under the overview hero: finding, size and action, as (lead, text)."""

    largest = _largest_deduction(bill)
    leaked = round(bill.leakage_rate * 100, 1)
    leaked_revenue = waterfall["list_revenue"].sum() - waterfall["pocket_revenue"].sum()
    change = recommendation["expected_gross_profit_change"].sum()
    share = change / recommendation["baseline_gross_profit"].sum()
    verb = "add" if change >= 0 else "cost"
    return [
        (
            "Finding",
            f"The largest leak is the {largest.label.lower()}, "
            f"{format_pct(largest.share_of_list)} of the list price.",
        ),
        (
            "Size",
            f"{CURRENCY}{NBSP}{format_number(leaked, 1)} of every {CURRENCY}{NBSP}100 at list "
            f"price never reaches the company, or {format_try(leaked_revenue)} a year.",
        ),
        (
            "Action",
            f"The recommended price steps {verb} {format_try(abs(change))} of gross profit a "
            f"year ({format_pct(share, 1, signed=True)}). This is an estimate that assumes no "
            "reaction from competitors.",
        ),
    ]


def trust_note(elasticities: pd.DataFrame) -> str:
    """Honest caveat under the trust strip, with the largest miss computed from the data."""

    miss = (elasticities["elasticity"] - elasticities["true_elasticity"]).abs().max()
    return (
        "Estimated without seeing the true values; largest miss "
        f"{format_number(miss, 2)}. Real data would be noisier."
    )


def promo_proof(estimates: pd.DataFrame) -> str:
    """One line: the price-adjusted promotion uplift next to the true value set in the data."""

    row = estimates.set_index("method").loc["price_adjusted"]
    return (
        f"The same test works for the promotion: uplift estimated at {format_pct(row['uplift'])} "
        f"against a true {format_pct(row['true_uplift'])}."
    )


def headline_findings(
    waterfall: pd.DataFrame,
    flags: pd.DataFrame,
    pvm_summary: pd.DataFrame,
    elasticities: pd.DataFrame,
    promo: pd.DataFrame,
    recommendation: pd.DataFrame,
) -> list[str]:
    """Three findings and one recommendation, one string each."""

    return [
        price_waterfall_insight(waterfall, flags),
        pvm_insight(pvm_summary),
        elasticity_insight(elasticities) + " " + promo_insight(promo),
        recommendation_insight(recommendation),
    ]
