"""Turkish display conventions shared by charts, the Streamlit app and the pipeline outputs.

Convention used throughout the project:

* Entity names in the data are already Turkish and fictional (companies, regions, products and
  customer segments). English glosses live in ``dim_customer_segment.customer_segment_en`` and in
  the README glossary.
* Enumerated codes produced by SQL or the estimators (for example ``Gaining`` or ``elastic``) stay
  in English in the data and are translated here at display time.
* All money is in Turkish lira at constant (real) 2025 prices. Numbers are formatted the Turkish
  way: ``.`` groups thousands and ``,`` marks decimals (``3.100 TL``, ``%85,2``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import pandas as pd

CURRENCY = "TL"
PRICE_BASIS = "sabit 2025 fiyatlarıyla"

# Display order of the customer segments (the order of ``pricing.segments`` in the config).
SEGMENT_ORDER = ("Mesken", "Ticarethane / KOBİ", "Sanayi")
SEGMENT_GLOSS = {
    "Mesken": "Residential",
    "Ticarethane / KOBİ": "SME",
    "Sanayi": "Industrial",
}
SEGMENT_PLAIN = {
    "Mesken": "konutlar",
    "Ticarethane / KOBİ": "küçük ve orta ölçekli işletmeler",
    "Sanayi": "sanayi tesisleri",
}

MISSING = "–"


def format_number(value: float, decimals: int = 0, *, signed: bool = False) -> str:
    """Format ``value`` with Turkish separators, e.g. ``1.234,5``."""

    if value is None or not math.isfinite(value):
        return MISSING
    value = round(float(value), decimals)
    if value == 0:
        value = 0.0
    text = f"{abs(value):,.{decimals}f}".translate(str.maketrans(",.", ".,"))
    if value < 0:
        return f"-{text}"
    return f"+{text}" if signed and value > 0 else text


def format_pct(fraction: float, decimals: int = 1, *, signed: bool = False) -> str:
    """Format a fraction in the Turkish way: ``0.852`` becomes ``%85,2``, ``0.043`` ``+%4,3``."""

    if fraction is None or not math.isfinite(fraction):
        return MISSING
    text = format_number(fraction * 100, decimals, signed=signed)
    sign = text[0] if text[0] in "+-" else ""
    return f"{sign}%{text[len(sign) :]}"


def format_pp(value: float, decimals: int = 2) -> str:
    """Format a change in percentage points: ``+0,55 puan``."""

    return f"{format_number(value, decimals, signed=True)} puan"


def format_tl(value: float, *, signed: bool = False) -> str:
    """Compact money amount: ``4,54 mlr TL``, ``21,4 mn TL``, ``128 bin TL`` or ``950 TL``."""

    if value is None or not math.isfinite(value):
        return MISSING
    magnitude = abs(value)
    if magnitude >= 1e9:
        scaled, decimals, unit = value / 1e9, 2, "mlr TL"
    elif magnitude >= 1e6:
        scaled = value / 1e6
        decimals, unit = (1 if abs(scaled) >= 10 else 2), "mn TL"
    elif magnitude >= 1e3:
        scaled = value / 1e3
        decimals, unit = (0 if abs(scaled) >= 100 else 1), "bin TL"
    else:
        scaled, decimals, unit = value, 0, "TL"
    return f"{format_number(scaled, decimals, signed=signed)} {unit}"


def format_tl_per_mwh(value: float, decimals: int = 0, *, signed: bool = False) -> str:
    """Unit price: ``3.100 TL/MWh``."""

    return f"{format_number(value, decimals, signed=signed)} TL/MWh"


def format_volume(mwh: float, *, signed: bool = False) -> str:
    """Energy volume with an energy-natural unit: ``1,45 TWh``, ``820 GWh`` or ``950 MWh``."""

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
    "region_name": "Bölge",
    "product_name": "Ürün",
    "customer_segment_name": "Müşteri segmenti",
    "company_name": "Şirket",
    "product_segment": "Ürün ailesi",
    "date": "Ay",
    "month_id": "Ay no",
    "volume_mwh": "Hacim (MWh)",
    "baseline_volume_mwh": "Mevcut hacim (MWh)",
    "list_price": "Liste fiyat (TL/MWh)",
    "pocket_price": "Cebe kalan fiyat (TL/MWh)",
    "current_pocket_price": "Mevcut cebe kalan fiyat (TL/MWh)",
    "recommended_pocket_price": "Önerilen cebe kalan fiyat (TL/MWh)",
    "unit_variable_cost": "Birim maliyet (TL/MWh)",
    "list_revenue": "Liste fiyatlı ciro (TL)",
    "pocket_revenue": "Cebe kalan ciro (TL)",
    "gross_profit": "Brüt kâr (TL)",
    "revenue": "Ciro (TL)",
    "on_invoice_discount_pct": "Fatura üstü indirim (liste fiyatın %'si)",
    "policy_max_discount_pct": "Politika üst sınırı",
    "excess_discount_pp": "Sınır aşımı (puan)",
    "revenue_leakage_above_policy": "Politika üstü indirim (TL)",
    "exceeds_policy": "Sınırı aşıyor mu?",
    "pocket_margin_pct": "Cep marjı",
    "current_margin_pct": "Mevcut marj",
    "new_margin_pct": "Yeni marj",
    "prior_volume": "Önceki yıl hacmi (MWh)",
    "current_volume": "Son yıl hacmi (MWh)",
    "prior_price": "Önceki yıl fiyatı (TL/MWh)",
    "current_price": "Son yıl fiyatı (TL/MWh)",
    "volume_effect": "Hacim etkisi (TL)",
    "mix_effect": "Karışım etkisi (TL)",
    "price_effect": "Fiyat etkisi (TL)",
    "total_revenue_change": "Ciro değişimi (TL)",
    "gp_cost_effect": "Maliyet etkisi (TL)",
    "total_gp_change": "Brüt kâr değişimi (TL)",
    "reconciliation_gap": "Mutabakat farkı (TL)",
    "elasticity": "Esneklik",
    "std_error": "Standart hata",
    "ci_low": "%95 GA alt",
    "ci_high": "%95 GA üst",
    "true_elasticity": "Gerçek esneklik",
    "abs_error": "Mutlak hata",
    "truth_in_ci": "Gerçek değer aralıkta mı?",
    "cross_elasticity": "Rakip fiyat esnekliği",
    "classification": "Sınıf",
    "n_obs": "Gözlem sayısı",
    "method": "Yöntem",
    "uplift": "Tahmin edilen etki",
    "true_uplift": "Gerçek etki",
    "std_error_log": "Standart hata (log)",
    "treated_regions": "Kampanya bölgesi sayısı",
    "control_regions": "Kontrol bölgesi sayısı",
    "price_change_pct": "Fiyat değişimi",
    "expected_volume_change_pct": "Beklenen hacim değişimi",
    "expected_gross_profit_change": "Beklenen brüt kâr değişimi (TL)",
    "gross_profit_change_low": "Brüt kâr değişimi, alt sınır (TL)",
    "gross_profit_change_high": "Brüt kâr değişimi, üst sınır (TL)",
    "baseline_gross_profit": "Mevcut brüt kâr (TL)",
    "binding_constraint": "Belirleyen kural",
    "momentum_rank": "Sıra",
    "current_share": "Güncel pay",
    "prior_share": "Önceki pay",
    "share_change_pp": "Pay değişimi (puan)",
    "momentum_signal": "Eğilim",
    "company_rank": "Bölgedeki sıra",
    "market_share": "Pazar payı",
    "hhi": "HHI (yoğunlaşma)",
    "concentration_classification": "Yoğunlaşma düzeyi",
    "opportunity_rank": "Sıra",
    "opportunity_score": "Fırsat skoru",
    "market_growth": "Pazar büyümesi (yıllık)",
    "focus_share": "Şirket payı",
    "share_momentum": "Pay eğilimi",
    "gross_margin_pct": "Brüt marj",
    "market_volume": "Pazar hacmi (MWh)",
    "market_volume_mwh": "Pazar hacmi (MWh)",
    "focus_volume_mwh": "Şirket hacmi (MWh)",
    "focus_market_share": "Şirket payı",
    "market_size_score": "Pazar büyüklüğü skoru",
    "market_growth_score": "Büyüme skoru",
    "share_gap_score": "Pay boşluğu skoru",
    "momentum_score": "Eğilim skoru",
    "margin_score": "Marj skoru",
    "competition_score": "Rekabet skoru",
    "variable_cost": "Değişken maliyet (TL)",
}

VALUE_LABELS: dict[str, str] = {
    # estimators
    "elastic": "Esnek (fiyata duyarlı)",
    "inelastic": "Esnek değil (fiyata az duyarlı)",
    "naive": "Basit karşılaştırma",
    "price_adjusted": "Fiyat düzeltmeli",
    # SQL classifications
    "Gaining": "Pay kazanıyor",
    "Losing": "Pay kaybediyor",
    "Stable": "Sabit",
    "Fragmented": "Dağınık",
    "Moderately concentrated": "Orta yoğunlaşmış",
    "Concentrated": "Yoğunlaşmış",
    # price recommendation rules
    "step cap": "Adım sınırı",
    "volume-loss guard": "Hacim kaybı sınırı",
    "profit-maximising price": "Kârı en çok artıran fiyat",
    "inelastic demand: raise to the step cap": "Esnek olmayan talep: adım sınırına kadar artır",
    "margin floor": "Marj tabanı",
    "margin floor (not reachable in one step)": "Marj tabanına tek adımda ulaşılamıyor",
    # booleans
    "True": "Evet",
    "False": "Hayır",
}


def translate_value(value: object) -> object:
    """Translate one enumerated code (booleans included); unknown values pass through."""

    return VALUE_LABELS.get(str(value), value)


def localize_frame(frame: pd.DataFrame, *, translate_values: bool = True) -> pd.DataFrame:
    """Return a display copy with Turkish column headers and translated enumerated codes."""

    result = frame.copy()
    if translate_values:
        for column in result.columns:
            series = result[column]
            if pd.api.types.is_bool_dtype(series) or pd.api.types.is_object_dtype(series):
                result[column] = series.map(translate_value)
    return result.rename(columns=COLUMN_LABELS)


def order_segments(frame: pd.DataFrame, column: str = "customer_segment_name") -> pd.DataFrame:
    """Sort rows into the display order Mesken, Ticarethane / KOBİ, Sanayi."""

    rank = {name: position for position, name in enumerate(SEGMENT_ORDER)}
    order = frame[column].map(rank).fillna(len(rank))
    return frame.assign(_order=order).sort_values("_order", kind="stable").drop(columns="_order")


def segment_with_gloss(name: str) -> str:
    """``Mesken (Residential)``: used where a bilingual label is helpful."""

    gloss = SEGMENT_GLOSS.get(name)
    return f"{name} ({gloss})" if gloss else name


def label_map(mapping: Mapping[str, str], keys: list[str]) -> dict[str, str]:
    """Subset of ``mapping`` for the given keys (used for chart axis labels)."""

    return {key: mapping[key] for key in keys if key in mapping}
