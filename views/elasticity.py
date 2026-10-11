"""Fiyat esnekliği: segment bazında tahmin ve bilinen gerçek değer."""

import streamlit as st

from dashboard_support import load_elasticities, page_intro, show_table, takeaway
from energy_market_intelligence.insights import elasticity_insight
from energy_market_intelligence.localization import format_number, order_segments
from energy_market_intelligence.pricing_visualization import elasticity_recovery_figure

page_intro(
    "Fiyat Esnekliği",
    "Cebe kalan fiyat %1 arttığında satış hacminin yüzde kaç değiştiğini, müşteri segmentine "
    "göre gösterir. Veri sentetik olduğu için gerçek değerler bilinir ve tahminin ne kadar "
    "doğru olduğu kontrol edilebilir.",
)
table = order_segments(load_elasticities()).reset_index(drop=True)

cards = st.columns(len(table))
for column, row in zip(cards, table.itertuples(index=False), strict=True):
    column.metric(
        row.customer_segment_name,
        format_number(row.elasticity, 2),
        f"%95 GA: {format_number(row.ci_low, 2)} / {format_number(row.ci_high, 2)}",
        delta_color="off",
        help="Fiyat esnekliği tahmini. -1'den küçükse talep esnek (fiyata duyarlı), "
        "-1'den büyükse esnek değil.",
    )
takeaway(elasticity_insight(table))

st.plotly_chart(elasticity_recovery_figure(table), width="stretch")
recovered = int(table["truth_in_ci"].sum())
st.success(
    f"Bilinen gerçek esneklik, {len(table)} segmentin {recovered} tanesinde tahminin %95 güven "
    "aralığı içinde. Veri üreticisinin gerçek parametreleri bilindiği için tahmin yöntemi "
    "doğrudan sınanabilir.",
    icon=":material/check_circle:",
)
show_table(
    table[
        [
            "customer_segment_name",
            "elasticity",
            "std_error",
            "ci_low",
            "ci_high",
            "true_elasticity",
            "abs_error",
            "truth_in_ci",
            "cross_elasticity",
            "classification",
        ]
    ]
)
with st.expander("Yöntem ve varsayımlar"):
    st.markdown(
        """
- Her müşteri segmenti için ayrı log-log regresyon (OLS):
  `log(hacim) ~ log(cebe kalan fiyat) + log(rakip fiyatı) + trend + ay değişkenleri +
  bölge x ürün sabit etkileri + kampanya`.
- Standart hatalar bölge bazında kümelenmiştir. Tahmini mümkün kılan fiyat değişimi, bölgelere
  kademeli uygulanan liste fiyat artışlarından ve aylık rastgele indirim oynamalarından gelir.
- Esneklik tasarım gereği sabittir. Gerçekte talep büyük fiyat değişimlerinde sabit esneklikle
  hareket etmez ve rakipler tepki verebilir; sonuçlar küçük fiyat adımları için yerel
  tahminlerdir.
        """
    )
