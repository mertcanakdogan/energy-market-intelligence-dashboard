"""The README headline numbers must match the committed pipeline outputs (no hand-typed drift)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

LIVE_APP_URL = "https://tavra-energy-pricing.streamlit.app"


@pytest.fixture(scope="module")
def readme(project_root: Path) -> str:
    return (project_root / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pricing(project_root: Path) -> dict:
    path = project_root / "outputs" / "examples" / "run_metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))["pricing"]


def try_amount(value: float, unit: str, decimals: int) -> str:
    return f"TRY {abs(value) / unit_scale(unit):.{decimals}f}{unit}"


def unit_scale(unit: str) -> float:
    return {"m": 1e6, "bn": 1e9}[unit]


def test_headline_numbers_match_run_metadata(readme: str, pricing: dict) -> None:
    expected = [
        f"{pricing['price_realization_pct'] * 100:.1f}%",
        f"{(1 - pricing['price_realization_pct']) * 100:.1f}%",
        try_amount(pricing["list_revenue_12m"], "bn", 2),
        try_amount(pricing["pocket_revenue_12m"], "bn", 2),
        try_amount(pricing["revenue_leakage_above_policy"], "m", 1),
        try_amount(pricing["pvm_total_revenue_change"], "m", 1),
        try_amount(pricing["pvm_gp_change"], "m", 1),
        try_amount(pricing["pvm_gp_cost_effect"], "m", 1),
        try_amount(pricing["recommended_gross_profit_change"], "m", 1),
        f"+{pricing['recommended_gross_profit_change_pct'] * 100:.1f}%",
        f"{pricing['promo_uplift']['price_adjusted']['estimate'] * 100:.1f}%",
        f"{pricing['promo_uplift']['naive']['estimate'] * 100:.1f}%",
    ]
    missing = [text for text in expected if text not in readme]
    assert not missing, f"README does not mention these pipeline numbers: {missing}"
    for segment, values in pricing["elasticity"].items():
        assert segment in readme, segment
        assert f"{values['estimate']:.2f}" in readme, segment
    assert pricing["region_segment_policy_breaches"] == 12
    assert "12 province-segment cases" in readme
    for province in pricing["breaching_regions"]:
        assert province in readme


def test_readme_states_currency_basis_and_calendar(readme: str) -> None:
    lowered = readme.lower()
    assert "constant 2025 prices" in lowered
    assert "calendar year 2025" in lowered
    assert "turkish lira (try)" in lowered


def test_readme_uses_english_currency_and_the_live_app_url(readme: str) -> None:
    assert LIVE_APP_URL in readme
    assert "tavra-enerji" not in readme
    for old in (" TL ", " TL/", "TL/MWh", "₺"):
        assert old not in readme, old
