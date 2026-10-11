"""Design system: tokens, Plotly template, price breakdown and the landing-page answers."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pandas as pd
import plotly.io as pio
import pytest

import dashboard_style as style
from energy_market_intelligence import visualization
from energy_market_intelligence.insights import (
    action_answer,
    bridge_answer,
    leakage_answer,
    leakage_thesis,
    overview_takeaway,
    promo_proof,
    trust_note,
)
from energy_market_intelligence.localization import SEGMENT_ORDER
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_visualization import (
    DEDUCTION_LABELS,
    LIST_LABEL,
    NET_LABEL,
    PORTFOLIO,
    bill_waterfall_figure,
    portfolio_bill,
    price_waterfall_figure,
)
from energy_market_intelligence.visualization import GAIN_GREEN, LEAK_RED, NAVY


@pytest.fixture(scope="module")
def theme(project_root: Path) -> dict:
    with (project_root / ".streamlit" / "config.toml").open("rb") as handle:
        return tomllib.load(handle)["theme"]


def test_streamlit_theme_uses_the_design_tokens(theme: dict) -> None:
    assert theme["base"] == "light"
    assert theme["primaryColor"] == NAVY == "#1F3A5F"
    assert theme["redColor"] == LEAK_RED == "#C8462B"
    assert theme["greenColor"] == GAIN_GREEN == "#2E7D5B"
    assert theme["backgroundColor"] == "#FFFFFF"
    assert theme["secondaryBackgroundColor"] == "#F2F4F5"
    assert theme["textColor"] == "#1B2430"


def test_only_system_fonts_arial_and_georgia_are_used(theme: dict) -> None:
    for option in ("font", "headingFont", "codeFont"):
        assert theme[option] == "Arial, Helvetica, sans-serif"
    assert "Georgia" in style.GLOBAL_CSS
    families = set(re.findall(r"font-family: ([^;!}]+)", style.GLOBAL_CSS))
    assert all(
        f.strip().split(",")[0] in {"var(--tv-sans)", "var(--tv-serif)", "var(--tv-num)"}
        for f in families
    ), families
    assert "fonts.googleapis.com" not in style.GLOBAL_CSS


def test_plotly_template_is_registered_once_and_is_the_default() -> None:
    assert pio.templates.default == visualization.TEMPLATE_NAME
    layout = pio.templates[visualization.TEMPLATE_NAME].layout
    assert layout.separators == ".,"  # English: decimal point, comma thousands
    assert layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert layout.colorway[0] == NAVY
    # Red and green are reserved for leakage and gains, so they never serve as series colours.
    assert LEAK_RED not in layout.colorway and GAIN_GREEN not in layout.colorway
    assert layout.font.family.startswith("Arial")
    assert layout.title.font.family.startswith("Georgia")


def test_bill_reconciles_and_leakage_is_the_complement_of_realization(
    waterfall_frame: pd.DataFrame,
) -> None:
    bill = portfolio_bill(waterfall_frame)
    realization = waterfall_frame["pocket_revenue"].sum() / waterfall_frame["list_revenue"].sum()
    assert bill.scope == PORTFOLIO
    assert bill.leakage_rate == pytest.approx(1 - realization)
    assert [line.label for line in bill.lines] == [
        LIST_LABEL,
        *DEDUCTION_LABELS.values(),
        NET_LABEL,
    ]
    list_line, *deductions, net = bill.lines
    assert list_line.amount - sum(line.amount for line in deductions) == pytest.approx(net.amount)
    assert net.share_of_list == pytest.approx(realization)


@pytest.mark.parametrize("segment", SEGMENT_ORDER)
def test_segment_bill_differs_from_the_portfolio(
    waterfall_frame: pd.DataFrame, segment: str
) -> None:
    bill = portfolio_bill(waterfall_frame, segment)
    assert bill.scope == segment
    assert bill.lines[-1].amount != portfolio_bill(waterfall_frame).lines[-1].amount


def test_unknown_segment_is_rejected(waterfall_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="No price waterfall rows"):
        portfolio_bill(waterfall_frame, "Unknown")


def test_bill_html_shows_displayed_amounts_that_add_up(waterfall_frame: pd.DataFrame) -> None:
    for segment in (None, *SEGMENT_ORDER):
        bill = portfolio_bill(waterfall_frame, segment)
        amounts = style.bill_display_amounts(bill)
        assert round(amounts[0] - sum(amounts[1:-1]) - amounts[-1], 2) == 0
        assert all(
            abs(shown - line.amount) < 0.02 for shown, line in zip(amounts, bill.lines, strict=True)
        )
    html = style.bill_html(portfolio_bill(waterfall_frame))
    assert "PRICE BREAKDOWN" in html and "Leakage rate:" in html
    assert 'class="bill"' in html and "bill-head" in html and "bill-foot" in html
    assert "TRY/MWh · 2025" in html
    assert 'aria-label="Price breakdown, Whole portfolio"' in html
    assert 'aria-label="percentage of list price"' in html
    assert ".bill {" in style.GLOBAL_CSS and ".bill-title" in style.GLOBAL_CSS
    assert html.count("fl--deduction") == 4 and html.count("fl--net") == 1
    assert html.count("−") == 4  # the sign of each deduction, once
    assert "\n" not in html, "blank lines or indentation would break the Markdown block"


def test_bill_waterfall_mirrors_the_bill_lines(waterfall_frame: pd.DataFrame) -> None:
    bill = portfolio_bill(waterfall_frame)
    trace = bill_waterfall_figure(bill).data[0]
    assert list(trace.y) == [line.label for line in bill.lines]
    assert trace.orientation == "h"
    assert trace.decreasing.marker.color == LEAK_RED
    assert trace.totals.marker.color == NAVY


def test_segment_waterfall_uses_bill_labels_and_semantic_colours(
    waterfall_frame: pd.DataFrame,
) -> None:
    figure = price_waterfall_figure(waterfall_frame)
    assert {trace.decreasing.marker.color for trace in figure.data} == {LEAK_RED}
    assert {trace.totals.marker.color for trace in figure.data} == {NAVY}
    assert list(figure.data[0].x)[1] == DEDUCTION_LABELS["on_invoice_discount"]


def test_trust_strip_lists_every_segment_with_the_true_value() -> None:
    table = pd.DataFrame(
        {
            "customer_segment_name": ["Industrial", "Residential"],
            "elasticity": [-0.61, -1.6],
            "ci_low": [-0.68, -1.76],
            "ci_high": [-0.53, -1.44],
            "true_elasticity": [-0.6, -1.6],
            "truth_in_ci": [True, False],
        }
    )
    html = style.trust_strip_html(table)
    assert html.index("Residential") < html.index("Industrial")
    assert "\u22121.60" in html and "\u22120.61" in html
    assert html.count("tv-trust-ok") == 1
    assert "True value is outside the interval" in html
    assert "True value is inside the interval" in html
    assert "95% interval" in html and "Estimate" in html
    # The key comes before the strip, and the estimate dot sits inside the larger diamond.
    assert html.index("tv-keys") < html.index("tv-trust-card")
    assert "True value</span>" in html and "95% confidence interval</span>" in html
    assert html.index("tv-scale-true") < html.index("tv-scale-est")
    assert "border-radius: 1px" not in style.GLOBAL_CSS


def test_callouts_escape_html(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(style.st, "markdown", lambda body, **_: captured.append(body))
    style.callout("breach", "Label", "<script>x</script>")
    style.callout("takeaway", "What it means", "text")
    assert "<script>" not in captured[0] and "&lt;script&gt;" in captured[0]
    assert "tv-callout--breach" in captured[0]
    assert 'class="tv-callout"' in captured[1]


def test_landing_answers_are_computed_from_the_data(
    analytics_db: Path, waterfall_frame: pd.DataFrame, pricing_config, synthetic_bundle
) -> None:
    from helpers import regression_frame

    from energy_market_intelligence.database import query_dataframe
    from energy_market_intelligence.elasticity import estimate_segment_elasticities

    bill = portfolio_bill(waterfall_frame)
    thesis = leakage_thesis(bill.leakage_rate)
    assert thesis.startswith(f"Of every TRY{chr(0xA0)}100 at list price, the company keeps TRY")
    assert thesis.endswith("leaks away.")
    assert ":red[" not in thesis
    assert leakage_thesis(bill.leakage_rate, highlight=True).count(":red[") == 1
    nbsp = chr(0xA0)
    assert leakage_thesis(0.148) == (
        f"Of every TRY{nbsp}100 at list price, the company keeps TRY{nbsp}85.2 and "
        f"TRY{nbsp}14.8 leaks away."
    )

    flags = query_dataframe(analytics_db, "SELECT * FROM vw_discount_policy_flags")
    answer = leakage_answer(bill, flags)
    assert (
        f"{int(flags['exceeds_policy'].sum())} combinations of province and customer segment"
        in answer
    )
    assert "pairs" not in answer
    assert "on-invoice discount" in answer  # the largest deduction of the synthetic portfolio

    summary = query_dataframe(analytics_db, "SELECT * FROM vw_pvm_bridge_summary")
    cause = bridge_answer(summary)
    assert cause.startswith("Prices rose, but costs rose faster: net revenue rose by TRY")
    assert "gross profit fell by TRY" in cause and "higher unit costs took TRY" in cause
    assert "-TRY" not in cause  # no signed money in the card answers

    elasticities = estimate_segment_elasticities(
        regression_frame(synthetic_bundle), pricing_config.true_elasticities
    )
    guard = pricing_config.recommendation
    table = recommend_prices(
        waterfall_frame,
        elasticities,
        guard.max_price_step_pct,
        guard.margin_floor_pct,
        max_volume_loss=guard.max_volume_loss_pct,
    )
    assert "gross profit could rise by TRY" in action_answer(table)
    assert re.search(r"a year \(\+\d+\.\d%\)\.$", action_answer(table))

    lines = dict(overview_takeaway(bill, waterfall_frame, table))
    assert list(lines) == ["Finding", "Size", "Action"]
    assert lines["Finding"].startswith("The largest leak is the on-invoice discount, ")
    assert f"TRY{nbsp}{round(bill.leakage_rate * 100, 1)} of every TRY{nbsp}100" in lines["Size"]
    assert re.search(r"add TRY\s\d+\.\dm of gross profit a year \(\+\d+\.\d%\)", lines["Action"])


def test_table_cells_use_english_separators_whatever_the_browser_locale() -> None:
    from dashboard_support import cell_formatter

    assert cell_formatter(2)(2.784) == "2.78"
    assert cell_formatter(0)(3180.47) == "3,180"
    assert cell_formatter(2)(-1234.5) == "\u22121,234.50"
    assert cell_formatter(2, percent=True)(0.0928) == "9.28%"
    assert cell_formatter(2, percent=True)(0.084) == "8.40%"
    assert cell_formatter(2)(float("nan")) == "–"
    assert cell_formatter(2)(None) == "–"


def test_callouts_use_a_top_rule_not_a_side_stripe() -> None:
    assert "border-left" not in style.GLOBAL_CSS


def test_unformatted_axes_get_english_months_and_thousands() -> None:
    import plotly.express as px

    frame = pd.DataFrame(
        {"month": pd.date_range("2024-01-01", periods=3, freq="MS"), "mwh": [1500, 2500, 4000]}
    )
    figure = visualization.format_axes(px.line(frame, x="month", y="mwh"))
    assert figure.layout.xaxis.tickformat == "%b %Y"  # "Jan 2025"
    assert figure.layout.yaxis.tickformat == ",~f"
    bars = visualization.format_axes(
        px.bar(x=["a", "b"], y=[0.1, 0.2]).update_yaxes(tickformat=".0%")
    )
    assert bars.layout.xaxis.tickformat is None
    assert bars.layout.yaxis.tickformat == ".0%"


def test_bridge_answer_falls_back_to_plain_effects_when_costs_did_not_win() -> None:
    summary = pd.DataFrame(
        [
            {
                "total_revenue_change": -2e6,
                "total_gp_change": 5e6,
                "gp_price_effect": 7e6,
                "gp_cost_effect": -2e6,
            }
        ]
    )
    text = bridge_answer(summary)
    assert text.startswith(
        "Net revenue fell by TRY\u00a02.0m while gross profit rose by TRY\u00a05.0m."
    )
    assert "Price changes added TRY\u00a07.0m; unit costs took TRY\u00a02.0m." in text


def test_trust_and_promotion_lines_are_computed() -> None:
    table = pd.DataFrame(
        {
            "elasticity": [-0.61, -1.58],
            "true_elasticity": [-0.6, -1.6],
        }
    )
    assert trust_note(table) == (
        "Estimated without seeing the true values; largest miss 0.02. Real data would be noisier."
    )
    estimates = pd.DataFrame(
        {
            "method": ["naive", "price_adjusted"],
            "uplift": [0.12, 0.0873],
            "true_uplift": [0.08, 0.08],
        }
    )
    assert promo_proof(estimates) == (
        "The same test works for the promotion: uplift estimated at 8.7% against a true 8.0%."
    )


def test_bill_terms_and_closing_use_the_bill_words_and_no_private_details() -> None:
    terms = style.bill_terms_html()
    for label in (*DEDUCTION_LABELS.values(), NET_LABEL, "Leakage rate"):
        assert f"<b>{label}</b>" in terms
    closing = style.closing_html()
    assert "Built by <b>Mert Can Akdoğan</b>" in closing
    assert style.GITHUB_URL in closing and style.LINKEDIN_URL in closing
    assert "@" not in closing and "tel:" not in closing


def test_takeaway_callout_accepts_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(style.st, "markdown", lambda body, **_: captured.append(body))
    style.callout("takeaway", "What it means", [("Finding", "a <b>"), ("Size", "b")])
    assert captured[0].count('class="tv-line"') == 2
    assert "<b>Finding</b> a &lt;b&gt;" in captured[0]


def test_intro_label_ends_with_a_colon(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(style.st, "markdown", lambda body, **_: captured.append(body))
    style.intro("What this page shows", "text")
    assert "<strong>What this page shows:</strong> text" in captured[0]


def test_segment_leakage_lists_each_segment_with_rate_and_net_price(
    waterfall_frame: pd.DataFrame,
) -> None:
    html = style.segment_leakage_html(waterfall_frame)
    assert [html.index(segment) for segment in SEGMENT_ORDER] == sorted(
        html.index(segment) for segment in SEGMENT_ORDER
    )
    for segment in SEGMENT_ORDER:
        bill = portfolio_bill(waterfall_frame, segment)
        assert f"{bill.leakage_rate * 100:.1f}%" in html
        assert f"{bill.lines[-1].amount:,.2f}" in html
        assert f"width:{100 * (1 - bill.leakage_rate):.1f}%" in html
    assert html.count("tv-seg-row") == len(SEGMENT_ORDER)
    assert chr(10) not in html
    assert ".tv-seg-rate" in style.GLOBAL_CSS and "var(--tv-leak)" in style.GLOBAL_CSS


def _luminance(color: str) -> float:
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _token(name: str) -> str:
    match = re.search(rf"--{name}: (#[0-9A-Fa-f]{{6}})", style.GLOBAL_CSS)
    assert match, name
    return match.group(1)


def test_labels_on_the_panel_and_the_interval_band_meet_contrast_minimums(theme: dict) -> None:
    panel = _token("tv-panel")
    for name in ("tv-slate-panel", "tv-leak-panel", "tv-navy", "tv-ink"):
        assert contrast(_token(name), panel) >= 4.5, name
    assert contrast(_token("tv-gain"), panel) >= 4.5
    assert contrast(_token("tv-band"), "#FFFFFF") >= 3.0
    # Streamlit's metric delta text sits on a pale tint of the same green.
    assert contrast(theme["greenTextColor"], "#EAF2EF") >= 4.5
    assert ".tv-callout--note .tv-label {color: var(--tv-slate-panel);}" in style.GLOBAL_CSS
    assert ".tv-callout--breach .tv-label {color: var(--tv-leak-panel);}" in style.GLOBAL_CSS


def test_links_and_controls_get_a_two_pixel_navy_focus_ring() -> None:
    css = style.GLOBAL_CSS
    for selector in (
        '[data-testid="stPageLink"] a:focus-visible',
        '[data-testid="stSidebarNav"] a:focus-visible',
        '[data-testid="stBaseButton-segmented_control"]:focus-visible',
    ):
        assert selector in css
    assert "outline: 2px solid var(--tv-navy); outline-offset: 2px;" in css


def test_section_headings_are_h2_in_the_theme(theme: dict) -> None:
    assert theme["headingFontSizes"][1] == "1.6rem"
    assert len(theme["headingFontSizes"]) == len(theme["headingFontWeights"]) == 6


def test_small_text_stays_at_the_documented_sizes() -> None:
    sizes = set(re.findall(r"font-size: ([0-9.]+)rem", style.GLOBAL_CSS))
    assert sizes <= {"0.875", "1.05", "1.1", "1.15", "1.3", "1.6", "1.9"}, sizes
    assert "font-size: 0.875rem" in style.GLOBAL_CSS.split(".fl-pct {")[1].split("}")[0]
