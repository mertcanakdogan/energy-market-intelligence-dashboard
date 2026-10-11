# Power BI model and DAX measures

This folder documents how to build a Power BI report on the pricing star schema. **No `.pbix` file
is included** and the DAX below has not been executed in Power BI Desktop as part of this
repository's tests. The price-volume-mix logic mirrors `sql/09_pvm_bridge.sql`, whose exact
reconciliation is covered by automated tests.

## 1. Generate the data

```bash
python -m energy_market_intelligence.pipeline
```

The pipeline writes tidy CSV files to `powerbi/data/` (git-ignored, regenerated on every run;
the export code is `src/energy_market_intelligence/powerbi_export.py`):

| File | Grain | Role |
|---|---|---|
| `fact_pricing.csv` | month x region x product x customer segment | fact |
| `dim_date.csv` | month | dimension (first-of-month dates) |
| `dim_region.csv` | region | dimension |
| `dim_product.csv` | product | dimension |
| `dim_customer_segment.csv` | customer segment | dimension |
| `dim_discount_policy.csv` | customer segment | policy threshold (`max_discount_pct`) |

Load them with *Get data > Text/CSV*. Set `dim_date[date]` to type Date and `promo_flag` to whole
number. Hide the key columns in report view.

## 2. Data model

```text
dim_date ───────────┐
dim_region ─────────┤  1:*   (single direction, dimension -> fact)
dim_product ────────┼──────►  fact_pricing
dim_customer_segment┘
dim_customer_segment ◄──1:1──► dim_discount_policy
```

| From (one side) | To (many side) | Key |
|---|---|---|
| `dim_date[month_id]` | `fact_pricing[month_id]` | month_id |
| `dim_region[region_id]` | `fact_pricing[region_id]` | region_id |
| `dim_product[product_id]` | `fact_pricing[product_id]` | product_id |
| `dim_customer_segment[customer_segment_id]` | `fact_pricing[customer_segment_id]` | customer_segment_id |
| `dim_customer_segment[customer_segment_id]` | `dim_discount_policy[customer_segment_id]` | 1:1 |

`dim_date` has one row per month, so it is not a contiguous daily calendar. The year-over-year and
last-12-month measures therefore shift `month_id` instead of using `DATEADD`.

Fact amount columns (`*_amount`, `*_revenue`, `variable_cost`, `gross_profit`) are totals in
synthetic currency units; per-unit columns (`list_price`, `pocket_price`, ...) are per MWh and must
be volume-weighted, never averaged. The measures below do that.

## 3. Waterfall measures

```DAX
Volume MWh = SUM ( fact_pricing[volume_mwh] )

List Revenue = SUM ( fact_pricing[list_revenue] )
On-invoice Discount = SUM ( fact_pricing[on_invoice_discount_amount] )
Invoice Revenue = SUM ( fact_pricing[invoice_revenue] )
Off-invoice Rebates = SUM ( fact_pricing[off_invoice_rebate_amount] )
Payment Term Cost = SUM ( fact_pricing[payment_term_cost_amount] )
Freight and Service Cost = SUM ( fact_pricing[freight_service_cost_amount] )
Pocket Revenue = SUM ( fact_pricing[pocket_revenue] )

List Price = DIVIDE ( [List Revenue], [Volume MWh] )
Invoice Price = DIVIDE ( [Invoice Revenue], [Volume MWh] )
Pocket Price = DIVIDE ( [Pocket Revenue], [Volume MWh] )

Discount Depth % = DIVIDE ( [On-invoice Discount], [List Revenue] )
Price Realization % = DIVIDE ( [Pocket Revenue], [List Revenue] )
Discount Leakage = [List Revenue] - [Pocket Revenue]
Discount Leakage % = DIVIDE ( [Discount Leakage], [List Revenue] )
```

Check: `[List Revenue] - [On-invoice Discount] - [Off-invoice Rebates] - [Payment Term Cost] -
[Freight and Service Cost]` equals `[Pocket Revenue]` (use a card or a measure to confirm).

### Discount above policy

Revenue given away on-invoice beyond the segment's policy depth, evaluated per region and segment:

```DAX
Discount Above Policy =
SUMX (
    SUMMARIZE (
        fact_pricing,
        dim_region[region_name],
        dim_customer_segment[customer_segment_name]
    ),
    VAR Depth = [Discount Depth %]
    VAR PolicyMax = CALCULATE ( MAX ( dim_discount_policy[max_discount_pct] ) )
    VAR ListRev = [List Revenue]
    RETURN MAX ( Depth - PolicyMax, 0 ) * ListRev
)

Regions Above Policy =
COUNTROWS (
    FILTER (
        SUMMARIZE (
            fact_pricing,
            dim_region[region_name],
            dim_customer_segment[customer_segment_name]
        ),
        [Discount Depth %] > CALCULATE ( MAX ( dim_discount_policy[max_discount_pct] ) )
    )
)
```

