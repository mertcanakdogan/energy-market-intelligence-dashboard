"""Kampanya etkisi: farkların farkı yöntemi."""

import streamlit as st

from dashboard_support import (
    load_pricing_config,
    load_promotion_results,
    page_intro,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import promo_insight
from energy_market_intelligence.localization import format_pct
from energy_market_intelligence.pricing_visualization import promo_did_figure

page_intro(
    "Kampanya Etkisi",
    "İndirim kampanyasının gerçekte ne kadar ek hacim yarattığını, kampanya yapılan ve "
    "yapılmayan bölgeleri karşılaştırarak (farkların farkı, DiD) ölçer. Kampanya: "
    "Ocak-Nisan 2025.",
)
estimates, trend = load_promotion_results()
promo = load_pricing_config().promotion
by_method = estimates.set_index("method")
adjusted = by_method.loc["price_adjusted"]
naive = by_method.loc["naive"]

cards = st.columns(3)
cards[0].metric(
    "Fiyat düzeltmeli etki",
    format_pct(adjusted["uplift"]),
    f"%95 GA: {format_pct(adjusted['ci_low'])} / {format_pct(adjusted['ci_high'])}",
    delta_color="off",
    help="Kampanya indiriminin ve liste fiyat farklarının etkisi çıkarıldıktan sonra kalan "
    "ek hacim.",
)
cards[1].metric(
    "Basit karşılaştırma",
    format_pct(naive["uplift"]),
    help="Önce/sonra ve kampanyalı/kampanyasız farkı; fiyat etkisini de içerdiği için şişkindir.",
)
cards[2].metric(
    "Gerçek etki (veri üreticisi)",
    format_pct(adjusted["true_uplift"]),
    help="Sentetik veride kullanılan gerçek ek hacim etkisi.",
)
takeaway(promo_insight(estimates))

st.plotly_chart(
    promo_did_figure(estimates, trend, (promo.start_month_id, promo.end_month_id)),
    width="stretch",
)
st.write(
    f"Kampanya bölgesi: {adjusted['treated_regions']}; kontrol bölgesi: "
    f"{adjusted['control_regions']}; kampanya ayları: {promo.start_month_id}-{promo.end_month_id} "
    "(Ocak-Nisan 2025). Basit tahmin, kampanya indiriminin ve liste fiyat artışlarının hacme "
    "yaptığı etkiyi de saydığı için kampanyanın ek etkisini olduğundan yüksek gösterir."
)
show_table(
    estimates[
        [
            "method",
            "uplift",
            "ci_low",
            "ci_high",
            "true_uplift",
            "abs_error",
            "truth_in_ci",
            "treated_regions",
            "control_regions",
        ]
    ],
    fractions={"uplift", "ci_low", "ci_high", "true_uplift", "abs_error"},
)
with st.expander("Yöntem ve varsayımlar"):
    st.markdown(
        """
- Öncesi: kampanyadan önceki aylar. Sonrası: kampanya ayları. Sonraki aylar dışarıda bırakılır.
- Fiyat düzeltmeli model: iki yönlü sabit etkiler (bölge x ürün x segment ve ay), segmente özel
  cebe kalan fiyat eğimi ve rakip fiyatı; standart hatalar bölge bazında kümelenmiştir.
- Temel varsayım: kampanya olmasaydı, fiyat hesaba katıldığında kampanya ve kontrol bölgeleri
  paralel seyredecekti. Bölgeler rastgele değil veri üreticisi tarafından seçildiği için bu
  varsayım gerçek veride mutlaka kontrol edilmelidir.
        """
    )
