"""Gelir köprüsü: fiyat, hacim, karışım ve maliyet etkileri."""

import streamlit as st

from dashboard_support import load_view, note, page_intro, show_chart, show_table, takeaway
from energy_market_intelligence.insights import pvm_insight
from energy_market_intelligence.localization import format_tl
from energy_market_intelligence.pricing_visualization import pvm_bridge_figure

page_intro(
    "views/pvm_bridge.py",
    "Net ciro ve brüt kârın neden değiştiğini fiyat, hacim, karışım ve maliyet etkilerine ayırır. "
    "Karşılaştırma: 2025 (son 12 ay) ve 2024 (önceki 12 ay).",
)
summary = load_view("vw_pvm_bridge_summary")
cells = load_view("vw_pvm_bridge")
row = summary.iloc[0]

cards = st.columns(4)
cards[0].metric(
    "Net ciro değişimi",
    format_tl(row["total_revenue_change"], signed=True),
    help="Cebe kalan fiyatla hesaplanan ciro; 2025 ve 2024 farkı.",
)
cards[1].metric(
    "Fiyat etkisi",
    format_tl(row["price_effect"], signed=True),
    help="Satılan hacim sabitken cebe kalan fiyattaki değişimin ciroya etkisi.",
)
cards[2].metric(
    "Brüt kâr değişimi",
    format_tl(row["total_gp_change"], signed=True),
    help="Net ciro eksi enerji maliyeti; 2025 ve 2024 farkı.",
)
cards[3].metric(
    "Birim maliyet etkisi",
    format_tl(row["gp_cost_effect"], signed=True),
    help="Enerji maliyetindeki artışın (veya azalışın) brüt kâra etkisi.",
)
takeaway(pvm_insight(summary))

show_chart(pvm_bridge_figure(summary))
largest_gap = cells[["reconciliation_gap", "gp_reconciliation_gap"]].abs().max().max()
note(
    "Hacim: toplam satış hacmindeki değişim (eski fiyat ve karışımla). "
    "Karışım: hacmin ürün ve müşteri segmentleri arasındaki dağılımının değişmesi. "
    "Fiyat: cebe kalan fiyattaki değişim (yeni hacimle). Brüt kârda ayrıca birim maliyet "
    "etkisi vardır. Bileşenler toplam değişime tam olarak eşittir; en büyük mutabakat farkı "
    f"{largest_gap:.1e} TL.",
    label="Terimler",
)

st.subheader("Ürün ve segment ayrıntısı")
detail = cells[
    [
        "product_name",
        "customer_segment_name",
        "prior_volume",
        "current_volume",
        "prior_price",
        "current_price",
        "volume_effect",
        "mix_effect",
        "price_effect",
        "total_revenue_change",
        "gp_cost_effect",
        "total_gp_change",
        "reconciliation_gap",
    ]
].sort_values("total_gp_change")
show_table(detail)