## 4. Margin measures

```DAX
Variable Cost = SUM ( fact_pricing[variable_cost] )
Gross Profit = SUM ( fact_pricing[gross_profit] )
Gross Margin % = DIVIDE ( [Gross Profit], [Pocket Revenue] )
Unit Variable Cost = DIVIDE ( [Variable Cost], [Volume MWh] )
Profit per MWh = DIVIDE ( [Gross Profit], [Volume MWh] )
```

## 5. Time intelligence: YoY and rolling 12 months

```DAX
Latest Month Id = CALCULATE ( MAX ( dim_date[month_id] ), REMOVEFILTERS ( dim_date ) )

Pocket Revenue PY =
VAR ShiftedMonths =
    SELECTCOLUMNS ( VALUES ( dim_date[month_id] ), "month_id", dim_date[month_id] - 12 )
RETURN
    CALCULATE ( [Pocket Revenue], REMOVEFILTERS ( dim_date ), TREATAS ( ShiftedMonths, dim_date[month_id] ) )

Pocket Revenue YoY % = DIVIDE ( [Pocket Revenue] - [Pocket Revenue PY], [Pocket Revenue PY] )

Gross Profit PY =
VAR ShiftedMonths =
    SELECTCOLUMNS ( VALUES ( dim_date[month_id] ), "month_id", dim_date[month_id] - 12 )
RETURN
    CALCULATE ( [Gross Profit], REMOVEFILTERS ( dim_date ), TREATAS ( ShiftedMonths, dim_date[month_id] ) )

Gross Profit YoY = [Gross Profit] - [Gross Profit PY]

-- Last 12 months (L12M) versus the 12 months before (P12M); ignores the date slicer.
Volume L12M =
CALCULATE ( [Volume MWh], REMOVEFILTERS ( dim_date ),
    dim_date[month_id] > [Latest Month Id] - 12, dim_date[month_id] <= [Latest Month Id] )
Volume P12M =
CALCULATE ( [Volume MWh], REMOVEFILTERS ( dim_date ),
    dim_date[month_id] > [Latest Month Id] - 24, dim_date[month_id] <= [Latest Month Id] - 12 )
Revenue L12M =
CALCULATE ( [Pocket Revenue], REMOVEFILTERS ( dim_date ),
    dim_date[month_id] > [Latest Month Id] - 12, dim_date[month_id] <= [Latest Month Id] )
Revenue P12M =
CALCULATE ( [Pocket Revenue], REMOVEFILTERS ( dim_date ),
    dim_date[month_id] > [Latest Month Id] - 24, dim_date[month_id] <= [Latest Month Id] - 12 )
Cost L12M =
CALCULATE ( [Variable Cost], REMOVEFILTERS ( dim_date ),
    dim_date[month_id] > [Latest Month Id] - 12, dim_date[month_id] <= [Latest Month Id] )
Cost P12M =
CALCULATE ( [Variable Cost], REMOVEFILTERS ( dim_date ),
    dim_date[month_id] > [Latest Month Id] - 24, dim_date[month_id] <= [Latest Month Id] - 12 )
```

## 6. Price-volume-mix (PVM) components

Cells are product x customer segment. With total volumes `VT0`/`VT1`, cell volumes `V0`/`V1`, cell
shares `s = V / VT` and cell net prices `P0`/`P1` (prior/current 12 months):

| Component | Formula per cell |
|---|---|
| Volume effect | `(VT1 - VT0) x s0 x P0` |
| Mix effect | `VT1 x (s1 - s0) x P0` |
| Price effect | `V1 x (P1 - P0)` |
| Unit-cost effect (gross profit) | `-V1 x (C1 - C0)` |

The three revenue components sum exactly to `V1 x P1 - V0 x P0` per cell. If a cell has no volume
in one period its price is taken from the other period, so its price effect is zero.

