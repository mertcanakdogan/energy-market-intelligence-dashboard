"""Landing page: the question, four headline numbers, the findings and a glossary."""

import streamlit as st

from dashboard_support import (
    PAGE_SPECS,
    load_elasticities,
    load_pricing_config,
    load_promotion_results,
    load_view,
)
from energy_market_intelligence.insights import (
    elasticity_insight,
    price_waterfall_insight,
    promo_insight,
    pvm_insight,
    recommendation_insight,
)
from energy_market_intelligence.localization import format_pct, format_tl
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY

st.title(f"{FOCUS_COMPANY}: Fiyatlama ve Gelir Analitiği")
st.subheader("Fiyatları nerede değiştirmeliyiz ve bunun değeri nedir?")
st.write(
    f"Bu, kurgusal bir elektrik perakende şirketi ({FOCUS_COMPANY}) üzerine hazırlanmış bir "
    "vaka çalışmasıdır. **Tüm veriler sentetiktir; şirket ve bölge adları kurgusaldır.** "
    "Tutarlar Türk lirasıyla ve **sabit 2025 fiyatlarıyla** (enflasyondan arındırılmış) "
    "gösterilir. Veriler bilinen gerçek değerlerle üretildiği için her tahmin doğru cevapla "
    "karşılaştırılabilir."
)

waterfall = load_view("vw_price_waterfall")
flags = load_view("vw_discount_policy_flags")
pvm_summary = load_view("vw_pvm_bridge_summary")
pvm = pvm_summary.iloc[0]
elasticities = load_elasticities()
promo, _trend = load_promotion_results()
guard = load_pricing_config().recommendation
recommendation = recommend_prices(
    waterfall,
    elasticities,
    guard.max_price_step_pct,
    guard.margin_floor_pct,
    max_volume_loss=guard.max_volume_loss_pct,
)

realization = waterfall["pocket_revenue"].sum() / waterfall["list_revenue"].sum()
cards = st.columns(4)
cards[0].metric(
    "Fiyat gerçekleşme oranı",
    format_pct(realization),
    help="Liste fiyatlı cironun yüzde kaçı gerçekten cebe kalıyor (indirimler, iskontolar, "
    "vade ve servis maliyetleri düşüldükten sonra). 2025 verisi.",
)
cards[1].metric(
    "Politika üstü indirim",
    format_tl(flags["revenue_leakage_above_policy"].sum()),
    f"{int(flags['exceeds_policy'].sum())} bölge-segment çifti",
    delta_color="off",
    help="İzin verilen indirim sınırının üstünde verilen indirimin yıllık tutarı.",
)
cards[2].metric(
    "Brüt kâr değişimi",
    format_tl(pvm["total_gp_change"], signed=True),
    "2025, 2024'e göre",
    delta_color="off",
    help="Brüt kâr = net ciro - değişken enerji maliyeti. Son 12 ay ile önceki 12 ayın farkı.",
)
cards[3].metric(
    "Esneklik tahmin doğruluğu",
    f"{int(elasticities['truth_in_ci'].sum())} / {len(elasticities)} segment",
    "gerçek değer güven aralığında",
    delta_color="off",
    help="Veri sentetik olduğu için gerçek esneklikler biliniyor; tahmin aralıkları bunları "
    "yakalıyor mu?",
)

st.markdown("### Üç bulgu ve bir öneri")
st.markdown(
    f"1. **Liste fiyatın bir kısmı cebe kalmıyor.** {price_waterfall_insight(waterfall, flags)}\n"
    f"2. **Ciro arttı ama kâr artmadı.** {pvm_insight(pvm_summary)}\n"
    f"3. **Müşteri grupları fiyata farklı tepki veriyor.** {elasticity_insight(elasticities)} "
    f"{promo_insight(promo)}\n\n"
    f"**Öneri.** {recommendation_insight(recommendation)}"
)

st.markdown("### Sayfalar")
left, right = st.columns(2)
for column, section in ((left, "Fiyatlama / Pricing"), (right, "Pazar / Market")):
    with column:
        st.markdown(f"**{section}**")
        for page_section, path, title, icon, _url in PAGE_SPECS:
            if page_section == section:
                st.page_link(path, label=title, icon=icon)

with st.expander("Terimler sözlüğü (bu sayfalarda geçen kavramlar)"):
    st.markdown(
        """
- **Liste fiyat:** Fiyat listesinde yazan birim fiyat (TL/MWh).
- **Cebe kalan fiyat (pocket price):** Liste fiyattan tüm indirimler, iskontolar, vade ve servis
  maliyeti düşüldükten sonra şirketin gerçekte eline geçen birim fiyat.
- **Fiyat şelalesi:** Liste fiyattan cebe kalan fiyata adım adım inişi gösteren grafik.
- **Fiyat gerçekleşme oranı:** Cebe kalan ciro / liste fiyatlı ciro.
- **Politika üstü indirim:** Bir segment için izin verilen indirim sınırını aşan kısım.
- **PVM köprüsü (fiyat-hacim-karışım):** Ciro veya kârdaki değişimi fiyat, satılan hacim, ürün ve
  müşteri karışımı ile maliyet etkisine ayıran analiz.
- **Fiyat esnekliği:** Fiyat %1 artınca hacmin yüzde kaç değiştiği. -1,6 ise %1 zam hacmi yaklaşık
  %1,6 düşürür. -1'den küçükse (örneğin -1,6) talep *esnek*, -1'den büyükse (örneğin -0,6)
  talep *esnek değil*, yani fiyata az duyarlıdır.
- **Farkların farkı (DiD):** Kampanya yapılan bölgelerin, kampanya yapılmayan bölgelere göre
  ek değişimini ölçerek kampanyanın gerçek etkisini ayıklayan yöntem.
- **Güven aralığı (GA):** Tahminin makul olarak yer alabileceği aralık; %95 GA geniş ise
  tahmin belirsizdir.
- **Brüt kâr / brüt marj:** Net ciro eksi enerji (değişken) maliyeti; marj bunun ciroya oranı.
- **Sabit 2025 fiyatları:** Tüm TL tutarlar enflasyondan arındırılmıştır; yıllar arası
  karşılaştırmada fiyat düzeyi etkisi yoktur.
- **MWh / GWh / TWh:** Megawatt-saat; 1 GWh = 1.000 MWh, 1 TWh = 1.000 GWh.
- **PTF, YEK-G:** PTF piyasa takas fiyatı (toptan elektrik fiyatı); YEK-G yenilenebilir enerji
  kaynak garantisi belgesidir.
        """
    )

st.info(
    "Bu uygulamadaki tüm veriler ve iş mantığı kamuya açık bir gösterim için yeniden "
    "tasarlanmıştır. Uygulama otomatik ticari karar vermez.",
    icon=":material/info:",
)
