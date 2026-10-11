"""Design system: tokens, Plotly template, fatura dökümü and the landing-page answers."""

from __future__ import annotations

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
)
from energy_market_intelligence.localization import (
    SEGMENT_ORDER,
    accusative_suffix,
    format_pct_accusative,
)
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


def test_fonts_are_loaded_through_the_native_theme_options(theme: dict) -> None:
    assert theme["font"].startswith("'Source Sans 3':https://fonts.googleapis.com/")
    assert theme["headingFont"].startswith("'Barlow Semi Condensed':https://fonts.googleapis.com/")
    assert theme["codeFont"].startswith("'IBM Plex Mono':https://fonts.googleapis.com/")


def test_plotly_template_is_registered_once_and_is_the_default() -> None:
    assert pio.templates.default == visualization.TEMPLATE_NAME
    layout = pio.templates[visualization.TEMPLATE_NAME].layout
    assert layout.separators == ",."
    assert layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert layout.colorway[0] == NAVY
    # Red and green are reserved for leakage and gains, so they never serve as series colours.
    assert LEAK_RED not in layout.colorway and GAIN_GREEN not in layout.colorway
    assert "Source Sans 3" in layout.font.family


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
        portfolio_bill(waterfall_frame, "Yok")


def test_bill_html_shows_displayed_amounts_that_add_up(waterfall_frame: pd.DataFrame) -> None:
    for segment in (None, *SEGMENT_ORDER):
        bill = portfolio_bill(waterfall_frame, segment)
        amounts = style.bill_display_amounts(bill)
        assert round(amounts[0] - sum(amounts[1:-1]) - amounts[-1], 2) == 0
        assert all(
            abs(shown - line.amount) < 0.02 for shown, line in zip(amounts, bill.lines, strict=True)
        )
    html = style.bill_html(portfolio_bill(waterfall_frame))
    assert "FATURA DÖKÜMÜ" in html and "Kaçak oranı:" in html
    assert html.count("fl--deduction") == 4 and html.count("fl--net") == 1
    assert html.count("−") >= 8  # operator and sign of each deduction
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
            "customer_segment_name": ["Sanayi", "Mesken"],
            "elasticity": [-0.61, -1.6],
            "ci_low": [-0.68, -1.76],
            "ci_high": [-0.53, -1.44],
            "true_elasticity": [-0.6, -1.6],
            "truth_in_ci": [True, False],
        }
    )
    html = style.trust_strip_html(table)
    assert html.index("Mesken") < html.index("Sanayi")
    assert "-1,60" in html and "-0,61" in html
    assert html.count("tv-trust-ok") == 1
    assert "aralığın dışında" in html


def test_callouts_escape_html(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(style.st, "markdown", lambda body, **_: captured.append(body))
    style.callout("breach", "Etiket", "<script>x</script>")
    style.callout("takeaway", "Ne anlama geliyor?", "metin")
    assert "<script>" not in captured[0] and "&lt;script&gt;" in captured[0]
    assert "tv-callout--breach" in captured[0]
    assert 'class="tv-callout"' in captured[1]


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [
        (0.148, "%14,8'i"),
        (0.142, "%14,2'yi"),
        (0.143, "%14,3'ü"),
        (0.146, "%14,6'yı"),
        (0.149, "%14,9'u"),
        (0.10, "%10,0'ı"),
    ],
)
def test_percent_gets_the_right_turkish_suffix(fraction: float, expected: str) -> None:
    assert format_pct_accusative(fraction) == expected


@pytest.mark.parametrize(
    ("number", "suffix"),
    [("10", "u"), ("20", "i"), ("40", "ı"), ("100", "ü"), ("90", "ı"), ("7", "yi"), ("", "i")],
)
def test_round_numbers_use_the_tens_word(number: str, suffix: str) -> None:
    assert accusative_suffix(number) == suffix


def test_landing_answers_are_computed_from_the_data(
    analytics_db: Path, waterfall_frame: pd.DataFrame, pricing_config, synthetic_bundle
) -> None:
    from helpers import regression_frame

    from energy_market_intelligence.database import query_dataframe
    from energy_market_intelligence.elasticity import estimate_segment_elasticities

    bill = portfolio_bill(waterfall_frame)
    thesis = leakage_thesis(bill.leakage_rate)
    assert thesis.startswith("Liste fiyatının %") and thesis.endswith("kayboluyor.")
    assert leakage_thesis(bill.leakage_rate, highlight=True).count(":red[") == 1

    flags = query_dataframe(analytics_db, "SELECT * FROM vw_discount_policy_flags")
    answer = leakage_answer(bill, flags)
    assert f"{int(flags['exceeds_policy'].sum())} bölge-segment çifti" in answer
    assert "fatura içi iskonto" in answer  # the largest deduction of the synthetic portfolio

    summary = query_dataframe(analytics_db, "SELECT * FROM vw_pvm_bridge_summary")
    assert "Net ciro" in bridge_answer(summary) and "birim maliyet" in bridge_answer(summary)

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
    assert "brüt kâr yılda" in action_answer(table)
