from __future__ import annotations

import math

import pandas as pd
import pytest

from energy_market_intelligence.localization import (
    SEGMENT_ORDER,
    format_number,
    format_pct,
    format_pp,
    format_try,
    format_try_per_mwh,
    format_volume,
    localize_frame,
    order_segments,
    translate_value,
)


@pytest.mark.parametrize(
    ("value", "decimals", "expected"),
    [
        (1234.5, 1, "1,234.5"),
        (3100, 0, "3,100"),
        (3732.61, 2, "3,732.61"),
        (-0.04, 1, "0.0"),
        (-1.6, 2, "\u22121.60"),
        (1_234_567.891, 2, "1,234,567.89"),
        (0, 0, "0"),
    ],
)
def test_format_number_uses_english_separators(value: float, decimals: int, expected: str) -> None:
    assert format_number(value, decimals) == expected


def test_signed_numbers_and_missing_values() -> None:
    assert format_number(4.3, 1, signed=True) == "+4.3"
    assert format_number(-4.2, 1, signed=True) == "\u22124.2"
    assert format_number(0.0, 1, signed=True) == "0.0"
    assert format_number(math.nan) == "–"
    assert format_pct(math.nan) == "–"
    assert format_try(math.inf) == "–"
    assert format_volume(math.nan) == "–"


def test_percent_follows_the_number() -> None:
    assert format_pct(0.852) == "85.2%"
    assert format_pct(0.148) == "14.8%"
    assert format_pct(0.043, 1, signed=True) == "+4.3%"
    assert format_pct(-0.044, 1) == "\u22124.4%"
    assert format_pct(0.08, 0) == "8%"
    assert format_pp(0.5) == "+0.50 pp"
    assert format_pp(-0.554) == "\u22120.55 pp"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (4_540_000_000, "TRY\u00a04.54bn"),
        (4_690_000_000, "TRY\u00a04.69bn"),
        (23_435_358, "TRY\u00a023.4m"),
        (540_000, "TRY\u00a0540k"),
        (5_400_000, "TRY\u00a05.4m"),
        (12_800, "TRY\u00a012.8k"),
        (950, "TRY\u00a0950"),
        (-36_340_165, "\u2212TRY\u00a036.3m"),
    ],
)
def test_compact_try(value: float, expected: str) -> None:
    assert format_try(value) == expected


def test_try_signed_price_and_volume_units() -> None:
    assert format_try(57_863_249, signed=True) == "+TRY\u00a057.9m"
    assert format_try(-1_300, signed=True) == "\u2212TRY\u00a01.3k"
    assert format_try_per_mwh(3099.6) == "3,100 TRY/MWh"
    assert format_try_per_mwh(3099.6, 1) == "3,099.6 TRY/MWh"
    assert format_volume(1_454_730) == "1.45 TWh"
    assert format_volume(820_000) == "820 GWh"
    assert format_volume(12_300) == "12.3 GWh"
    assert format_volume(950) == "950 MWh"
    assert format_volume(-1_200_000, signed=True) == "\u22121.20 TWh"


def test_translate_and_localize_frame() -> None:
    assert translate_value("Gaining") == "Gaining share"
    assert translate_value(True) == "Yes"
    assert translate_value("unknown code") == "unknown code"
    frame = pd.DataFrame(
        {
            "region_name": ["Ankara"],
            "momentum_signal": ["Gaining"],
            "exceeds_policy": [True],
            "elasticity": [-1.6],
        }
    )
    shown = localize_frame(frame)
    assert list(shown.columns) == ["Province", "Trend", "Above the limit?", "Elasticity"]
    assert shown.iloc[0].tolist() == ["Ankara", "Gaining share", "Yes", -1.6]
    raw = localize_frame(frame, translate_values=False)
    assert raw.iloc[0]["Trend"] == "Gaining"


def test_segments_are_ordered() -> None:
    frame = pd.DataFrame(
        {"customer_segment_name": ["Industrial", "Residential", "Commercial (SME)", "x"]}
    )
    ordered = order_segments(frame)["customer_segment_name"].tolist()
    assert ordered == [*SEGMENT_ORDER, "x"]
