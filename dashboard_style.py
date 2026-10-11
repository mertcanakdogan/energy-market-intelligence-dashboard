"""Visual layer of the Streamlit app: one CSS block and the small HTML components.

The design follows docs/DESIGN.md. Colours each carry one meaning: lacivert (navy) for prices and
headings, kaçak kırmızısı (red) only for deductions, leakage and policy breaches, sertifika
yeşili (green) only for gains and positive outcomes. The web fonts are loaded by Streamlit from
``.streamlit/config.toml``; this module only refers to them by name.
"""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from energy_market_intelligence.localization import (
    format_number,
    format_pct,
    order_segments,
)
from energy_market_intelligence.pricing_visualization import Bill

GLOBAL_CSS = """
<style>
:root {
  --tv-navy: #1F3A5F; --tv-leak: #C8462B; --tv-gain: #2E7D5B; --tv-slate: #6B7480;
  --tv-ink: #1B2430; --tv-rule: #E3E7EA; --tv-panel: #F2F4F5;
  --tv-mono: 'IBM Plex Mono', Consolas, Menlo, monospace;
  --tv-head: 'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif;
}
::selection {background: #C5D0DF; color: var(--tv-ink);}
.block-container {padding-top: 2.4rem; padding-bottom: 3.5rem; max-width: 1360px;}
h1, h2, h3, h4 {color: var(--tv-navy);}
h1 {letter-spacing: -0.01em; line-height: 1.12;}
h2, h3 {letter-spacing: 0;}
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
.tv-callout--note {border-top-color: var(--tv-slate);}
.tv-callout--note .tv-label {color: var(--tv-slate);}
.tv-callout--breach {border-top-color: var(--tv-leak);}
.tv-callout--breach .tv-label {color: var(--tv-leak);}
.tv-callout--gain {border-top-color: var(--tv-gain);}
.tv-callout--gain .tv-label {color: var(--tv-gain);}

/* The signature: fatura dökümü (bill-style itemisation). */
.fatura {
  background: #FFFFFF; border: 1px solid var(--tv-rule); border-top: 4px solid var(--tv-navy);
  padding: 1rem 1.3rem 1.1rem; max-width: 36rem; color: var(--tv-ink);
}
.fatura-head {
  display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;
  gap: 0.2rem 1rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--tv-rule);
}
.fatura-title {
  font-family: var(--tv-head); font-weight: 700; letter-spacing: 0.16em; font-size: 1.1rem;
  color: var(--tv-navy);
}
.fatura-meta {font-size: 0.875rem; color: var(--tv-slate);}
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
@media (min-width: 521px) {.fl--net .fl-label {white-space: nowrap;}}
.fatura-foot {margin: 0.65rem 0 0; font-size: 0.92rem; color: var(--tv-slate);}
.fatura-foot b {color: var(--tv-leak); font-family: var(--tv-mono); font-weight: 600;}
@media (max-width: 520px) {
  .fatura {padding: 0.9rem 0.9rem 1rem;}
  .fl {font-size: 1rem;}
  .fl--net {font-size: 1.1rem;}
  .fl-pct {display: none;}
  .fl-amt {min-width: 5.2rem;}
}

/* Link cards on the landing page: the question is the link. */
[class*="st-key-card-"] {
  border: 1px solid var(--tv-rule); border-top: 3px solid var(--tv-navy); border-radius: 0;
  padding: 0.9rem 1.1rem 1rem; height: 100%; box-sizing: border-box;
}
[data-testid="stColumn"]:has([class*="st-key-card-"]) > [data-testid="stVerticalBlock"],
[data-testid="stColumn"]:has([class*="st-key-card-"]) [data-testid="stLayoutWrapper"] {height: 100%;}
[data-testid="stPageLink"] a {padding-left: 0; text-decoration: none;}
[data-testid="stPageLink"] a:hover p {text-decoration: underline;}
[data-testid="stPageLink"] p {font-weight: 600; color: var(--tv-navy);}
[class*="st-key-card-"] [data-testid="stPageLink"] p {
  font-family: var(--tv-head); font-weight: 700; font-size: 1.35rem; color: var(--tv-navy);
}
[data-testid="stPageLink"] a::after {content: "\\2192"; margin-left: 0.4rem; color: var(--tv-navy);}
.tv-chart-title {
  font-family: var(--tv-head); font-weight: 700; font-size: 1.3rem; line-height: 1.2;
  color: var(--tv-navy); margin: 0.9rem 0 0.2rem;
}
.tv-answer {margin: 0.35rem 0 0; color: var(--tv-ink); line-height: 1.45;}

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


def callout(kind: str, label: str, text: str) -> None:
    """Top-ruled callout (the same rule as the bill and the cards). ``kind``: ``takeaway`` (navy), ``note``, ``breach`` or ``gain``."""

    modifier = "" if kind == "takeaway" else f" tv-callout--{kind}"
    st.markdown(
        f'<div class="tv-callout{modifier}"><span class="tv-label">{_html(label)}</span>'
        f"{_html(text)}</div>",
        unsafe_allow_html=True,
    )


def intro(label: str, text: str) -> None:
    """Quiet one-line explanation under the page title."""

    st.markdown(
        f'<div class="tv-intro"><strong>{_html(label)}</strong> {_html(text)}</div>',
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


def bill_display_amounts(bill: Bill) -> list[float]:
    """Amounts at two decimals that add up exactly (the net line is list minus the deductions)."""

    amounts = [round(line.amount, 2) for line in bill.lines]
    amounts[-1] = round(amounts[0] - sum(amounts[1:-1]), 2)
    return amounts


def bill_html(bill: Bill) -> str:
    """The "fatura dökümü": per-MWh itemisation with dotted leaders and tabular amounts."""

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
            f'<span class="fl-pct" aria-label="liste fiyatın yüzdesi">{share}</span>'
            "</div>"
        )
    return (
        f'<section class="fatura" aria-label="Fatura dökümü, {_html(bill.scope)}">'
        '<div class="fatura-head"><span class="fatura-title">FATURA DÖKÜMÜ</span>'
        f'<span class="fatura-meta">{_html(bill.scope)} · TL/MWh · 2025</span></div>'
        + "".join(rows)
        + f'<div class="fatura-foot">Kaçak oranı: <b>{format_pct(bill.leakage_rate, 1)}</b></div>'
        "</section>"
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
            "Gerçek değer aralığın içinde" if row.truth_in_ci else "Gerçek değer aralığın dışında"
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
            f"{_row('Gerçek', format_number(row.true_elasticity, 2))}"
            f"{_row('Tahmin', format_number(row.elasticity, 2))}"
            f"{_row('%95 aralık', f'{format_number(row.ci_low, 2)} / {format_number(row.ci_high, 2)}')}"
            f'<div class="{verdict_class}">{verdict}</div>'
            "</div>"
        )
    legend = (
        '<div class="tv-legend">Dolu daire: tahmin. Açık baklava: gerçek değer. '
        "Açık mavi şerit: %95 güven aralığı. Esneklik: fiyat %1 artınca hacmin yüzde kaç "
        "değiştiği.</div>"
    )
    return f'<div class="tv-trust">{"".join(cards)}</div>{legend}'
