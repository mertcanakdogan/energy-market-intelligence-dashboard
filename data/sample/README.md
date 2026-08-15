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

The default run contains 36 months, 18 fictional regions, seven fictional companies, and four generic product segments. The generator combines explicit seasonality, region and product growth, company momentum, pricing positions, cost inflation, a temporary margin-compression interval, and seeded noise. These assumptions are public-demo constructs only and are not calibrated to a real business.
