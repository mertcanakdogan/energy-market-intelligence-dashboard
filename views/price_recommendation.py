"""Fiyat önerisi: sınırlı ve marj tabanlı karar destek hesabı."""

import streamlit as st

from dashboard_support import (
    load_elasticities,
    load_pricing_config,
    load_view,
    page_intro,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import recommendation_insight
from energy_market_intelligence.localization import format_pct, format_tl
from energy_market_intelligence.price_recommendation import recommend_prices
from energy_market_intelligence.pricing_visualization import price_recommendation_figure

page_intro(
    "Fiyat Önerisi",
    "Her müşteri segmenti için cebe kalan fiyatın ne kadar değiştirilebileceğini ve bunun "
    "brüt kâra tahmini etkisini gösterir. Soldaki sınırları değiştirerek sonucun nasıl "
    "değiştiğini deneyebilirsiniz.",
)
st.warning(
    "Bu bir karar destek hesabıdır, otomatik fiyat kuralı değildir. Sabit tahmini esneklik, "
    "rakip tepkisi olmaması ve değişmeyen birim maliyet varsayar; yalnızca küçük fiyat "
    "adımları için anlamlıdır.",
    icon=":material/warning:",
)
defaults = load_pricing_config().recommendation
st.sidebar.header("Sınırlar")
max_step = st.sidebar.slider(
    "En büyük fiyat adımı (%)",
    1.0,
    15.0,
    defaults.max_price_step_pct * 100,
    0.5,
    help="Cebe kalan fiyat tek seferde en fazla bu oranda değişir.",
)
margin_floor = st.sidebar.slider(
    "En düşük marj (%)",
    0.0,
    40.0,
    defaults.margin_floor_pct * 100,
    0.5,
    help="Önerilen fiyattaki cep marjı bu değerin altına düşmez (ulaşılabiliyorsa).",
)
volume_guard = st.sidebar.slider(
    "En büyük hacim kaybı (%)",
    1.0,
    20.0,
    defaults.max_volume_loss_pct * 100,
    0.5,
    help="Fiyat artışı, beklenen hacim kaybı bu oranı aşmayacak şekilde sınırlanır.",
)
level = st.sidebar.radio("Ayrıntı düzeyi", ["Müşteri segmenti", "Segment x bölge"])

baseline = load_view("vw_price_waterfall")
elasticities = load_elasticities()
guard_rails = {
    "max_step": max_step / 100,
    "margin_floor": margin_floor / 100,
    "max_volume_loss": volume_guard / 100,
}
by_segment = recommend_prices(baseline, elasticities, **guard_rails)
if level == "Müşteri segmenti":
    group = ["customer_segment_name"]
    table = by_segment
else:
    group = ["customer_segment_name", "region_name"]
    table = recommend_prices(baseline, elasticities, **guard_rails, group_columns=group)

total_change = table["expected_gross_profit_change"].sum()
weighted_price = (table["price_change_pct"] * table["baseline_volume_mwh"]).sum()
cards = st.columns(3)
cards[0].metric(
    "Beklenen brüt kâr değişimi",
    format_tl(total_change, signed=True),
    format_pct(total_change / table["baseline_gross_profit"].sum(), 1, signed=True),
    help="Önerilen fiyat adımları uygulanırsa yıllık brüt kârdaki tahmini değişim.",
)
cards[1].metric(
    "Ortalama fiyat değişimi",
    format_pct(weighted_price / table["baseline_volume_mwh"].sum(), 2, signed=True),
    help="Hacim ağırlıklı ortalama cebe kalan fiyat değişimi.",
)
cards[2].metric(
    "Marj tabanına ulaşamayan grup",
    int(table["binding_constraint"].str.contains("not reachable").sum()),
    help="Tek fiyat adımıyla en düşük marja ulaşılamayan segment veya bölge sayısı.",
)
takeaway(recommendation_insight(table))

st.plotly_chart(price_recommendation_figure(by_segment), width="stretch")
show_table(
    table.sort_values("expected_gross_profit_change", ascending=False)[
        [
            *group,
            "current_pocket_price",
            "unit_variable_cost",
            "current_margin_pct",
            "elasticity",
            "price_change_pct",
            "expected_volume_change_pct",
            "expected_gross_profit_change",
            "gross_profit_change_low",
            "gross_profit_change_high",
            "binding_constraint",
        ]
    ],
    fractions={"current_margin_pct", "price_change_pct", "expected_volume_change_pct"},
)
with st.expander("Uygulanan kurallar"):
    st.markdown(
        """
1. Esnek segmentlerde (esneklik -1'den küçük) kârı en çok artıran cebe kalan fiyat hedeflenir:
   `c * e / (1 + e)` (c: birim maliyet, e: esneklik). Esnek olmayan segmentlerde izin verilen
   en büyük artış hedeflenir.
2. Her değişim en büyük fiyat adımıyla sınırlanır.
3. Fiyat artışı, beklenen hacim kaybı hacim kaybı sınırına ulaşan fiyatla sınırlanır.
4. En düşük marj kuralı en sonda uygulanır ve hacim sınırından önceliklidir. Tek adımda
   ulaşılamıyorsa tam adım önerilir ve grup işaretlenir.

Beklenen hacim değişimi = `(1 + fiyat değişimi) ^ esneklik - 1`. Brüt kâr aralığı, esneklik
tahmininin %95 güven sınırlarıyla hesaplanır.
        """
    )
