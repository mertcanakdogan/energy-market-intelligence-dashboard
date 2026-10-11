"""Plain-language Turkish takeaways computed from the analytical tables.

Every sentence is built from calculated numbers (nothing is hard-coded), so the text on the app
pages always matches the data on the same page. Sentences deliberately avoid Turkish case
suffixes on dynamic names and numbers, which cannot be generated reliably.
"""

from __future__ import annotations

import pandas as pd

from energy_market_intelligence.localization import (
    format_number,
    format_pct,
    format_pct_accusative,
    format_tl,
    format_tl_per_mwh,
    format_volume,
    order_segments,
)
from energy_market_intelligence.pricing_visualization import Bill, segment_waterfall_table


def _worst_row(frame: pd.DataFrame, column: str, *, largest: bool = True) -> pd.Series:
    return frame.loc[frame[column].idxmax() if largest else frame[column].idxmin()]


def price_waterfall_insight(waterfall: pd.DataFrame, flags: pd.DataFrame) -> str:
    """Realization, the segment with the largest list-to-pocket gap and policy breaches."""

    table = segment_waterfall_table(waterfall)
    table = table.assign(gap=1 - table["pocket_price"] / table["list_price"])
    realization = waterfall["pocket_revenue"].sum() / waterfall["list_revenue"].sum()
    worst = _worst_row(table, "gap")
    text = (
        f"100 TL liste fiyatlı satıştan ortalama {format_number(realization * 100, 1)} TL "
        f"cebe kalıyor. Kayıp en çok {worst['customer_segment_name']} segmentinde: "
        f"liste fiyat {format_tl_per_mwh(worst['list_price'])}, cebe kalan fiyat "
        f"{format_tl_per_mwh(worst['pocket_price'])} "
        f"(fark {format_pct(worst['gap'])})."
    )
    breaches = flags[flags["exceeds_policy"]]
    if breaches.empty:
        return text + " Hiçbir bölge indirim politikasının üst sınırını aşmıyor."
    regions = breaches.groupby("region_name")["revenue_leakage_above_policy"].sum()
    top = regions.sort_values(ascending=False).head(3).index.tolist()
    return (
        text + f" {breaches['region_name'].nunique()} bölgede indirim, politika sınırının üstünde; "
        f"bu fazladan indirim yılda {format_tl(breaches['revenue_leakage_above_policy'].sum())} "
        f"tutuyor (en çok: {', '.join(top)})."
    )


def pvm_insight(summary: pd.DataFrame) -> str:
    """Why revenue and gross profit moved: price, volume, mix and unit cost."""

    row = summary.iloc[0]
    revenue_word = "arttı" if row["total_revenue_change"] >= 0 else "azaldı"
    profit_word = "arttı" if row["total_gp_change"] >= 0 else "azaldı"
    text = (
        f"Net ciro {format_tl(abs(row['total_revenue_change']))} {revenue_word} "
        f"(hacim {format_tl(row['volume_effect'], signed=True)}, "
        f"fiyat {format_tl(row['price_effect'], signed=True)}, "
        f"karışım {format_tl(row['mix_effect'], signed=True)}). "
        f"Brüt kâr ise {format_tl(abs(row['total_gp_change']))} {profit_word}; "
        f"birim maliyetteki değişim {format_tl(row['gp_cost_effect'], signed=True)} etki yaptı."
    )
    if row["gp_cost_effect"] < 0 and row["gp_price_effect"] > 0:
        recovery = row["gp_price_effect"] / -row["gp_cost_effect"]
        text += (
            f" Fiyat artışları, maliyet artışının yaklaşık {format_pct(recovery, 0)} kadarını "
            "telafi edebildi."
        )
    return text


def elasticity_insight(table: pd.DataFrame, price_step: float = 0.05) -> str:
    """Per-segment elasticity in words and how many true values the intervals recover."""

    ordered = order_segments(table)
    estimates = ", ".join(
        f"{row.customer_segment_name} {format_number(row.elasticity, 2)}"
        for row in ordered.itertuples(index=False)
    )
    losses = ", ".join(
        format_pct(1 - (1 + price_step) ** row.elasticity, 1)
        for row in ordered.itertuples(index=False)
    )
    recovered = int(table["truth_in_ci"].sum()) if "truth_in_ci" in table else 0
    text = (
        f"Esneklik tahminleri: {estimates}. Fiyat {format_pct(price_step, 0)} artarsa hacim "
        f"sırasıyla yaklaşık {losses} düşer; yani en duyarlı segment en çok hacim kaybeder."
    )
    if "truth_in_ci" in table:
        text += (
            f" Veri sentetik olduğu için gerçek değerler bilinir: {recovered}/{len(table)} "
            "segmentte gerçek esneklik tahminin %95 güven aralığının içinde."
        )
    return text


