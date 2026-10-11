"""Kârlılık: hacim ile kârın kalitesini ayırmak."""

import plotly.express as px
import streamlit as st

from dashboard_support import load_view, page_intro, show_chart, takeaway
from energy_market_intelligence.insights import profitability_insight
from energy_market_intelligence.localization import format_number, format_pct, format_tl
from energy_market_intelligence.visualization import gross_margin_trend_figure, profit_bridge_figure

page_intro(
    "views/profitability.py",
    "Satış hacmi ile o hacmin ürettiği brüt kârın kalitesini birbirinden ayırır: hangi "
    "bölge ve ürün ailesi ne kadar kâr getiriyor? Veri: 2025.",
)
monthly = load_view("vw_focus_profitability_monthly")
summary = load_view("vw_profitability_summary")
bridge = load_view("vw_revenue_bridge")

totals = summary[["volume_mwh", "revenue", "gross_profit"]].sum()
margin = totals["gross_profit"] / totals["revenue"]
profit_per_mwh = totals["gross_profit"] / totals["volume_mwh"]
cards = st.columns(4)
cards[0].metric("Ciro", format_tl(totals["revenue"]))
cards[1].metric("Brüt kâr", format_tl(totals["gross_profit"]))
cards[2].metric("Brüt marj", format_pct(margin), help="Brüt kâr / ciro.")
cards[3].metric("Kâr (TL/MWh)", format_number(profit_per_mwh, 0))

region = summary.groupby("region_name", as_index=False)[
    ["volume_mwh", "revenue", "gross_profit"]
].sum()
region["gross_margin_pct"] = region["gross_profit"] / region["revenue"]
takeaway(profitability_insight(region))

region["volume_gwh"] = region["volume_mwh"] / 1e3
region["gross_profit_mn"] = region["gross_profit"] / 1e6
left, right = st.columns(2)
with left:
    show_chart(gross_margin_trend_figure(monthly))
region_figure = px.scatter(
    region,
    x="volume_gwh",
    y="gross_margin_pct",
    size="gross_profit_mn",
    text="region_name",
    title="Hangi bölgeler hacim ve marjı birlikte sağlıyor?",
    labels={
        "volume_gwh": "Şirket hacmi (GWh)",
        "gross_margin_pct": "Brüt marj",
        "gross_profit_mn": "Brüt kâr (mn TL)",
    },
)
region_figure.update_traces(textposition="top center", textfont={"size": 11})
region_figure.update_yaxes(tickformat=".1%")
with right:
    show_chart(region_figure)

left, right = st.columns(2)
product = summary.groupby("product_segment", as_index=False)[
    ["volume_mwh", "revenue", "gross_profit"]
].sum()
product["gross_margin_pct"] = product["gross_profit"] / product["revenue"]
product["gross_profit_mn"] = product["gross_profit"] / 1e6
product_figure = px.bar(
    product,
    x="product_segment",
    y="gross_profit_mn",
    color="gross_margin_pct",
    title="Hangi ürün aileleri brüt kâra katkı veriyor?",
    labels={
        "gross_profit_mn": "Brüt kâr (mn TL)",
        "product_segment": "Ürün ailesi",
        "gross_margin_pct": "Brüt marj",
    },
)
with left:
    show_chart(product_figure)
with right:
    show_chart(profit_bridge_figure(bridge))

st.caption(
    "Köprü, baz dönem hacmi ve fiyatı etkileri ile bir etkileşim terimi kullanır. "
    "Ciro değişimini toplam olarak açıklar; nedensellik iddia etmez."
)
