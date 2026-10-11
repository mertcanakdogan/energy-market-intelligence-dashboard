"""Visual layer of the Streamlit app: one CSS block and the small HTML components.

The design follows DESIGN.md. Colours each carry one meaning: grid navy for prices and
headings, leak red only for deductions, leakage and policy breaches, certificate green only for
gains and positive outcomes, transformer grey for secondary text. The web fonts are loaded by
Streamlit from ``.streamlit/config.toml``; this module only refers to them by name.
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import pandas as pd
import streamlit as st

from energy_market_intelligence.localization import (
    SEGMENT_ORDER,
    format_number,
    format_pct,
    order_segments,
)
from energy_market_intelligence.pricing_visualization import (
    DEDUCTION_LABELS,
    NET_LABEL,
    Bill,
    portfolio_bill,
)

GITHUB_URL = "https://github.com/mertcanakdogan/energy-market-intelligence-dashboard"
LINKEDIN_URL = "https://www.linkedin.com/in/mertcanakdogan/"

# One-line meaning of each bill line, shown under the bill where the reader meets the words.
BILL_TERMS = (
    (DEDUCTION_LABELS["on_invoice_discount"], "comes off the price on the invoice."),
    (DEDUCTION_LABELS["off_invoice_rebate"], "is paid back to the customer later."),
    (DEDUCTION_LABELS["payment_term_cost"], "is what waiting to be paid costs."),
    (DEDUCTION_LABELS["freight_service_cost"], "covers delivery and support."),
    (NET_LABEL, "is the price the company keeps."),
    ("Leakage rate", "is the share of the list price it does not keep."),
)

GLOBAL_CSS = """
<style>
:root {
  --tv-navy: #1F3A5F; --tv-leak: #C8462B; --tv-gain: #2E7D5B; --tv-slate: #6B7480;
  --tv-ink: #1B2430; --tv-rule: #E3E7EA; --tv-panel: #F2F4F5;
  --tv-slate-panel: #5C6570; --tv-leak-panel: #B83F25; --tv-band: #7B92B1;
  --tv-mono: 'IBM Plex Mono', Consolas, Menlo, monospace;
  --tv-head: 'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif;
}
::selection {background: #C5D0DF; color: var(--tv-ink);}
.block-container {padding-top: 2.4rem; padding-bottom: 3.5rem; max-width: 1360px;}
h1, h2, h3, h4 {color: var(--tv-navy);}
h1 {letter-spacing: -0.01em; line-height: 1.12;}
h2, h3 {letter-spacing: 0;}
[data-testid="stHeading"] {margin-top: 1.2rem;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: var(--tv-slate); opacity: 1;}
[data-testid="stMetric"] {border-top: 1px solid var(--tv-rule); padding-top: 0.65rem;}
[data-testid="stMetricLabel"] p {color: var(--tv-slate); font-size: 0.92rem;}
[data-testid="stMetricValue"] {
  font-family: var(--tv-mono); font-variant-numeric: tabular-nums; font-weight: 500;
  font-size: 1.4rem; color: var(--tv-ink);
}
[data-testid="stMetricValue"] > div, [data-testid="stMetricLabel"] p,
[data-testid="stMetricDelta"] > div {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
  overflow-wrap: anywhere;
}
[data-testid="stMetricDelta"] {font-family: var(--tv-mono); font-size: 0.85rem;}

/* Keyboard focus: a 2px navy ring with an offset on links and buttons that show no ring of
   their own (Streamlit's own box-shadow ring on heading links and expanders is left alone). */
[data-testid="stPageLink"] a:focus-visible, [data-testid="stSidebarNav"] a:focus-visible,
[data-testid="stSidebarNavLink"]:focus-visible, [data-testid="stMarkdownContainer"] a:focus-visible,
[data-testid="stBaseButton-segmented_control"]:focus-visible,
[data-testid="stBaseButton-segmented_controlActive"]:focus-visible,
[data-testid="stBaseButton-secondary"]:focus-visible, [data-testid="stBaseButton-primary"]:focus-visible {
  outline: 2px solid var(--tv-navy); outline-offset: 2px;
}
[data-testid="stHeading"] a:focus-visible {outline: none;}

/* Callouts: intro line, takeaway (navy), caveat (slate), breach (red), gain (green). */
.tv-intro {margin: 0.1rem 0 1.1rem; max-width: 64rem; font-size: 1.05rem; color: var(--tv-ink);}
.tv-intro strong {color: var(--tv-navy);}
.tv-callout {
  border-top: 2px solid var(--tv-navy); background: var(--tv-panel);
  padding: 0.75rem 1.1rem 0.85rem; margin: 0.9rem 0 1.4rem;
  color: var(--tv-ink); line-height: 1.5;
}
.tv-callout .tv-label {
  display: block; font-family: var(--tv-head); font-weight: 700; font-size: 1.05rem;
  color: var(--tv-navy); margin-bottom: 0.1rem;
}
.tv-callout .tv-line {display: grid; grid-template-columns: 4.4rem 1fr; gap: 0 0.4rem; margin-top: 0.3rem;}
.tv-callout .tv-line b {color: var(--tv-navy);}
.tv-callout--note {border-top-color: var(--tv-slate);}
.tv-callout--note .tv-label {color: var(--tv-slate-panel);}
.tv-callout--breach {border-top-color: var(--tv-leak);}
.tv-callout--breach .tv-label {color: var(--tv-leak-panel);}
.tv-callout--gain {border-top-color: var(--tv-gain);}
.tv-callout--gain .tv-label {color: var(--tv-gain);}

/* The signature: the price breakdown (bill-style itemisation). */
.bill {
  background: #FFFFFF; border: 1px solid var(--tv-rule); border-top: 4px solid var(--tv-navy);
  padding: 1rem 1.3rem 1.1rem; max-width: 36rem; color: var(--tv-ink);
  container-type: inline-size;
}
.bill-head {
  display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;
  gap: 0.2rem 1rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--tv-rule);
}
.bill-title {
  font-family: var(--tv-head); font-weight: 700; letter-spacing: 0.16em; font-size: 1.1rem;
  color: var(--tv-navy);
}
.bill-meta {font-size: 0.875rem; color: var(--tv-slate);}
.fl {display: flex; align-items: baseline; gap: 0.45rem; padding: 0.42rem 0; font-size: 1.05rem;}
.fl-op {
  flex: 0 0 0.9rem; font-family: var(--tv-mono); color: var(--tv-slate); text-align: center;
}
.fl-label {flex: 0 1 auto; min-width: 0;}
.fl-dots {
  flex: 1 1 0.8rem; min-width: 0.8rem; align-self: flex-end; margin-bottom: 0.38em;
  border-bottom: 2px dotted #AAB2BB;
}
.fl-amt {
  flex: 0 0 auto; min-width: 6.2rem; text-align: right; font-weight: 500;
  font-family: var(--tv-mono); font-variant-numeric: tabular-nums;
}
.fl-pct {
  flex: 0 0 3.7rem; text-align: right; font-size: 0.85rem; color: var(--tv-slate);
  font-family: var(--tv-mono); font-variant-numeric: tabular-nums;
}
.fl--deduction .fl-amt {color: var(--tv-leak);}
.fl--net {
  margin-top: 0.45rem; padding-top: 0.7rem; border-top: 2px solid var(--tv-navy);
  font-weight: 700; color: var(--tv-navy); font-size: 1.2rem;
}
.fl--net .fl-op, .fl--net .fl-pct {color: var(--tv-navy);}
.fl--net .fl-amt {font-weight: 600;}
@container (min-width: 27rem) {.fl--net .fl-label {white-space: nowrap;}}
.bill-foot {margin: 0.65rem 0 0; font-size: 0.92rem; color: var(--tv-slate);}
.bill-foot b {color: var(--tv-leak); font-family: var(--tv-mono); font-weight: 600;}
/* The bill sits in a column, so it adapts to its own width, not the viewport's. */
@media (max-width: 520px) {.bill {padding: 0.9rem 0.9rem 1rem;}}
@container (max-width: 27rem) {
  .fl {font-size: 1rem;}
  .fl--net {font-size: 1.1rem;}
  .fl-pct {display: none;}
  .fl-amt {min-width: 5.2rem;}
}

