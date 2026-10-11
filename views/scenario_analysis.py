"""Senaryo analizi: şeffaf "ya şöyle olursa" hesabı."""

import pandas as pd
import streamlit as st

from dashboard_support import load_elasticities, load_view, note, page_intro, takeaway
from energy_market_intelligence.insights import scenario_insight
from energy_market_intelligence.localization import (
    format_number,
    format_pct,
    format_tl,
    format_volume,
    order_segments,
)
from energy_market_intelligence.scenario import (
    scenario_for_selection,
    volume_response_from_elasticity,
)

page_intro(
    "views/scenario_analysis.py",
    "Bir bölge ve ürün ailesi için fiyat veya maliyet değişirse brüt kârın ne olacağını "
    "hesaplar (baz: 2025). Bu bir tahmin değil, seçtiğiniz varsayımların aritmetik sonucudur.",
)
note(
    "Bu hesaplayıcı varsayımların aritmetik sonuçlarını gösterir; nedensel bir talep modeli "
    "değildir. Hacim tepkisi ya sizin girdiğiniz bir varsayımdır ya da tahmini esneklikten "
    "türetilir; esneklik de belirsizdir.",
    label="Varsayımlar",
)
monthly = load_view("vw_focus_profitability_monthly")
baseline = monthly[monthly["date"] > monthly["date"].max() - pd.DateOffset(months=12)]
elasticities = order_segments(load_elasticities()).set_index("customer_segment_name")
region = st.selectbox("Bölge", sorted(baseline["region_name"].unique()))
product = st.selectbox("Ürün ailesi", sorted(baseline["product_segment"].unique()))
price_change = st.slider("Fiyat değişimi (%)", -20.0, 20.0, 0.0, 0.5)
cost_change = st.slider("Birim maliyet değişimi (%)", -20.0, 20.0, 0.0, 0.5)

mode = st.radio(
    "Hacim tepkisi",
    ["Tahmini esneklik", "Elle girilen"],
    horizontal=True,
    help="Tahmini esneklik, Fiyat duyarlılığı sayfasındaki modelden gelir.",
)
if mode == "Tahmini esneklik":
    segment = st.selectbox("Müşteri segmenti (esnekliğin alındığı grup)", list(elasticities.index))
    elasticity = float(elasticities.loc[segment, "elasticity"])
    volume_response = volume_response_from_elasticity(price_change, elasticity)
    st.caption(
        f"{segment}: esneklik {format_number(elasticity, 2)} (%95 GA "
        f"{format_number(elasticities.loc[segment, 'ci_low'], 2)} / "
        f"{format_number(elasticities.loc[segment, 'ci_high'], 2)}); "
        f"fiyat {format_pct(price_change / 100, 1, signed=True)} değişirse hacim tepkisi "
        f"{format_pct(volume_response / 100, 2, signed=True)} olur."
    )
else:
    volume_response = st.slider("Beklenen hacim tepkisi (%, elle girilen)", -25.0, 25.0, 0.0, 0.5)

result = scenario_for_selection(
    baseline, region, product, price_change, volume_response, cost_change
)
cards = st.columns(4)
cards[0].metric(
    "Tahmini hacim",
    format_volume(result["scenario_volume_mwh"]),
    format_volume(result["volume_delta"], signed=True),
    help="Bu bölge ve ürün ailesi için 2025 hacmi baz alınır.",
)
cards[1].metric(
    "Tahmini ciro",
    format_tl(result["scenario_revenue"]),
    format_tl(result["revenue_delta"], signed=True),
)
cards[2].metric(
    "Tahmini brüt kâr",
    format_tl(result["scenario_gross_profit"]),
    format_tl(result["gross_profit_delta"], signed=True),
)
margin_delta = (result["scenario_gross_margin_pct"] - result["baseline_gross_margin_pct"]) * 100
cards[3].metric(
    "Tahmini brüt marj",
    format_pct(result["scenario_gross_margin_pct"]),
    f"{format_number(margin_delta, 2, signed=True)} puan",
)
takeaway(scenario_insight(result))

if mode == "Tahmini esneklik":
    st.subheader("Esnekliğin belirsizliğine duyarlılık")
    rows = []
    for label, value in (
        ("Alt sınır (daha esnek)", float(elasticities.loc[segment, "ci_low"])),
        ("Nokta tahmin", elasticity),
        ("Üst sınır (daha az esnek)", float(elasticities.loc[segment, "ci_high"])),
    ):
        response = volume_response_from_elasticity(price_change, value)
        outcome = scenario_for_selection(
            baseline, region, product, price_change, response, cost_change
        )
        rows.append(
            {
                "Esneklik": label,
                "Değer": value,
                "Hacim tepkisi (%)": response,
                "Brüt kâr değişimi (mn TL)": outcome["gross_profit_delta"] / 1e6,
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Değer": st.column_config.NumberColumn(format="%.2f"),
            "Hacim tepkisi (%)": st.column_config.NumberColumn(format="%.2f"),
            "Brüt kâr değişimi (mn TL)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

st.subheader("Hesap formülleri")
formula = pd.DataFrame(
    {
        "Ölçü": ["Hacim", "Ortalama fiyat", "Birim değişken maliyet", "Ciro", "Brüt kâr"],
        "Hesaplama": [
            "mevcut hacim x (1 + hacim tepkisi %)",
            "mevcut fiyat x (1 + fiyat değişimi %)",
            "mevcut birim maliyet x (1 + maliyet değişimi %)",
            "senaryo hacmi x senaryo fiyatı",
            "senaryo cirosu - senaryo değişken maliyeti",
        ],
    }
)
st.dataframe(formula, hide_index=True, width="stretch")
st.caption(
    "Esneklik modunda: hacim tepkisi % = ((1 + fiyat değişimi %) ^ esneklik - 1) x 100. "
    "Esneklik, fiyatlama verisinde müşteri segmenti bazında tahmin edilir ve burada seçilen "
    "bölge ve ürün ailesine aynen uygulanır."
)
