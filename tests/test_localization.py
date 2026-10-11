from __future__ import annotations

import math

import pandas as pd
import pytest

from energy_market_intelligence.localization import (
    SEGMENT_ORDER,
    format_number,
    format_pct,
    format_pp,
    format_tl,
    format_tl_per_mwh,
    format_volume,
    localize_frame,
    order_segments,
    segment_with_gloss,
    translate_value,
)


@pytest.mark.parametrize(
    ("value", "decimals", "expected"),
    [
        (1234.5, 1, "1.234,5"),
        (3100, 0, "3.100"),
        (-0.04, 1, "0,0"),
        (-1.6, 2, "-1,60"),
        (1_234_567.891, 2, "1.234.567,89"),
        (0, 0, "0"),
    ],
)
def test_format_number_uses_turkish_separators(value: float, decimals: int, expected: str) -> None:
    assert format_number(value, decimals) == expected


def test_signed_numbers_and_missing_values() -> None:
    assert format_number(4.3, 1, signed=True) == "+4,3"
    assert format_number(-4.2, 1, signed=True) == "-4,2"
    assert format_number(0.0, 1, signed=True) == "0,0"
    assert format_number(math.nan) == "–"
    assert format_pct(math.nan) == "–"
    assert format_tl(math.inf) == "–"
    assert format_volume(math.nan) == "–"


def test_percent_has_the_turkish_prefix_form() -> None:
    assert format_pct(0.852) == "%85,2"
    assert format_pct(0.043, 1, signed=True) == "+%4,3"
    assert format_pct(-0.044, 1) == "-%4,4"
    assert format_pct(0.08, 0) == "%8"
    assert format_pp(0.5) == "+0,50 puan"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (4_540_000_000, "4,54 mlr TL"),
        (23_435_358, "23,4 mn TL"),
        (540_000, "540 bin TL"),
        (5_400_000, "5,40 mn TL"),
        (12_800, "12,8 bin TL"),
        (950, "950 TL"),
        (-36_340_165, "-36,3 mn TL"),
    ],
)
def test_compact_tl(value: float, expected: str) -> None:
    assert format_tl(value) == expected


def test_tl_signed_price_and_volume_units() -> None:
    assert format_tl(57_863_249, signed=True) == "+57,9 mn TL"
    assert format_tl_per_mwh(3099.6) == "3.100 TL/MWh"
    assert format_volume(1_454_730) == "1,45 TWh"
    assert format_volume(820_000) == "820 GWh"
    assert format_volume(12_300) == "12,3 GWh"
    assert format_volume(950) == "950 MWh"
    assert format_volume(-1_200_000, signed=True) == "-1,20 TWh"


def test_translate_and_localize_frame() -> None:
    assert translate_value("Gaining") == "Pay kazanıyor"
    assert translate_value(True) == "Evet"
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
    assert list(shown.columns) == ["Bölge", "Eğilim", "Sınırı aşıyor mu?", "Esneklik"]
    assert shown.iloc[0].tolist() == ["Ankara", "Pay kazanıyor", "Evet", -1.6]
    raw = localize_frame(frame, translate_values=False)
    assert raw.iloc[0]["Eğilim"] == "Gaining"


def test_segments_are_ordered_and_glossed() -> None:
    frame = pd.DataFrame({"customer_segment_name": ["Sanayi", "Mesken", "Ticarethane / KOBİ", "x"]})
    ordered = order_segments(frame)["customer_segment_name"].tolist()
    assert ordered == [*SEGMENT_ORDER, "x"]
    assert segment_with_gloss("Mesken") == "Mesken (Residential)"
    assert segment_with_gloss("Başka") == "Başka"