/* Leakage by customer segment, next to the bill. */
.tv-seg {
  border: 1px solid var(--tv-rule); border-top: 3px solid var(--tv-navy);
  padding: 0.9rem 1.1rem 0.4rem; color: var(--tv-ink);
}
.tv-seg-title {
  font-family: var(--tv-head); font-weight: 700; font-size: 1.3rem; line-height: 1.2;
  color: var(--tv-navy);
}
.tv-seg-sub {margin: 0.3rem 0 0.4rem; font-size: 0.875rem; line-height: 1.45; color: var(--tv-slate);}
.tv-seg-row {padding: 0.65rem 0 0.7rem; border-top: 1px solid var(--tv-rule);}
.tv-seg-line {display: flex; justify-content: space-between; align-items: baseline; gap: 0.8rem;}
.tv-seg-name {font-family: var(--tv-head); font-weight: 600; font-size: 1.1rem; color: var(--tv-navy);}
.tv-seg-rate {
  font-family: var(--tv-mono); font-variant-numeric: tabular-nums; font-weight: 500;
  font-size: 1.05rem; color: var(--tv-leak);
}
.tv-seg-bar {display: flex; gap: 2px; height: 0.5rem; margin: 0.4rem 0 0.35rem;}
.tv-seg-kept {background: var(--tv-navy);}
.tv-seg-leak {background: var(--tv-leak);}
.tv-seg-net {font-size: 0.875rem; color: var(--tv-slate);}
.tv-seg-net b {
  font-family: var(--tv-mono); font-variant-numeric: tabular-nums; font-weight: 500;
  color: var(--tv-ink);
}