def promo_insight(estimates: pd.DataFrame) -> str:
    """Compare the naive before/after reading with the price-adjusted campaign effect."""

    by_method = estimates.set_index("method")
    adjusted, naive = by_method.loc["price_adjusted"], by_method.loc["naive"]
    text = (
        f"Kampanyanın gerçek ek hacim etkisi yaklaşık {format_pct(adjusted['uplift'])} "
        f"(%95 güven aralığı: {format_pct(adjusted['ci_low'])} ile "
        f"{format_pct(adjusted['ci_high'])}). "
        f"Basit önce/sonra karşılaştırması {format_pct(naive['uplift'])} gösteriyor; "
        "aradaki fark, "
        "kampanya indiriminin ve liste fiyat artışlarının hacme etkisinden geliyor."
    )
    if "true_uplift" in adjusted:
        text += (
            f" Gerçek (veri üreticisindeki) değer {format_pct(adjusted['true_uplift'])}: "
            "fiyat düzeltmeli tahmin buna yakın, basit karşılaştırma ise şişkin."
        )
    return text


def recommendation_insight(table: pd.DataFrame) -> str:
    """Total expected gross-profit effect of the recommended price steps."""

    baseline = table["baseline_gross_profit"].sum()
    change = table["expected_gross_profit_change"].sum()
    volume_base = table["baseline_volume_mwh"].sum()
    volume_change = (
        table["expected_volume_change_pct"] * table["baseline_volume_mwh"]
    ).sum() / volume_base
    price_change = (table["price_change_pct"] * table["baseline_volume_mwh"]).sum() / volume_base
    direction = "artar" if change >= 0 else "azalır"
    price_word = "artar" if price_change >= 0 else "azalır"
    volume_word = "artar" if volume_change >= 0 else "azalır"
    return (
        "Önerilen adımlar uygulanırsa cebe kalan fiyat ortalama "
        f"{format_pct(abs(price_change), 1)} {price_word}, hacim yaklaşık "
        f"{format_pct(abs(volume_change), 1)} {volume_word} ve brüt kâr yılda "
        f"{format_tl(abs(change))} ({format_pct(change / baseline, 1, signed=True)}) "
        f"{direction}. "
        "Bu bir karar destek hesabıdır; sabit esneklik ve rakip tepkisi olmaması "
        "varsayımına dayanır."
    )


# ---------------------------------------------------------------------------------------------
# Landing page: the thesis and one-line answers to the three questions
# ---------------------------------------------------------------------------------------------


def leakage_thesis(leakage_rate: float, *, highlight: bool = False) -> str:
    """The hero sentence of the landing page, e.g. "Liste fiyatının %14,8'i ... kayboluyor."

    With ``highlight`` the percentage is wrapped in Streamlit's red text markup.
    """

    share = format_pct_accusative(leakage_rate)
    if highlight:
        share = f":red[{share}]"
    return f"Liste fiyatının {share} müşteriye ulaşmadan kayboluyor."


def leakage_answer(bill: Bill, flags: pd.DataFrame) -> str:
    """Largest bill deduction and the number of region-segment pairs above the policy limit."""

    deductions = [line for line in bill.lines if line.kind == "deduction"]
    largest = max(deductions, key=lambda line: line.amount)
    breaches = int(flags["exceeds_policy"].sum())
    return (
        f"En büyük kalem {largest.label.lower()} (liste fiyata göre "
        f"{format_pct(largest.share_of_list)}); {breaches} bölge-segment çifti indirim "
        "politikasının sınırını aşıyor."
    )


def bridge_answer(summary: pd.DataFrame) -> str:
    """Revenue versus gross-profit change and the unit-cost effect in one sentence."""

    row = summary.iloc[0]
    revenue_word = "arttı" if row["total_revenue_change"] >= 0 else "azaldı"
    profit_word = "arttı" if row["total_gp_change"] >= 0 else "azaldı"
    return (
        f"Net ciro {format_tl(abs(row['total_revenue_change']))} {revenue_word}, brüt kâr "
        f"{format_tl(abs(row['total_gp_change']))} {profit_word}; birim maliyet etkisi "
        f"{format_tl(row['gp_cost_effect'], signed=True)}."
    )


def action_answer(table: pd.DataFrame) -> str:
    """Expected yearly gross-profit change of the recommended price steps."""

    change = table["expected_gross_profit_change"].sum()
    share = change / table["baseline_gross_profit"].sum()
    direction = "artabilir" if change >= 0 else "azalabilir"
    return (
        f"Önerilen fiyat adımlarıyla brüt kâr yılda {format_tl(abs(change))} "
        f"({format_pct(share, 1, signed=True)}) {direction}."
    )


def headline_findings(
    waterfall: pd.DataFrame,
    flags: pd.DataFrame,
    pvm_summary: pd.DataFrame,
    elasticities: pd.DataFrame,
    promo: pd.DataFrame,
    recommendation: pd.DataFrame,
) -> list[str]:
    """The three findings and one recommendation shown on the landing page."""

    return [
        price_waterfall_insight(waterfall, flags),
        pvm_insight(pvm_summary),
        elasticity_insight(elasticities) + " " + promo_insight(promo),
        recommendation_insight(recommendation),
    ]