```DAX
PVM Volume Effect =
VAR VT0 = [Volume P12M]
VAR VT1 = [Volume L12M]
VAR Cells =
    CALCULATETABLE (
        SUMMARIZE ( fact_pricing, dim_product[product_name], dim_customer_segment[customer_segment_name] ),
        REMOVEFILTERS ( dim_date )
    )
RETURN
    SUMX (
        Cells,
        VAR P1 = DIVIDE ( [Revenue L12M], [Volume L12M] )
        VAR P0 = COALESCE ( DIVIDE ( [Revenue P12M], [Volume P12M] ), P1 )
        RETURN ( VT1 - VT0 ) * DIVIDE ( [Volume P12M], VT0 ) * P0
    )

PVM Mix Effect =
VAR VT0 = [Volume P12M]
VAR VT1 = [Volume L12M]
VAR Cells =
    CALCULATETABLE (
        SUMMARIZE ( fact_pricing, dim_product[product_name], dim_customer_segment[customer_segment_name] ),
        REMOVEFILTERS ( dim_date )
    )
RETURN
    SUMX (
        Cells,
        VAR P1 = DIVIDE ( [Revenue L12M], [Volume L12M] )
        VAR P0 = COALESCE ( DIVIDE ( [Revenue P12M], [Volume P12M] ), P1 )
        RETURN VT1 * ( DIVIDE ( [Volume L12M], VT1 ) - DIVIDE ( [Volume P12M], VT0 ) ) * P0
    )

PVM Price Effect =
VAR Cells =
    CALCULATETABLE (
        SUMMARIZE ( fact_pricing, dim_product[product_name], dim_customer_segment[customer_segment_name] ),
        REMOVEFILTERS ( dim_date )
    )
RETURN
    SUMX (
        Cells,
        VAR P1 = DIVIDE ( [Revenue L12M], [Volume L12M] )
        VAR P0 = COALESCE ( DIVIDE ( [Revenue P12M], [Volume P12M] ), P1 )
        RETURN [Volume L12M] * ( P1 - P0 )
    )

PVM Total Revenue Change = [Revenue L12M] - [Revenue P12M]

PVM Reconciliation Gap =
[PVM Total Revenue Change] - ( [PVM Volume Effect] + [PVM Mix Effect] + [PVM Price Effect] )
```

### Gross-profit bridge

Volume and mix use the cell unit margin `M0 = P0 - C0` instead of `P0`; the price effect is
unchanged and a unit-cost effect is added.

```DAX
PVM GP Volume Effect =
VAR VT0 = [Volume P12M]
VAR VT1 = [Volume L12M]
VAR Cells =
    CALCULATETABLE (
        SUMMARIZE ( fact_pricing, dim_product[product_name], dim_customer_segment[customer_segment_name] ),
        REMOVEFILTERS ( dim_date )
    )
RETURN
    SUMX (
        Cells,
        VAR P1 = DIVIDE ( [Revenue L12M], [Volume L12M] )
        VAR P0 = COALESCE ( DIVIDE ( [Revenue P12M], [Volume P12M] ), P1 )
        VAR C1 = DIVIDE ( [Cost L12M], [Volume L12M] )
        VAR C0 = COALESCE ( DIVIDE ( [Cost P12M], [Volume P12M] ), C1 )
        RETURN ( VT1 - VT0 ) * DIVIDE ( [Volume P12M], VT0 ) * ( P0 - C0 )
    )

PVM GP Mix Effect =
VAR VT0 = [Volume P12M]
VAR VT1 = [Volume L12M]
VAR Cells =
    CALCULATETABLE (
        SUMMARIZE ( fact_pricing, dim_product[product_name], dim_customer_segment[customer_segment_name] ),
        REMOVEFILTERS ( dim_date )
    )
RETURN
    SUMX (
        Cells,
        VAR P1 = DIVIDE ( [Revenue L12M], [Volume L12M] )
        VAR P0 = COALESCE ( DIVIDE ( [Revenue P12M], [Volume P12M] ), P1 )
        VAR C1 = DIVIDE ( [Cost L12M], [Volume L12M] )
        VAR C0 = COALESCE ( DIVIDE ( [Cost P12M], [Volume P12M] ), C1 )
        RETURN
            VT1 * ( DIVIDE ( [Volume L12M], VT1 ) - DIVIDE ( [Volume P12M], VT0 ) ) * ( P0 - C0 )
    )

PVM GP Unit-cost Effect =
VAR Cells =
    CALCULATETABLE (
        SUMMARIZE ( fact_pricing, dim_product[product_name], dim_customer_segment[customer_segment_name] ),
        REMOVEFILTERS ( dim_date )
    )
RETURN
    SUMX (
        Cells,
        VAR C1 = DIVIDE ( [Cost L12M], [Volume L12M] )
        VAR C0 = COALESCE ( DIVIDE ( [Cost P12M], [Volume P12M] ), C1 )
        RETURN - [Volume L12M] * ( C1 - C0 )
    )

PVM GP Total Change = ( [Revenue L12M] - [Cost L12M] ) - ( [Revenue P12M] - [Cost P12M] )

PVM GP Reconciliation Gap =
[PVM GP Total Change]
    - ( [PVM GP Volume Effect] + [PVM GP Mix Effect] + [PVM Price Effect] + [PVM GP Unit-cost Effect] )
```

## 7. Suggested report pages

1. **Waterfall**: waterfall visual (list, discount, rebates, payment terms, freight, pocket) by
   segment; matrix of `Discount Depth %` and `Discount Above Policy` by region x segment.
2. **PVM bridge**: waterfall visual on the PVM measures plus `PVM Reconciliation Gap` and
   `PVM GP Reconciliation Gap` as cards that should read 0. Compare with `outputs/examples/pvm_bridge.csv`.
3. **Margin trend**: line chart of `Gross Margin %` and `Pocket Price` by month with a YoY card.
