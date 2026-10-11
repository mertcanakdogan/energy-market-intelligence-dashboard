"""The README headline numbers must match the committed pipeline outputs (no hand-typed drift)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from energy_market_intelligence.localization import format_number


@pytest.fixture(scope="module")
def readme(project_root: Path) -> str:
    return (project_root / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pricing(project_root: Path) -> dict:
    path = project_root / "outputs" / "examples" / "run_metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))["pricing"]


def english(value: float, unit: str, decimals: int) -> str:
    return f"TL {abs(value) / unit_scale(unit):.{decimals}f}{unit}"


def unit_scale(unit: str) -> float:
    return {"m": 1e6, "bn": 1e9}[unit]


def test_english_headline_numbers_match_run_metadata(readme: str, pricing: dict) -> None:
    expected = [
        f"{pricing['price_realization_pct'] * 100:.1f}%",
        english(pricing["list_revenue_12m"], "bn", 2),
        english(pricing["pocket_revenue_12m"], "bn", 2),
        english(pricing["revenue_leakage_above_policy"], "m", 1),
        english(pricing["pvm_total_revenue_change"], "m", 1),
        english(pricing["pvm_gp_change"], "m", 1),
        english(pricing["pvm_gp_cost_effect"], "m", 1),
        english(pricing["recommended_gross_profit_change"], "m", 1),
        f"+{pricing['recommended_gross_profit_change_pct'] * 100:.1f}%",
        f"{pricing['promo_uplift']['price_adjusted']['estimate'] * 100:.1f}%",
        f"{pricing['promo_uplift']['naive']['estimate'] * 100:.1f}%",
    ]
    missing = [text for text in expected if text not in readme]
    assert not missing, f"README does not mention these pipeline numbers: {missing}"
    for segment, values in pricing["elasticity"].items():
        assert f"{values['estimate']:.2f}" in readme, segment
    assert pricing["region_segment_policy_breaches"] == 12
    assert "12 region-segment cases" in readme
    for region in pricing["breaching_regions"]:
        assert region in readme


def test_turkish_summary_uses_turkish_number_format_and_matches(readme: str, pricing: dict) -> None:
    summary = readme.split("## Türkçe özet", 1)[1].split("## Key terms", 1)[0]
    expected = [
        format_number(pricing["price_realization_pct"] * 100, 1),
        format_number(pricing["revenue_leakage_above_policy"] / 1e6, 1),
        format_number(pricing["pvm_total_revenue_change"] / 1e6, 1),
        format_number(abs(pricing["pvm_gp_change"]) / 1e6, 1),
        format_number(abs(pricing["pvm_gp_cost_effect"]) / 1e6, 1),
        format_number(pricing["recommended_gross_profit_change"] / 1e6, 1),
        format_number(pricing["recommended_gross_profit_change_pct"] * 100, 1),
    ]
    missing = [text for text in expected if text not in summary]
    assert not missing, f"Türkçe özet is missing: {missing}"
    lines = [line for line in summary.splitlines() if line.strip()]
    assert 5 <= len(lines) <= 8 + 1


def test_readme_states_currency_basis_and_calendar(readme: str) -> None:
    lowered = readme.lower()
    assert "constant 2025 prices" in lowered
    assert "calendar year 2025" in lowered
    assert "sabit 2025 fiyatlarıyla" in lowered
