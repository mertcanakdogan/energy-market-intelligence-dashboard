"""Rekabet analizi: pay eğilimi ve pazar yoğunlaşması."""

import plotly.express as px
import streamlit as st

from dashboard_support import load_view, page_intro, show_chart, show_table, takeaway
from energy_market_intelligence.insights import competition_insight
from energy_market_intelligence.localization import VALUE_LABELS
from energy_market_intelligence.visualization import competitor_change_figure

page_intro(
    "views/competitive_intelligence.py",
    "Şirketlerin pazar payı ve son 12 aydaki pay değişimi ile bölgesel pazarların ne kadar "
    "yoğunlaştığını gösterir. HHI, payların karelerinin toplamıdır; hukuki veya düzenleyici bir "
    "değerlendirme değildir.",
)
momentum = load_view("vw_competitor_momentum").sort_values("momentum_rank")
ranking = load_view("vw_regional_company_ranking")
concentration = load_view("vw_regional_concentration")
takeaway(competition_insight(momentum, concentration))

left, right = st.columns(2)
with left:
    show_chart(competitor_change_figure(momentum))
share_figure = px.bar(
    momentum.sort_values("current_share"),
    x="current_share",
    y="company_name",
    orientation="h",
    title="Şirketlerin güncel pazar payı",
    labels={"current_share": "Pazar payı", "company_name": "Şirket"},
)
share_figure.update_xaxes(tickformat=".1%")
with right:
    show_chart(share_figure)

dominant = ranking.query("company_rank == 1")
left, right = st.columns(2)
concentration_view = concentration.sort_values("hhi").assign(
    concentration_classification=lambda frame: frame["concentration_classification"].map(
        lambda value: VALUE_LABELS.get(value, value)
    )
)
concentration_figure = px.bar(
    concentration_view,
    x="hhi",
    y="region_name",
    color="concentration_classification",
    orientation="h",
    title="Bölgesel pazarlar ne kadar yoğunlaşmış?",
    labels={
        "hhi": "HHI (paylar 0-1 arası)",
        "region_name": "Bölge",
        "concentration_classification": "Yoğunlaşma düzeyi",
    },
)
with left:
    show_chart(concentration_figure)
leader_figure = px.histogram(
    dominant,
    x="company_name",
    title="Hangi şirket en çok bölgede lider?",
    labels={"company_name": "Bölge lideri"},
)
leader_figure.update_layout(yaxis_title="Lider olduğu bölge sayısı")
with right:
    show_chart(leader_figure)

st.subheader("Bölgeye göre şirket sıralaması")
selected = st.selectbox("Bölge", sorted(ranking["region_name"].unique()))
show_table(
    ranking[ranking["region_name"] == selected].sort_values("company_rank"),
    fractions={"market_share"},
)
