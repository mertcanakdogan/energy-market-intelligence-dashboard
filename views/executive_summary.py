"""Yönetici özeti: pazar ve şirket performansı tek bakışta."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_support import (
    load_config,
    load_view,
    page_intro,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import market_insight
from energy_market_intelligence.localization import (
    format_number,
    format_pct,
    format_tl,
    format_volume,
)
from energy_market_intelligence.metrics import generate_management_observations
from energy_market_intelligence.opportunity import calculate_opportunity_scores
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY
from energy_market_intelligence.visualization import (
    NAVY,
    SLATE,
    gross_margin_trend_figure,
    market_share_trend_figure,
)

page_intro(
    "views/executive_summary.py",
    "Pazarın ve şirketin son 12 ayını (2025) bir önceki 12 ayla (2024) karşılaştırır: hacim, "
    "pazar payı, kâr, rakipler ve bölgesel öncelikler.",
)
kpis = load_view("vw_executive_kpis").iloc[0]
trend = load_view("vw_growth_analysis").sort_values("date")
profit = load_view("vw_focus_profitability_monthly")
regional = calculate_opportunity_scores(
    load_view("vw_regional_opportunity_inputs"), load_config()["opportunity_weights"]
)
share_change = load_view("vw_regional_share_change")
competitors = load_view("vw_competitor_momentum").sort_values("momentum_rank")

row1 = st.columns(5)
row1[0].metric(
    "Pazar hacmi",
    format_volume(kpis["market_volume"]),
    format_pct(kpis["market_yoy_growth"], 1, signed=True),
)
row1[1].metric(
    "Şirket hacmi",
    format_volume(kpis["focus_volume"]),
    format_pct(kpis["focus_yoy_growth"], 1, signed=True),
)
row1[2].metric(
    "Pazar payı",
    format_pct(kpis["focus_market_share"]),
    f"{format_number(kpis['share_change_pp'], 2, signed=True)} puan",
)
row1[3].metric("Brüt kâr", format_tl(kpis["gross_profit"]))
row1[4].metric(
    "Brüt marj",
    format_pct(kpis["gross_margin_pct"]),
    f"{format_number(kpis['gross_margin_change_pp'], 2, signed=True)} puan",
)
takeaway(market_insight(kpis))

left, right = st.columns(2)
with left:
    volume = trend.melt(
        id_vars="date",
        value_vars=["market_volume_mwh", "focus_volume_mwh"],
        var_name="series",
        value_name="volume_mwh",
    )
    volume["series"] = volume["series"].map(
        {"market_volume_mwh": "Toplam pazar", "focus_volume_mwh": FOCUS_COMPANY}
    )
    volume["volume_gwh"] = volume["volume_mwh"] / 1e3
    figure = px.line(
        volume,
        x="date",
        y="volume_gwh",
        color="series",
        title="Aylık hacim: pazar ve şirket",
    )
    figure.update_layout(legend_title=None, yaxis_title="GWh", xaxis_title=None)
    show_chart(figure)
with right:
    show_chart(market_share_trend_figure(trend))

left, right = st.columns(2)
with left:
    st.subheader("Bölgesel kazananlar ve kaybedenler")
    winners = share_change.nlargest(3, "share_change_pp")[["region_name", "share_change_pp"]]
    losers = share_change.nsmallest(3, "share_change_pp")[["region_name", "share_change_pp"]]
    comparison = pd.concat([winners.assign(signal="Kazanım"), losers.assign(signal="Kayıp")])
    chart = px.bar(
        comparison,
        x="share_change_pp",
        y="region_name",
        color="signal",
        color_discrete_map={"Kazanım": NAVY, "Kayıp": SLATE},
        orientation="h",
        title="Bölgelere göre şirketin pay değişimi",
    )
    chart.update_layout(xaxis_title="Yüzde puan", yaxis_title=None, legend_title=None)
    show_chart(chart)
with right:
    show_chart(gross_margin_trend_figure(profit))

left, right = st.columns(2)
with left:
    st.subheader("Rakiplerin pay eğilimi")
    show_table(
        competitors[
            ["momentum_rank", "company_name", "current_share", "share_change_pp", "momentum_signal"]
        ].head(5),
        fractions={"current_share"},
    )
with right:
    st.subheader("Fırsat sıralaması: ilk 5 bölge")
    show_table(
        regional[
            [
                "opportunity_rank",
                "region_name",
                "opportunity_score",
                "market_growth",
                "focus_share",
            ]
        ].head(5),
        fractions={"market_growth", "focus_share"},
    )

st.subheader("Yönetim gözlemleri")
observation_kpis = {
    "share_change_pp": float(kpis["share_change_pp"]),
    "market_yoy_growth_pct": float(kpis["market_yoy_growth"]) * 100,
    "gross_margin_change_pp": float(kpis["gross_margin_change_pp"]),
}
for observation in generate_management_observations(observation_kpis, regional, language="tr"):
    st.markdown(f"- {observation}")
