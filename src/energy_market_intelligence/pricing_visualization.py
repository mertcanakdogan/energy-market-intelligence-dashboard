"""Plotly figures for the pricing case study (pipeline PNG exports and Streamlit pages)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from energy_market_intelligence.localization import (
    VALUE_LABELS,
    format_number,
    format_pct,
    order_segments,
)
from energy_market_intelligence.synthetic_data import FOCUS_COMPANY
from energy_market_intelligence.visualization import (
    FONT_BODY,
    FONT_MONO,
    GAIN_GREEN,
    GRID,
    INK,
    LEAK_RED,
    NAVY,
    NAVY_SOFT,
    SLATE,
    SLATE_SOFT,
    TL_AXIS,
    apply_business_theme,
)

# Line items of the price waterfall. The labels read like the lines of an electricity bill and
# are shared by the charts, the "fatura dökümü" block on the home page and the tables.
LIST_LABEL = "Liste fiyatı"
INVOICE_LABEL = "Fatura fiyatı"
NET_LABEL = "Net (cebe kalan) fiyat"
DEDUCTION_LABELS = {
    "on_invoice_discount": "Fatura içi iskonto",
    "off_invoice_rebate": "Fatura dışı prim",
    "payment_term_cost": "Vade maliyeti",
    "freight_service_cost": "Hizmet ve nakliye",
}
WATERFALL_STEPS = (
    (LIST_LABEL, "list_price", "absolute"),
    (DEDUCTION_LABELS["on_invoice_discount"], "on_invoice_discount", "relative"),
    (INVOICE_LABEL, "invoice_price", "total"),
    (DEDUCTION_LABELS["off_invoice_rebate"], "off_invoice_rebate", "relative"),
    (DEDUCTION_LABELS["payment_term_cost"], "payment_term_cost", "relative"),
    (DEDUCTION_LABELS["freight_service_cost"], "freight_service_cost", "relative"),
    (NET_LABEL, "pocket_price", "total"),
)
PORTFOLIO = "Tüm portföy"
AMOUNT_COLUMNS = {
    "list_price": "list_revenue",
    "on_invoice_discount": "on_invoice_discount_amount",
    "invoice_price": "invoice_revenue",
    "off_invoice_rebate": "off_invoice_rebate_amount",
    "payment_term_cost": "payment_term_cost_amount",
    "freight_service_cost": "freight_service_cost_amount",
    "pocket_price": "pocket_revenue",
}


def segment_waterfall_table(waterfall: pd.DataFrame) -> pd.DataFrame:
    """Volume-weighted per-MWh waterfall by customer segment from ``vw_price_waterfall``."""

    totals = waterfall.groupby("customer_segment_name", as_index=False)[
        ["volume_mwh", *AMOUNT_COLUMNS.values()]
    ].sum()
    for unit_column, amount_column in AMOUNT_COLUMNS.items():
        totals[unit_column] = totals[amount_column] / totals["volume_mwh"]
    ordered = order_segments(totals).reset_index(drop=True)
    return ordered[["customer_segment_name", "volume_mwh", *AMOUNT_COLUMNS]]


@dataclass(frozen=True)
class BillLine:
    """One line of the itemised price (TL/MWh) with its share of the list price."""

    label: str
    amount: float
    share_of_list: float
    kind: str  # "list", "deduction" or "net"


@dataclass(frozen=True)
class Bill:
    """The "fatura dökümü": list price down to the net (pocket) price per MWh."""

    scope: str
    lines: tuple[BillLine, ...]
    leakage_rate: float  # 1 - net / list: the share of the list price that never arrives


def portfolio_bill(waterfall: pd.DataFrame, segment: str | None = None) -> Bill:
    """Volume-weighted bill for the whole portfolio or a single customer segment."""

    selected = waterfall
    if segment is not None:
        selected = waterfall[waterfall["customer_segment_name"] == segment]
    if selected.empty:
        raise ValueError(f"No price waterfall rows for segment: {segment}")
    totals = selected[["volume_mwh", *AMOUNT_COLUMNS.values()]].sum()
    per_mwh = {
        name: float(totals[column] / totals["volume_mwh"])
        for name, column in AMOUNT_COLUMNS.items()
    }
    list_price = per_mwh["list_price"]
    lines = [BillLine(LIST_LABEL, list_price, 1.0, "list")]
    lines += [
        BillLine(label, per_mwh[name], per_mwh[name] / list_price, "deduction")
        for name, label in DEDUCTION_LABELS.items()
    ]
    net = per_mwh["pocket_price"]
    lines.append(BillLine(NET_LABEL, net, net / list_price, "net"))
    return Bill(segment or PORTFOLIO, tuple(lines), float(1 - net / list_price))


def bill_waterfall_figure(bill: Bill) -> go.Figure:
    """Horizontal waterfall that mirrors the bill lines one to one (TL/MWh)."""

    labels = [line.label for line in bill.lines]
    values = [-line.amount if line.kind == "deduction" else line.amount for line in bill.lines]
    measure = ["absolute" if line.kind == "list" else "relative" for line in bill.lines]
    measure[-1] = "total"
    values[-1] = 0.0  # Plotly derives the total bar from the running sum
    text = [
        f"−{format_number(line.amount, 0)}"
        if line.kind == "deduction"
        else format_number(line.amount, 0)
        for line in bill.lines
    ]
    figure = go.Figure(
        go.Waterfall(
            orientation="h",
            y=labels,
            x=values,
            measure=measure,
            text=text,
            textposition="outside",
            textfont={"family": FONT_MONO, "size": 13, "color": INK},
            decreasing={"marker": {"color": LEAK_RED}},
            increasing={"marker": {"color": NAVY}},
            totals={"marker": {"color": NAVY}},
            connector={"line": {"color": SLATE_SOFT, "width": 1}},
            hovertemplate="%{y}: %{text} TL/MWh<extra></extra>",
            showlegend=False,
        )
    )
    list_price, net = bill.lines[0].amount, bill.lines[-1].amount
    apply_business_theme(figure, mono_axis="x")
    figure.update_layout(margin={"l": 8, "r": 24, "t": 12, "b": 48}, height=380)
    figure.update_yaxes(
        autorange="reversed",
        showgrid=False,
        zeroline=False,
        ticksuffix="  ",
        tickfont={"family": FONT_BODY, "size": 13, "color": INK},
    )
    figure.update_xaxes(
        range=[net * 0.94, list_price * 1.06],
        showgrid=True,
        gridcolor=GRID,
        title="TL/MWh (eksen kesik)",
        tickformat=",d",
    )
    return figure


def price_waterfall_figure(waterfall: pd.DataFrame) -> go.Figure:
    """List-to-pocket price waterfall (per MWh) for each customer segment."""

    table = segment_waterfall_table(waterfall)
    segments = table["customer_segment_name"].tolist()
    figure = make_subplots(
        rows=1,
        cols=len(segments),
        subplot_titles=segments,
        shared_yaxes=True,
        horizontal_spacing=0.03,
    )
    for column, row in enumerate(table.itertuples(index=False), start=1):
        levels = [getattr(row, field) for _label, field, _measure in WATERFALL_STEPS]
        # Plotly derives "total" bars from the running sum, so their own y is 0.
        values = [
            0.0 if measure == "total" else (level if measure == "absolute" else -level)
            for (_label, _field, measure), level in zip(WATERFALL_STEPS, levels, strict=True)
        ]
        figure.add_trace(
            go.Waterfall(
                x=[label for label, _field, _measure in WATERFALL_STEPS],
                y=values,
                measure=[measure for _label, _field, measure in WATERFALL_STEPS],
                text=[format_number(level, 0) for level in levels],
                textposition="outside",
                increasing={"marker": {"color": NAVY}},
                decreasing={"marker": {"color": LEAK_RED}},
                totals={"marker": {"color": NAVY}},
                textfont={"family": FONT_MONO, "size": 12, "color": INK},
                connector={"line": {"color": SLATE_SOFT}},
                hoverinfo="x+text",
                showlegend=False,
            ),
            row=1,
            col=column,
        )
    figure.update_layout(title="Liste fiyattan cebe kalan fiyata (TL/MWh, 2025)")
    apply_business_theme(figure)
    figure.update_xaxes(tickangle=-40, tickfont={"size": 11})
    figure.update_yaxes(
        range=[float(table["pocket_price"].min()) * 0.9, float(table["list_price"].max()) * 1.04],
        tickformat=",d",
    )
    figure.update_yaxes(title="TL/MWh (sabit 2025 fiyatları, eksen kesik)", col=1)
    return figure


def pvm_bridge_figure(summary: pd.DataFrame) -> go.Figure:
    """Price-volume-mix bridge of net revenue and gross profit, latest 12 months vs prior 12."""

    row = summary.iloc[0]
    panels = (
        (
            "Net ciro değişimi (cebe kalan fiyatla)",
            [
                ("Hacim", row["volume_effect"]),
                ("Karışım", row["mix_effect"]),
                ("Fiyat", row["price_effect"]),
            ],
            ("Ciro değişimi", row["total_revenue_change"]),
        ),
        (
            "Brüt kâr değişimi",
            [
                ("Hacim", row["gp_volume_effect"]),
                ("Karışım", row["gp_mix_effect"]),
                ("Fiyat", row["gp_price_effect"]),
                ("Birim maliyet", row["gp_cost_effect"]),
            ],
            ("Toplam", row["total_gp_change"]),
        ),
    )
    figure = make_subplots(
        rows=1, cols=2, subplot_titles=[panel[0] for panel in panels], horizontal_spacing=0.1
    )
    for column, (_title, effects, (total_label, total)) in enumerate(panels, start=1):
        values = [value / 1e6 for _, value in effects] + [total / 1e6]
        figure.add_trace(
            go.Waterfall(
                x=[label for label, _ in effects] + [total_label],
                y=values,
                measure=["relative"] * len(effects) + ["total"],
                text=[format_number(value, 1, signed=True) for value in values],
                textposition="outside",
                increasing={"marker": {"color": NAVY_SOFT}},
                decreasing={"marker": {"color": SLATE}},
                totals={"marker": {"color": NAVY}},
                textfont={"family": FONT_MONO, "size": 12, "color": INK},
                connector={"line": {"color": SLATE_SOFT}},
                hovertemplate="%{x}: %{y:,.1f} mn TL<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=column,
        )
    figure.update_layout(
        title=f"{FOCUS_COMPANY}: fiyat-hacim-karışım köprüsü (2025, 2024 ile kıyas)"
    )
    return apply_business_theme(figure, y_title=TL_AXIS)


def _interval_trace(
    x: pd.Series, y: pd.Series, low: pd.Series, high: pd.Series, name: str
) -> go.Scatter:
    return go.Scatter(
        x=x,
        y=y,
        mode="markers",
        name=name,
        marker={"color": NAVY, "size": 11},
        error_x={
            "type": "data",
            "symmetric": False,
            "array": high - x,
            "arrayminus": x - low,
            "color": NAVY,
            "thickness": 2.5,
        },
    )


def elasticity_recovery_figure(table: pd.DataFrame) -> go.Figure:
    """Estimated elasticity with 95% CI next to the known true value, per segment."""

    table = order_segments(table).iloc[::-1]  # first segment at the top of the chart
    figure = go.Figure()
    figure.add_trace(
        _interval_trace(
            table["elasticity"],
            table["customer_segment_name"],
            table["ci_low"],
            table["ci_high"],
            "Tahmin (%95 güven aralığı)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=table["true_elasticity"],
            y=table["customer_segment_name"],
            mode="markers",
            name="Gerçek değer (veri üreticisi)",
            marker={
                "color": "#FFFFFF",
                "size": 13,
                "symbol": "diamond",
                "line": {"color": INK, "width": 2},
            },
        )
    )
    figure.add_vline(x=-1, line_dash="dot", line_color=SLATE, annotation_text="birim esneklik (-1)")
    figure.update_layout(title="Fiyat esnekliği: tahmin ve bilinen gerçek değer")
    apply_business_theme(figure, mono_axis="x")
    figure.update_yaxes(showgrid=False)
    figure.update_xaxes(
        title="Fiyat esnekliği: fiyat %1 artınca hacim yüzde kaç değişir? (cebe kalan fiyat)",
        showgrid=True,
        gridcolor=GRID,
    )
    return figure


def promo_did_figure(
    estimates: pd.DataFrame, trend: pd.DataFrame, window: tuple[int, int]
) -> go.Figure:
    """Treated-vs-control volume index and DiD uplift estimates against the true uplift."""

    figure = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.55, 0.45],
        subplot_titles=(
            "Hacim endeksi (kampanya öncesi = 100)",
            "Tahmini kampanya etkisi ve gerçek değer",
        ),
        horizontal_spacing=0.1,
    )
    for name, label, color in (
        ("control", "Kontrol bölgeleri", SLATE),
        ("treated", "Kampanya bölgeleri", NAVY),
    ):
        figure.add_trace(
            go.Scatter(
                x=trend["month_id"],
                y=trend[name],
                mode="lines+markers",
                name=label,
                line={"color": color, "width": 2.5},
                marker={"size": 4},
            ),
            row=1,
            col=1,
        )
    figure.add_vrect(
        x0=window[0] - 0.5,
        x1=window[1] + 0.5,
        fillcolor=SLATE_SOFT,
        opacity=0.3,
        line_width=0,
        row=1,
        col=1,
    )
    labels = estimates["method"].map(
        {"naive": VALUE_LABELS["naive"], "price_adjusted": VALUE_LABELS["price_adjusted"]}
    )
    figure.add_trace(
        _interval_trace(
            estimates["uplift"] * 100,
            labels,
            estimates["ci_low"] * 100,
            estimates["ci_high"] * 100,
            "Tahmin (%95 güven aralığı)",
        ),
        row=1,
        col=2,
    )
    truth = float(estimates["true_uplift"].iloc[0]) * 100
    figure.add_vline(
        x=truth,
        line_dash="dash",
        line_color=INK,
        annotation_text=f"gerçek {format_pct(truth / 100, 0)}",
        row=1,
        col=2,
    )
    figure.update_layout(title="Kampanya etkisi: farkların farkı (DiD) yöntemi")
    apply_business_theme(figure)
    figure.update_layout(
        legend={"orientation": "h", "yanchor": "top", "y": -0.2, "x": 0},
        margin={"l": 65, "r": 30, "t": 80, "b": 120},
    )
    figure.update_xaxes(title="Ay (1 = Ocak 2023, 36 = Aralık 2025)", row=1, col=1)
    figure.update_xaxes(title="Ek hacim etkisi (%)", row=1, col=2, showgrid=True)
    return figure


def price_recommendation_figure(table: pd.DataFrame) -> go.Figure:
    """Expected 12-month gross-profit change by segment with the elasticity-CI range."""

    ordered = table.sort_values("expected_gross_profit_change")
    labels = [
        f"{row.customer_segment_name}<br>"
        f"fiyat {format_pct(row.price_change_pct, 1, signed=True)}, "
        f"hacim {format_pct(row.expected_volume_change_pct, 1, signed=True)}"
        for row in ordered.itertuples(index=False)
    ]
    expected = ordered["expected_gross_profit_change"] / 1e6
    figure = go.Figure(
        go.Bar(
            x=expected,
            y=labels,
            orientation="h",
            marker_color=GAIN_GREEN,
            text=[f"{format_number(value, 1, signed=True)} mn TL" for value in expected],
            textposition="inside",
            insidetextanchor="middle",
            textfont={"family": FONT_MONO, "color": "white", "size": 15},
            error_x={
                "type": "data",
                "symmetric": False,
                "array": ordered["gross_profit_change_high"] / 1e6 - expected,
                "arrayminus": expected - ordered["gross_profit_change_low"] / 1e6,
                "color": INK,
                "thickness": 2,
            },
            hovertemplate="%{y}: %{x:,.1f} mn TL<extra></extra>",
        )
    )
    figure.update_layout(title="Önerilen fiyat adımı: beklenen 12 aylık brüt kâr değişimi")
    apply_business_theme(figure, mono_axis="x")
    figure.update_yaxes(
        showgrid=False, ticksuffix="  ", tickfont={"family": FONT_BODY, "size": 13, "color": INK}
    )
    figure.update_layout(margin={"l": 210, "r": 30, "t": 70, "b": 60})
    figure.update_xaxes(
        title="mn TL, sabit 2025 fiyatları (çubuk = tahmin, çizgi = esneklik güven aralığı)"
    )
    return figure
