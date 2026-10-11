"""Fiyat şelalesi: liste fiyattan cebe kalan fiyata."""

import plotly.express as px
import streamlit as st

from dashboard_support import (
    breach,
    load_view,
    page_intro,
    select_regions,
    show_chart,
    show_table,
    takeaway,
)
from energy_market_intelligence.insights import price_waterfall_insight
from energy_market_intelligence.localization import (
    SEGMENT_ORDER,
    format_number,
    format_pct,
    format_tl,
)
from energy_market_intelligence.pricing_visualization import (
    DEDUCTION_LABELS,
    INVOICE_LABEL,
    price_waterfall_figure,
    segment_waterfall_table,
)
from energy_market_intelligence.visualization import LEAK_RED, NAVY, apply_business_theme

page_intro(
    "views/price_waterfall.py",
    "Bir MWh elektriğin liste fiyatından, indirimler, iskontolar, vade ve servis maliyetleri "
    "düşüldükten sonra şirketin eline geçen (cebe kalan) fiyata nasıl inildiğini gösterir. "
    "Veri: 2025.",
)
detail = load_view("vw_price_waterfall")
flags = load_view("vw_discount_policy_flags")
regions = select_regions(detail, key="waterfall_regions")
selected = detail[detail["region_name"].isin(regions)]
if selected.empty:
    st.info("En az bir bölge seçin.")
    st.stop()

list_revenue = selected["list_revenue"].sum()
pocket_revenue = selected["pocket_revenue"].sum()
volume = selected["volume_mwh"].sum()
selected_flags = flags[flags["region_name"].isin(regions)]
cards = st.columns(4)
cards[0].metric(
    "Liste fiyat (TL/MWh)",
    format_number(list_revenue / volume, 0),
    help="Hacim ağırlıklı ortalama liste fiyat.",
)
cards[1].metric(
    "Cebe kalan (TL/MWh)",
    format_number(pocket_revenue / volume, 0),
    help="Tüm indirim ve maliyet kalemleri düşüldükten sonra kalan hacim ağırlıklı fiyat.",
)
cards[2].metric(
    "Fiyat gerçekleşme",
    format_pct(pocket_revenue / list_revenue),
    help="Cebe kalan ciro / liste fiyatlı ciro.",
)
cards[3].metric(
    "Politika üstü indirim",
    format_tl(selected_flags["revenue_leakage_above_policy"].sum()),
    help="Her segment için izin verilen indirim oranının üstünde verilen indirimin yıllık tutarı.",
)
takeaway(price_waterfall_insight(selected, selected_flags))

show_chart(price_waterfall_figure(selected))
st.caption(
    "Lacivert çubuklar liste fiyatı ve ara toplamları (fatura fiyatı, net fiyat), kırmızı "
    "çubuklar fiyattan düşülen kalemleri gösterir. Dikey eksen, farkların okunabilmesi için "
    "kesilmiştir."
)

st.subheader("İndirim politikaya uygun mu?")
available = [name for name in SEGMENT_ORDER if name in set(flags["customer_segment_name"])]
segment = st.selectbox("Müşteri segmenti", available)
view = selected_flags[selected_flags["customer_segment_name"] == segment].sort_values(
    "excess_discount_pp", ascending=False
)
status = view["exceeds_policy"].map({True: "Politika sınırını aşıyor", False: "Sınır içinde"})
figure = px.bar(
    view.assign(status=status),
    x="region_name",
    y="on_invoice_discount_pct",
    color="status",
    color_discrete_map={"Politika sınırını aşıyor": LEAK_RED, "Sınır içinde": NAVY},
    title=f"{segment}: bölgelere göre fatura içi iskonto oranı ve politika sınırı",
    labels={"on_invoice_discount_pct": "İndirim oranı (liste fiyata göre)", "region_name": "Bölge"},
)
figure.update_layout(legend_title=None)
figure.add_hline(
    y=float(view["policy_max_discount_pct"].iloc[0]),
    line_dash="dash",
    annotation_text="politika üst sınırı",
)
figure.update_yaxes(tickformat=".0%")
apply_business_theme(figure, y_title="İndirim oranı (liste fiyata göre)")
figure.update_xaxes(title=None)
show_chart(figure)

breaches = selected_flags[selected_flags["exceeds_policy"]].sort_values(
    "revenue_leakage_above_policy", ascending=False
)
if breaches.empty:
    st.caption("Seçilen bölgelerde hiçbir segment indirim politikasının sınırını aşmıyor.")
else:
    breach(
        f"{len(breaches)} bölge-segment çifti indirim politikasının sınırını aşıyor. "
        "Politika üstü indirim = (indirim oranı - politika sınırı) x liste fiyatlı ciro."
    )
show_table(
    breaches[
        [
            "customer_segment_name",
            "region_name",
            "on_invoice_discount_pct",
            "policy_max_discount_pct",
            "excess_discount_pp",
            "revenue_leakage_above_policy",
        ]
    ].assign(excess_discount_pp=lambda frame: frame["excess_discount_pp"] * 100),
    fractions={"on_invoice_discount_pct", "policy_max_discount_pct"},
)
with st.expander("MWh başına şelale tablosu (segmentlere göre)"):
    show_table(
        segment_waterfall_table(selected).rename(
            columns={
                "on_invoice_discount": f"{DEDUCTION_LABELS['on_invoice_discount']} (TL/MWh)",
                "invoice_price": f"{INVOICE_LABEL} (TL/MWh)",
                "off_invoice_rebate": f"{DEDUCTION_LABELS['off_invoice_rebate']} (TL/MWh)",
                "payment_term_cost": f"{DEDUCTION_LABELS['payment_term_cost']} (TL/MWh)",
                "freight_service_cost": f"{DEDUCTION_LABELS['freight_service_cost']} (TL/MWh)",
            }
        )
    )
