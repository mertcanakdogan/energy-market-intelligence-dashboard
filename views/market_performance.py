"""Pazar performansı: büyüme, hacim ve pay."""

import plotly.express as px
import streamlit as st

from dashboard_support import (
    load_view,
    page_intro,
    select_regions,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import performance_insight

page_intro(
    "views/market_performance.py",
    "Pazarın ve şirketin hacmini ve pazar payını zaman içinde ve bölgelere göre gösterir. "
    "Soldaki filtrelerle bölge ve dönem seçebilirsiniz.",
)
regional = load_view("vw_market_metrics")
companies = load_view("vw_company_monthly")
selected_regions = select_regions(regional, key="market_regions")
minimum = regional["date"].min().date()
maximum = regional["date"].max().date()
date_range = st.sidebar.slider("Dönem", minimum, maximum, (minimum, maximum), format="MM/YYYY")

filtered = regional[
    regional["region_name"].isin(selected_regions)
    & regional["date"].dt.date.between(date_range[0], date_range[1])
]
company_filtered = companies[
    companies["region_name"].isin(selected_regions)
    & companies["date"].dt.date.between(date_range[0], date_range[1])
]
if filtered.empty:
    st.info("Seçilen bölge ve dönem için veri yok.")
    st.stop()
monthly = filtered.groupby("date", as_index=False)[["market_volume_mwh", "focus_volume_mwh"]].sum()
monthly["focus_share"] = monthly["focus_volume_mwh"] / monthly["market_volume_mwh"]
takeaway(performance_insight(monthly))

monthly["market_volume_gwh"] = monthly["market_volume_mwh"] / 1e3
left, right = st.columns(2)
volume_figure = px.line(
    monthly,
    x="date",
    y="market_volume_gwh",
    title="Toplam pazar hacmi nasıl değişiyor?",
    labels={"market_volume_gwh": "Pazar hacmi (GWh)", "date": "Ay"},
)
with left:
    show_chart(volume_figure)
share_figure = px.line(
    monthly,
    x="date",
    y="focus_share",
    title="Şirket pazar payı kazanıyor mu?",
    labels={"focus_share": "Şirketin pazar payı", "date": "Ay"},
)
share_figure.update_yaxes(tickformat=".1%")
with right:
    show_chart(share_figure)

company_summary = (
    company_filtered.groupby("company_name", as_index=False)["company_volume_mwh"]
    .sum()
    .sort_values("company_volume_mwh", ascending=False)
)
company_summary["volume_gwh"] = company_summary["company_volume_mwh"] / 1e3
region_summary = filtered.groupby("region_name", as_index=False).agg(
    market_volume_mwh=("market_volume_mwh", "sum"),
    focus_volume_mwh=("focus_volume_mwh", "sum"),
)
region_summary["focus_share"] = (
    region_summary["focus_volume_mwh"] / region_summary["market_volume_mwh"]
)
region_summary["market_volume_gwh"] = region_summary["market_volume_mwh"] / 1e3
left, right = st.columns(2)
company_figure = px.bar(
    company_summary,
    x="company_name",
    y="volume_gwh",
    title="Hangi şirketler en çok hacme sahip?",
    labels={"volume_gwh": "Hacim (GWh)", "company_name": "Şirket"},
)
with left:
    show_chart(company_figure)
regional_figure = px.scatter(
    region_summary,
    x="market_volume_gwh",
    y="focus_share",
    text="region_name",
    title="Pazar büyüklüğü ile şirket payı nerede ayrışıyor?",
    labels={"market_volume_gwh": "Pazar hacmi (GWh)", "focus_share": "Şirketin pazar payı"},
)
regional_figure.update_traces(textposition="top center", textfont={"size": 11})
regional_figure.update_yaxes(tickformat=".1%")
with right:
    show_chart(regional_figure)

st.subheader("Bölge ve ay bazında ayrıntı")
show_table(
    filtered.sort_values("date", ascending=False)[
        [
            "date",
            "region_name",
            "market_volume_mwh",
            "focus_volume_mwh",
            "focus_market_share",
            "market_yoy_growth",
        ]
    ].assign(date=lambda frame: frame["date"].dt.strftime("%m/%Y")),
    fractions={"focus_market_share", "market_yoy_growth"},
)
