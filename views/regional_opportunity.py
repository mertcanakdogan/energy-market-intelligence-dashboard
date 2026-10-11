"""Bölgesel fırsat: açıklanabilir önceliklendirme."""

import streamlit as st

from dashboard_support import (
    load_config,
    load_view,
    note,
    page_intro,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import opportunity_insight
from energy_market_intelligence.localization import COLUMN_LABELS, format_pct
from energy_market_intelligence.opportunity import calculate_opportunity_scores
from energy_market_intelligence.visualization import opportunity_matrix_figure

page_intro(
    "views/regional_opportunity.py",
    "Hangi bölgelere öncelik verilmesi gerektiğini, pazar büyüklüğü, büyüme, pay boşluğu, "
    "pay eğilimi, marj ve rekabet puanlarını birleştirerek sıralar. Puanlar açıkça "
    "görülebilir; analist incelemesi için bir başlangıçtır.",
)
note(
    "Bu, gösterim amaçlı şeffaf bir önceliklendirme yöntemidir; nedensel bir model veya "
    "otomatik karar kuralı değildir.",
    label="Yöntem",
)
config = load_config()
opportunity = calculate_opportunity_scores(
    load_view("vw_regional_opportunity_inputs"), config["opportunity_weights"]
)
takeaway(opportunity_insight(opportunity))

minimum_score = st.sidebar.slider("En düşük fırsat skoru", 0, 100, 0)
sort_options = {
    COLUMN_LABELS["opportunity_score"]: "opportunity_score",
    COLUMN_LABELS["market_growth"]: "market_growth",
    COLUMN_LABELS["focus_share"]: "focus_share",
    COLUMN_LABELS["gross_margin_pct"]: "gross_margin_pct",
}
sort_label = st.sidebar.selectbox("Sıralama ölçütü", list(sort_options))
filtered = opportunity[opportunity["opportunity_score"] >= minimum_score].sort_values(
    sort_options[sort_label], ascending=False
)
if filtered.empty:
    st.info("Seçilen en düşük skoru sağlayan bölge yok.")
    st.stop()
show_chart(opportunity_matrix_figure(filtered))

left, right = st.columns(2)
with left:
    st.subheader("En yüksek fırsatlar")
    show_table(
        filtered.head(5)[
            [
                "opportunity_rank",
                "region_name",
                "opportunity_score",
                "market_growth",
                "focus_share",
                "gross_margin_pct",
            ]
        ],
        fractions={"market_growth", "focus_share", "gross_margin_pct"},
    )
with right:
    st.subheader("Risk ve gerileme işaretleri")
    risks = opportunity.sort_values(["market_growth", "share_momentum"]).head(5)
    show_table(
        risks[["region_name", "market_growth", "share_momentum", "gross_margin_pct", "hhi"]],
        fractions={"market_growth", "share_momentum", "gross_margin_pct"},
    )

st.subheader("Skorun bileşenleri")
components = [
    "region_name",
    "opportunity_score",
    "market_size_score",
    "market_growth_score",
    "share_gap_score",
    "momentum_score",
    "margin_score",
    "competition_score",
]
show_table(filtered[components])
weights = ", ".join(
    f"{COLUMN_LABELS.get(key + '_score', key)}: {format_pct(value, 0)}"
    for key, value in config["opportunity_weights"].items()
)
st.caption(f"Gösterim ağırlıkları: {weights}")