/* Link cards on the landing page: the question is the link. */
[class*="st-key-card-"] {
  border: 1px solid var(--tv-rule); border-top: 3px solid var(--tv-navy); border-radius: 0;
  padding: 0.9rem 1.1rem 1rem; flex: 1 1 auto; box-sizing: border-box;
}
.st-key-card-action {background: var(--tv-panel); border-top-width: 4px;}
/* Equal-height cards: stretch every level from the column down to the card. */
[data-testid="stColumn"]:has([class*="st-key-card-"]) {display: flex; flex-direction: column;}
[data-testid="stColumn"]:has([class*="st-key-card-"]) > [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has([class*="st-key-card-"]) [data-testid="stLayoutWrapper"] {flex: 1 1 auto;}
[data-testid="stPageLink"] a {padding-left: 0; text-decoration: none;}
[data-testid="stPageLink"] a:hover p {text-decoration: underline;}
[data-testid="stPageLink"] p {font-weight: 600; color: var(--tv-navy);}
[class*="st-key-card-"] [data-testid="stPageLink"] p {
  font-family: var(--tv-head); font-weight: 700; font-size: 1.35rem; color: var(--tv-navy);
  white-space: normal; overflow: visible; text-overflow: clip; line-height: 1.2;
}
[class*="st-key-card-"] [data-testid="stPageLink"] a,
[class*="st-key-card-"] [data-testid="stPageLink"] a > div {max-width: 100%; overflow: visible;}
[class*="st-key-card-"] [data-testid="stPageLink"] a {justify-content: space-between; align-items: flex-start;}
[class*="st-key-card-"] [data-testid="stPageLink"] a > div {flex: 1 1 auto;}
@media (min-width: 901px) {[class*="st-key-card-"] [data-testid="stPageLink"] a {min-height: 3.2rem;}}
/* Three cards side by side need room; below that they stack. */
@media (max-width: 900px) {
  [data-testid="stHorizontalBlock"]:has([class*="st-key-card-"]) {flex-wrap: wrap;}
  [data-testid="stHorizontalBlock"]:has([class*="st-key-card-"]) > [data-testid="stColumn"] {
    flex: 1 1 100%; min-width: 100%;
  }
}
[data-testid="stPageLink"] a::after {content: "\\2192"; margin-left: 0.4rem; color: var(--tv-navy);}
.tv-chart-title {
  font-family: var(--tv-head); font-weight: 700; font-size: 1.3rem; line-height: 1.2;
  color: var(--tv-navy); margin: 0.9rem 0 0.2rem;
}
/* Streamlit pulls the last block of a markdown container up by 1rem; give that back. */
.tv-answer {margin: 0.35rem 0 0; padding-bottom: 1rem; color: var(--tv-ink); line-height: 1.45;}

/* Bill terms (under the bill) and the closing line of the overview. */
.tv-terms {margin: 0.9rem 0 0; max-width: 36rem; font-size: 0.875rem; line-height: 1.5; color: var(--tv-slate);}
.tv-terms b {font-weight: 600; color: var(--tv-ink);}
.tv-closing {
  margin: 2.2rem 0 0.4rem; padding-top: 0.9rem; border-top: 1px solid var(--tv-rule);
  color: var(--tv-ink);
}

/* Model trust strip: true value, estimate and interval per segment. */
.tv-trust {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.2rem;}
.tv-trust-card {border-top: 1px solid var(--tv-rule); padding-top: 0.6rem;}
.tv-trust-seg {font-family: var(--tv-head); font-weight: 600; font-size: 1.1rem; color: var(--tv-navy);}
.tv-scale {position: relative; height: 1.5rem; margin: 0.5rem 0 0.45rem;}
.tv-scale-axis {position: absolute; left: 0; right: 0; top: 50%; border-top: 1px solid var(--tv-rule);}
.tv-scale-ci {position: absolute; top: 50%; height: 0.55rem; margin-top: -0.275rem;
  background: #C5D0DF; border-radius: 1px;}
.tv-scale-est {position: absolute; top: 50%; width: 0.7rem; height: 0.7rem; margin: -0.35rem 0 0 -0.35rem;
  background: var(--tv-navy); border-radius: 50%;}
.tv-scale-true {position: absolute; top: 50%; width: 0.85rem; height: 0.85rem; margin: -0.425rem 0 0 -0.425rem;
  border: 2px solid var(--tv-ink); transform: rotate(45deg); box-sizing: border-box;}
.tv-trust-row {display: flex; justify-content: space-between; gap: 0.6rem; font-size: 0.92rem;
  color: var(--tv-slate);}
.tv-trust-row b {font-family: var(--tv-mono); font-weight: 500; color: var(--tv-ink);}
.tv-trust-ok {margin-top: 0.25rem; font-size: 0.9rem; font-weight: 600; color: var(--tv-gain);}
.tv-legend {margin: 1.1rem 0 0.6rem; font-size: 0.875rem; color: var(--tv-slate);}
@media (max-width: 640px) {.tv-trust {grid-template-columns: minmax(0, 1fr);}}
@media (max-width: 640px) {
  h1 {font-size: 2.1rem !important;}
  .block-container {padding-top: 3.2rem;}
}
</style>
"""


def inject_global_css() -> None:
    """Add the app-wide stylesheet (called once from ``app.py``)."""

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def _html(text: str) -> str:
    return escape(text, quote=True)


def callout(kind: str, label: str, text: str | Sequence[tuple[str, str]]) -> None:
    """Top-ruled callout (the same rule as the bill and the cards).

    ``kind``: ``takeaway`` (navy), ``note``, ``breach`` or ``gain``. ``text`` is one sentence or
    a sequence of ``(lead, sentence)`` pairs shown as short lines with a bold lead-in.
    """

    modifier = "" if kind == "takeaway" else f" tv-callout--{kind}"
    if isinstance(text, str):
        body = _html(text)
    else:
        body = "".join(
            f'<span class="tv-line"><b>{_html(lead)}</b> {_html(sentence)}</span>'
            for lead, sentence in text
        )
    st.markdown(
        f'<div class="tv-callout{modifier}"><span class="tv-label">{_html(label)}</span>'
        f"{body}</div>",
        unsafe_allow_html=True,
    )


def intro(label: str, text: str) -> None:
    """Quiet one-line explanation under the page title."""

    st.markdown(
        f'<div class="tv-intro"><strong>{_html(label)}:</strong> {_html(text)}</div>',
        unsafe_allow_html=True,
    )


def chart_title(text: str) -> None:
    """Chart heading rendered in HTML so that it wraps on narrow screens."""

    st.markdown(f'<div class="tv-chart-title">{_html(text)}</div>', unsafe_allow_html=True)


def lead(text: str) -> None:
    """One plain sentence under the hero title."""

    st.markdown(f'<div class="tv-intro">{_html(text)}</div>', unsafe_allow_html=True)


def answer(text: str) -> None:
    """One-line data-driven answer inside a landing-page card."""

    st.markdown(f'<div class="tv-answer">{_html(text)}</div>', unsafe_allow_html=True)


def bill_terms_html() -> str:
    """One-line meaning of each bill line, as a compact paragraph under the bill."""

    parts = " ".join(f"<b>{_html(term)}</b> {_html(meaning)}" for term, meaning in BILL_TERMS)
    return f'<p class="tv-terms">{parts}</p>'


def closing_html() -> str:
    """Author line with the links to the code and to LinkedIn (no employer, no contact data)."""

    return (
        '<div class="tv-closing">Built by <b>Mert Can Akdoğan</b> · '
        f'<a href="{GITHUB_URL}">Method and code on GitHub</a> · '
        f'<a href="{LINKEDIN_URL}">LinkedIn</a></div>'
    )


def bill_display_amounts(bill: Bill) -> list[float]:
    """Amounts at two decimals that add up exactly (the net line is list minus the deductions)."""

    amounts = [round(line.amount, 2) for line in bill.lines]
    amounts[-1] = round(amounts[0] - sum(amounts[1:-1]), 2)
    return amounts


def bill_html(bill: Bill) -> str:
    """The "price breakdown": per-MWh itemisation with dotted leaders and tabular amounts."""

    amounts = bill_display_amounts(bill)
    rows = []
    for line, amount in zip(bill.lines, amounts, strict=True):
        operator = {"list": "", "deduction": "−", "net": "="}[line.kind]
        sign = "−" if line.kind == "deduction" else ""
        share = format_pct(line.share_of_list, 1)
        rows.append(
            f'<div class="fl fl--{line.kind}">'
            f'<span class="fl-op" aria-hidden="true">{operator}</span>'
            f'<span class="fl-label">{_html(line.label)}</span>'
            '<span class="fl-dots" aria-hidden="true"></span>'
            f'<span class="fl-amt">{sign}{format_number(amount, 2)}</span>'
            f'<span class="fl-pct" aria-label="percentage of list price">{share}</span>'
            "</div>"
        )
    return (
        f'<section class="bill" aria-label="Price breakdown, {_html(bill.scope)}">'
        '<div class="bill-head"><span class="bill-title">PRICE BREAKDOWN</span>'
        f'<span class="bill-meta">{_html(bill.scope)} · TRY/MWh · 2025</span></div>'
        + "".join(rows)
        + f'<div class="bill-foot">Leakage rate: <b>{format_pct(bill.leakage_rate, 1)}</b></div>'
        "</section>"
    )


def segment_leakage_html(waterfall: pd.DataFrame) -> str:
    """Leakage rate and net price of each customer segment: where leakage differs.

    One row per segment: its name and leakage rate, a bar of the list price split into the part
    kept (navy) and the part that leaks (red), and the net price per MWh.
    """

    rows = []
    for name in SEGMENT_ORDER:
        if name not in set(waterfall["customer_segment_name"]):
            continue
        bill = portfolio_bill(waterfall, name)
        net = bill.lines[-1]
        leak = bill.leakage_rate
        rows.append(
            '<div class="tv-seg-row">'
            f'<div class="tv-seg-line"><span class="tv-seg-name">{_html(name)}</span>'
            f'<span class="tv-seg-rate">{format_pct(leak, 1)}</span></div>'
            '<div class="tv-seg-bar" aria-hidden="true">'
            f'<span class="tv-seg-kept" style="width:{100 * (1 - leak):.1f}%"></span>'
            f'<span class="tv-seg-leak" style="width:{100 * leak:.1f}%"></span></div>'
            '<div class="tv-seg-line tv-seg-net"><span>Net price</span>'
            f"<b>{format_number(net.amount, 2)}</b></div>"
            "</div>"
        )
    return (
        '<section class="tv-seg" aria-label="Leakage by customer segment">'
        '<div class="tv-seg-title">Where leakage differs</div>'
        '<p class="tv-seg-sub">Leakage rate by customer segment, with the net price in TRY/MWh. '
        "Bars show the list price: navy is kept, red leaks away.</p>" + "".join(rows) + "</section>"
    )


def _row(label: str, value: str) -> str:
    return f'<div class="tv-trust-row"><span>{_html(label)}</span><b>{_html(value)}</b></div>'


def trust_strip_html(table: pd.DataFrame) -> str:
    """True versus estimated price elasticity with its 95% interval, one card per segment."""

    ordered = order_segments(table)
    low = float(min(ordered["ci_low"].min(), ordered["true_elasticity"].min()))
    high = float(max(ordered["ci_high"].max(), ordered["true_elasticity"].max()))
    pad = (high - low) * 0.06
    low, high = low - pad, high + pad

    def place(value: float) -> float:
        return 100 * (float(value) - low) / (high - low)

    cards = []
    for row in ordered.itertuples(index=False):
        verdict = (
            "True value is inside the interval"
            if row.truth_in_ci
            else "True value is outside the interval"
        )
        verdict_class = "tv-trust-ok" if row.truth_in_ci else "tv-trust-row"
        width = place(row.ci_high) - place(row.ci_low)
        cards.append(
            '<div class="tv-trust-card">'
            f'<div class="tv-trust-seg">{_html(row.customer_segment_name)}</div>'
            '<div class="tv-scale" aria-hidden="true"><span class="tv-scale-axis"></span>'
            f'<span class="tv-scale-ci" style="left:{place(row.ci_low):.1f}%;width:{width:.1f}%">'
            "</span>"
            f'<span class="tv-scale-est" style="left:{place(row.elasticity):.1f}%"></span>'
            f'<span class="tv-scale-true" style="left:{place(row.true_elasticity):.1f}%"></span>'
            "</div>"
            f"{_row('True', format_number(row.true_elasticity, 2))}"
            f"{_row('Estimate', format_number(row.elasticity, 2))}"
            f"{_row('95% interval', f'{format_number(row.ci_low, 2)} / {format_number(row.ci_high, 2)}')}"
            f'<div class="{verdict_class}">{verdict}</div>'
            "</div>"
        )
    legend = (
        '<div class="tv-legend">Filled dot: estimate. Open diamond: true value. '
        "Light blue band: 95% confidence interval. Elasticity: the percent change in volume "
        "when the price rises 1%.</div>"
    )
    return f'<div class="tv-trust">{"".join(cards)}</div>{legend}'