# ---------------------------------------------------------------------------------------------
# Market pages
# ---------------------------------------------------------------------------------------------


def market_insight(kpis: pd.Series) -> str:
    """Market growth, the focus company's share and margin in one paragraph."""

    growth = kpis["market_yoy_growth"]
    share_change = kpis["share_change_pp"]
    margin_change = kpis["gross_margin_change_pp"]
    return (
        f"Pazar hacmi bir önceki yıla göre {format_pct(growth, 1, signed=True)} değişti; şirketin "
        f"pazar payı {format_pct(kpis['focus_market_share'])} ve "
        f"{format_number(share_change, 2, signed=True)} puan değişti. Brüt marj "
        f"{format_pct(kpis['gross_margin_pct'])}; yıllık değişim "
        f"{format_number(margin_change, 2, signed=True)} puan."
    )


def competition_insight(momentum: pd.DataFrame, concentration: pd.DataFrame) -> str:
    """Leader, fastest gainer and the most concentrated regional market."""

    leader = _worst_row(momentum, "current_share")
    gainer = _worst_row(momentum, "share_change_pp")
    loser = _worst_row(momentum, "share_change_pp", largest=False)
    top = _worst_row(concentration, "hhi")
    return (
        f"Pazar lideri {leader['company_name']} (pay {format_pct(leader['current_share'])}). "
        f"Son 12 ayda en çok pay kazanan {gainer['company_name']} "
        f"({format_number(gainer['share_change_pp'], 2, signed=True)} puan), en çok kaybeden "
        f"{loser['company_name']} "
        f"({format_number(loser['share_change_pp'], 2, signed=True)} puan). "
        f"En yoğunlaşmış bölgesel pazar: {top['region_name']} (HHI {format_number(top['hhi'], 3)})."
    )


def performance_insight(monthly: pd.DataFrame) -> str:
    """Peak-to-trough seasonality and the share trend over the selected period."""

    ordered = monthly.sort_values("date")
    first, last = ordered["focus_share"].iloc[0], ordered["focus_share"].iloc[-1]
    peak = _worst_row(ordered, "market_volume_mwh")
    low = _worst_row(ordered, "market_volume_mwh", largest=False)
    return (
        f"Seçili dönemde şirketin pazar payı {format_pct(first)} düzeyinden {format_pct(last)} "
        f"düzeyine geldi. Pazar hacmi en yüksek {peak['date']:%m/%Y} ayında "
        f"({format_volume(peak['market_volume_mwh'])}), en düşük {low['date']:%m/%Y} ayında "
        f"({format_volume(low['market_volume_mwh'])}); mevsimsellik büyüme okumasını etkiler."
    )


def profitability_insight(region: pd.DataFrame) -> str:
    """Best and weakest regional gross margin of the focus company."""

    best = _worst_row(region, "gross_margin_pct")
    worst = _worst_row(region, "gross_margin_pct", largest=False)
    return (
        f"En yüksek brüt marj {best['region_name']} bölgesinde "
        f"({format_pct(best['gross_margin_pct'])}), en düşük marj {worst['region_name']} "
        f"bölgesinde ({format_pct(worst['gross_margin_pct'])}). "
        "Hacim tek başına yeterli değildir: marjı düşük bölgelerde büyümek kârı azaltabilir."
    )


def opportunity_insight(opportunity: pd.DataFrame) -> str:
    """Top-ranked region and the weakest-growth regions."""

    top = _worst_row(opportunity, "opportunity_score")
    weakest = opportunity.sort_values("market_growth").head(2)["region_name"].tolist()
    return (
        f"Öncelik sıralamasında ilk bölge {top['region_name']} "
        f"(skor {format_number(top['opportunity_score'], 1)}/100): pazar büyümesi "
        f"{format_pct(top['market_growth'], 1, signed=True)}, şirket payı "
        f"{format_pct(top['focus_share'])}. Pazarı en yavaş büyüyen bölgeler: {', '.join(weakest)}."
    )


def scenario_insight(result: dict[str, float]) -> str:
    """Direction of the what-if result in one sentence."""

    profit = result["gross_profit_delta"]
    volume_change = result["volume_delta"] / result["baseline_volume_mwh"]
    word = "artar" if profit >= 0 else "azalır"
    return (
        f"Bu varsayımlarla brüt kâr yılda {format_tl(abs(profit))} {word} "
        f"({format_pct(profit / result['baseline_gross_profit'], 1, signed=True)}); "
        f"hacim {format_pct(volume_change, 1, signed=True)} "
        "değişir. Bu bir tahmin değil, seçilen varsayımların aritmetik sonucudur."
    )
