# Synthetic sample-data generation

The repository does not ship a manually curated raw dataset. Run:

```bash
python -m energy_market_intelligence.pipeline
```

This creates deterministic CSV tables under `data/generated/` and a local DuckDB file at `data/energy_market.duckdb`. Both are Git-ignored.

## Declared grain

One `fact_sales` row represents:

```text
month × region × company × product
```

The default run contains 36 months, 18 sales provinces of Turkey (with invented figures), seven fictional companies named "<invented word> Energy", and four products. The column `region_name` (the internal name is kept) holds the province name. `dim_customer_segment` has no `customer_segment_en` column, because the segment names (Residential, Commercial (SME), Industrial) are already English. All amounts are Turkish lira (TRY) at constant 2025 prices; the 36 months run from January 2023 to December 2025. The generator combines explicit seasonality, region and product growth, company momentum, pricing positions, cost inflation, a temporary margin-compression interval, and seeded noise. These assumptions are public-demo constructs only and are not calibrated to a real business.

## Pricing ledger

The same run also generates `fact_pricing`, one row per:

```text
month × region × product × customer segment
```

with 36 × 18 × 4 × 3 = 7,776 rows. It carries a list-to-pocket price waterfall (TRY per MWh), unit variable cost, competitor price and a promotion flag. Its demand follows a constant-elasticity model whose true parameters (own-price elasticity by segment, cross elasticity, promotion uplift) and the staggered list-price increases are documented in the `pricing:` section of `config/default.yaml`, so analytics can be checked against the truth.
