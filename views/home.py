"""Landing page: the thesis, the fatura dökümü, three questions and the proof the model works."""

import streamlit as st

import dashboard_style as style
from dashboard_support import (
    load_elasticities,
    load_pricing_config,
    load_view,
    note,
    page_spec,
    show_chart,
)
from energy_market_intelligence.insights import (
    action_answer,
    bridge_answer,
    leakage_answer,
    leakage_thesis,
)
from energy_market_intelligence.localization import SEGMENT_ORDER
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_visualization import (
    PORTFOLIO,
    bill_waterfall_figure,
    portfolio_bill,
)
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY

waterfall = load_view("vw_price_waterfall")
flags = load_view("vw_discount_policy_flags")
pvm_summary = load_view("vw_pvm_bridge_summary")
elasticities = load_elasticities()
guard = load_pricing_config().recommendation
recommendation = recommend_prices(
    waterfall,
    elasticities,
    guard.max_price_step_pct,
    guard.margin_floor_pct,
    max_volume_loss=guard.max_volume_loss_pct,
)
portfolio = portfolio_bill(waterfall)

# 1. The thesis, computed from the data.
with st.container(key="hero"):
    st.title(leakage_thesis(portfolio.leakage_rate, highlight=True))
    style.lead(
        f"{FOCUS_COMPANY} kurgusal bir elektrik perakendecisidir ve tüm veriler sentetiktir; "
        "tutarlar TL cinsinden, sabit 2025 fiyatlarıyla gösterilir."
    )

# 2. The fatura dökümü next to the waterfall it summarises.
segments = [name for name in SEGMENT_ORDER if name in set(waterfall["customer_segment_name"])]
scope = st.segmented_control(
    "Fatura dökümünün kapsamı", [PORTFOLIO, *segments], default=PORTFOLIO, key="home_scope"
)
bill = portfolio_bill(waterfall, None if scope in (None, PORTFOLIO) else scope)
left, right = st.columns([6, 5], gap="large")
with left:
    st.markdown(style.bill_html(bill), unsafe_allow_html=True)
with right:
    st.markdown("**Liste fiyatından net fiyata** (TL/MWh)")
    show_chart(
        bill_waterfall_figure(bill),
        alt=f"Liste fiyatından net fiyata kalemler, TL/MWh ({bill.scope})",
    )
    st.caption("Eksen kesiktir: kalemler arasındaki fark okunabilsin diye sıfırdan başlamaz.")

# 3. Three questions, each with its one-line answer.
st.subheader("Üç soru, veriyle cevap")
cards = (
    ("views/price_waterfall.py", None, leakage_answer(portfolio, flags)),
    ("views/pvm_bridge.py", None, bridge_answer(pvm_summary)),
    ("views/price_recommendation.py", "Ne yapmalı?", action_answer(recommendation)),
)
for index, (column, (path, label, answer)) in enumerate(
    zip(st.columns(3, gap="medium"), cards, strict=True)
):
    with column, st.container(key=f"card-{index}"):
        st.page_link(path, label=label or page_spec(path).question)
        style.answer(answer)

# 4. Why the model can be trusted: true versus estimated elasticity.
st.subheader("Modele neden güvenebilirsiniz?")
recovered = int(elasticities["truth_in_ci"].sum())
st.write(
    "Veri sentetik olduğu için gerçek fiyat esneklikleri bilinir; model onları görmeden tahmin "
    f"eder. {len(elasticities)} segmentin {recovered} tanesinde gerçek değer tahminin %95 güven "
    "aralığının içinde kalır."
)
st.markdown(style.trust_strip_html(elasticities), unsafe_allow_html=True)
st.page_link("views/elasticity.py", label=page_spec("views/elasticity.py").question)

with st.expander("Terimler sözlüğü (bu sayfalarda geçen kavramlar)"):
    st.markdown(
        """
- **Liste fiyatı:** Fiyat listesinde yazan birim fiyat (TL/MWh).
- **Fatura dökümü:** Liste fiyatından net fiyata inen kalemlerin fatura gibi sıralanmış hâli.
- **Fatura içi iskonto:** Faturada liste fiyatın üzerinden düşülen indirim.
- **Fatura dışı prim:** Fatura kesildikten sonra geri ödenen prim ve iskontolar.
- **Net (cebe kalan) fiyat:** Liste fiyatından tüm indirimler, primler, vade ve nakliye maliyeti
  düşüldükten sonra şirketin gerçekte eline geçen birim fiyat.
- **Kaçak oranı:** Liste fiyatının müşteriye ulaşmadan kaybolan kısmı: 1 - net fiyat / liste fiyatı.
- **Fiyat gerçekleşme oranı:** Net ciro / liste fiyatlı ciro (kaçak oranının tamamlayıcısı).
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

note(
    "Bu uygulamadaki tüm veriler ve iş mantığı kamuya açık bir gösterim için yeniden "
    "tasarlanmıştır. Uygulama otomatik ticari karar vermez.",
    label="Gösterim amaçlıdır",
)
