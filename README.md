[![Tests](https://github.com/mertcanakdogan/energy-market-intelligence-dashboard/actions/workflows/tests.yml/badge.svg)](https://github.com/mertcanakdogan/energy-market-intelligence-dashboard/actions/workflows/tests.yml)

# Northstar Energy — Pricing & Revenue Analytics

> A pricing and revenue-management case study on a fictional energy retailer: price waterfall, price-volume-mix bridge, price elasticity, promotion impact and a price-recommendation decision aid, built on a SQL (DuckDB) star schema with a Streamlit app and a Power BI model specification.

All data are **synthetic and generated with a known ground truth**: the true price elasticities and the true promotion uplift are set in [`config/default.yaml`](config/default.yaml), so every estimate in this repository can be checked against the real answer.

## Executive summary

**Business question:** where should Northstar change prices, and what is it worth?

![Northstar price waterfall by customer segment](outputs/examples/price_waterfall.png)

All figures are synthetic currency units for the latest 12 months and come from [`outputs/examples/`](outputs/examples/) and `run_metadata.json`.

**Key findings**

1. **Price realization is 85.2%.** Of 128.5M list revenue, 109.4M reaches the pocket. Leakage is highest for Industrial customers (pocket 72.44 per MWh against a list of 92.74, a 21.9% gap) versus Residential (83.60, 9.8%) and SME (79.35, 14.4%). Discounting also exceeds policy in 4 regions (Blue Mesa, Western Reach, Highland Zone, Central Basin; 12 region-segment cells), worth 0.54M of revenue given away above policy. In Blue Mesa, Highland Zone and Western Reach the Industrial pocket margin is only 7.2% to 9.9%.
2. **Revenue grew, gross profit did not.** Versus the prior 12 months, net revenue rose 4.75M (volume +3.70M, price +1.07M, mix -0.02M), but gross profit fell 1.02M because unit cost rose 2.89M. Price increases recovered about 37% of the cost increase.
3. **Demand differs sharply by segment, and the model finds it.** Estimated elasticities are Residential -1.60 (elastic), SME -1.10 (borderline; its 95% CI of -1.23 to -0.98 includes -1) and Industrial -0.61 (inelastic). The 8% discount-campaign effect is estimated at 8.7% (95% CI 7.9% to 9.6%) after adjusting for price, while a naive before/after comparison reports 12.0%.

**Recommendation:** take a capped pocket-price step in every segment (Industrial +5.0%, SME +4.8%, Residential +3.3%, limited by the 5% step cap and a 5% volume-loss guard) and close discount leakage in the four breaching regions. The model expects gross profit to rise by 3.41M (+15.5% on a 22.08M baseline; 3.29M to 3.54M across the elasticity confidence interval) for a 2.9% to 5.0% volume loss. This is a decision aid built on constant-elasticity assumptions; see [Limitations](#limitations).

![Recommended price step and expected gross-profit change](outputs/examples/price_recommendation.png)

## How we know the model works

Because the generator's parameters are known, the estimators are tested for recovery. Elasticities are estimated by log-log OLS per customer segment (month-of-year dummies, region x product fixed effects, trend, log competitor price, region-clustered standard errors):

| Segment | True elasticity | Estimate | Std. error | 95% CI | Truth inside CI |
|---|---:|---:|---:|---|:---:|
| Residential | -1.60 | -1.598 | 0.075 | [-1.758, -1.439] | yes |
| SME | -1.10 | -1.103 | 0.059 | [-1.228, -0.977] | yes |
| Industrial | -0.60 | -0.605 | 0.035 | [-0.680, -0.530] | yes |

Promotion uplift by difference-in-differences (5 treated and 13 control regions, months 25 to 28):

| Estimator | True uplift | Estimate | 95% CI | Truth inside CI |
|---|---:|---:|---|:---:|
| Naive 2 x 2 DiD | 8.0% | 12.0% | [10.2%, 13.8%] | no (biased: counts the campaign price cut and list-price drift) |
| Price-adjusted two-way fixed-effects DiD | 8.0% | 8.7% | [7.9%, 9.6%] | yes |

| Elasticity recovery | Promotion DiD |
|---|---|
| ![Elasticity recovery](outputs/examples/elasticity_recovery.png) | ![Promotion DiD](outputs/examples/promo_did.png) |

One draw can miss: a 95% interval misses the truth about 1 time in 20. `tests/test_elasticity.py` therefore also re-draws the pricing noise for six other seeds and requires at least 85% coverage and a mean bias below 0.08.

## Business questions answered

- Where does list price leak to pocket price, and which regions discount beyond policy? (`vw_price_waterfall`, `vw_discount_policy_flags`)
- Why did revenue and gross profit move: price, volume, mix or cost? (`vw_pvm_bridge`)
- How price-sensitive is each customer segment? (`elasticity.py`)
- Did the discount campaign create incremental volume? (`promotion.py`)
- What price step is worth taking, within margin and volume guard rails? (`price_recommendation.py`)
- Market context: growth, Northstar share, competitor momentum, regional opportunity and profitability (the original market-intelligence pages).

## Data model

Two synthetic fact tables share the date, region and product dimensions.

| Table | Grain | Purpose |
|---|---|---|
| `fact_sales` | month x region x company x product | Market view: volume, price, revenue and cost for Northstar and six fictional competitors |
| **`fact_pricing`** | **month x region x product x customer segment** | Northstar pricing ledger: list, discount, rebate, payment-term and freight cost, pocket price, unit cost, competitor price, promo flag |
| `dim_customer_segment` | segment | Residential, SME, Industrial |
| `dim_discount_policy` | segment | Policy maximum on-invoice discount depth |
| `dim_date`, `dim_region`, `dim_company`, `dim_product` | | Shared dimensions |

`fact_pricing` has 7,776 rows (36 months x 18 regions x 4 products x 3 segments). Its volume scale is calibrated to the market fact, but it is a separate ledger and not a reconciled split of `fact_sales`.

Ground truth built into the pricing generator (all in `config/default.yaml`, `pricing:` section):

- **Waterfall:** list price, minus on-invoice discount, equals invoice price; minus off-invoice rebate, payment-term cost and freight/service cost, equals pocket price. Discount depth increases from Residential to Industrial, and four leakage regions sit above policy.
- **Identifying price variation:** staggered list-price increases by region (months 7, 14, 21 and 28) plus small random monthly discount noise. One region never changes its list price.
- **Demand:** `log(volume) = region-product-segment intercept + seasonality + trend + elasticity x log(pocket price) + 0.35 x log(competitor price) + log(1.08) x promo + noise`, with true elasticities -1.6, -1.1 and -0.6.
- **Promotion:** 5 treated regions get an extra 3% on-invoice discount and a non-price volume uplift of +8% for four months; 13 regions are controls.

## SQL layer

Numbered files in [`sql/`](sql/) run in order against registered dataframes:

| File | Content |
|---|---|
| `01_schema.sql` | Star-schema tables and indexes (market and pricing facts) |
| `02_market_metrics.sql` | Company monthly share, market volume, rolling 3/6-month averages, YoY, MoM |
| `03_growth_analysis.sql` | National growth and share trend |
| `04_competitor_intelligence.sql` | Competitor momentum, regional ranks, HHI concentration |
| `05_profitability.sql` | Profitability summaries and the original revenue bridge |
| `06_regional_opportunity.sql` | Regional opportunity inputs |
| `07_executive_kpis.sql` | Executive KPI view |
| `08_price_waterfall.sql` | Pricing detail, list-to-pocket waterfall, leakage, policy flags and ranking |
| `09_pvm_bridge.sql` | Price-volume-mix bridge for net revenue and gross profit |

## Methods and assumptions

**Price waterfall.** Per-MWh values are volume-weighted (`SUM(amount) / SUM(volume)`). Leakage = (list - pocket) / list. A region-segment cell breaches policy when its list-weighted on-invoice discount depth exceeds the segment maximum; revenue above policy = excess depth x list revenue.

**PVM bridge.** Latest 12 months versus the prior 12 at product x segment level, on net (pocket) revenue and on gross profit. With total volumes VT0/VT1, cell shares s and cell net prices P0/P1:

```text
Volume effect = (VT1 - VT0) x s0 x P0
Mix effect    = VT1 x (s1 - s0) x P0
Price effect  = V1 x (P1 - P0)
```

These sum exactly to the revenue change (view column `reconciliation_gap`, asserted ~0 in tests). Gross profit uses the unit margin for volume and mix and adds a unit-cost effect of `-V1 x (C1 - C0)`. A cell absent in one period takes its price from the other, so the identity still holds.

**Elasticity.** Log-log OLS per segment: `log(volume) ~ log(pocket price) + log(competitor price) + trend + month-of-year + region x product fixed effects + promo`, with region-clustered standard errors and t-based 95% intervals. Price variation that is unrelated to demand shocks (staggered list increases, discount noise) identifies the slope; region and product fixed effects absorb permanent differences such as leakage regions.

**Promotion DiD.** Treated = regions that ever carry the campaign flag; pre = months before, post = campaign months. The adjusted model has region x product x segment and month fixed effects, segment-specific pocket-price slopes and competitor price. Identifying assumption: parallel trends once price is controlled for.

**Price recommendation** (`price_recommendation.py`). Per segment (optionally per region), using the estimated elasticity `e`, current pocket price and unit cost `c`:

1. Elastic (`e < -1`): target the profit-maximising pocket price `c x e / (1 + e)`. Inelastic: target the largest allowed step.
2. Limit every move to the step cap (+/-5%).
3. Limit increases to the price at which expected volume loss reaches the guard (5%).
4. Enforce a pocket-margin floor (15%) last; if it cannot be reached within the step cap, apply the full step and flag the group.

Expected volume change is `(1 + price change)^e - 1`; gross-profit bounds use the elasticity confidence limits. With this data the unconstrained optimum for the elastic segment is far outside the observed price range, so the step cap and volume guard decide the result. Three Industrial regions (Blue Mesa, Highland Zone, Western Reach) cannot reach the 15% floor in one step.

**Scenario page.** The original arithmetic scenario function is unchanged. The page can now derive the volume response from the estimated elasticity of a chosen customer segment (with a sensitivity table over its confidence interval) or use a manual override.

## Limitations

- All data are synthetic. Results demonstrate method and recovery of known parameters; they are not calibrated to any real market.
- Elasticity is constant by construction, in line with the model that is estimated. Real demand is rarely constant-elasticity over large moves, so recommendations are limited to small steps.
- Competitors do not react to Northstar price changes, and unit costs are held fixed in the recommendation.
- Estimated elasticities are per customer segment and are applied unchanged to every region and product.
- The pricing ledger is a separate sub-ledger; it is not reconciled to `fact_sales`.
- The promotion regions were assigned by the generator, not randomly; parallel trends is an assumption that must be checked on real data.
- Recommendations are a decision aid, not an automated pricing rule, and ignore contract terms, competitor positioning and regulation.
- The Power BI DAX measures are documented but were not executed in Power BI Desktop for this repository.

## Run locally

Python 3.12 is the reference version used by CI; the suite also passes on Python 3.14. Chrome or Chromium is only needed by Kaleido for PNG export in the pipeline.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1   |   macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m energy_market_intelligence.pipeline   # data, SQL models, analyses, outputs/examples, powerbi/data
streamlit run app.py
pytest --cov                                    # tests (coverage floor 85%)
ruff check .
```

If `data/energy_market.duckdb` does not exist, the app builds it on first start.

## Live demo

Live demo: see [DEPLOY.md](DEPLOY.md).

## Power BI

[`powerbi/measures.md`](powerbi/measures.md) documents the data model (relationships) and DAX measures: Pocket Price, Price Realization %, Discount Leakage, Discount Above Policy, Gross Margin %, YoY, rolling 12 months and the PVM components with a reconciliation check. The pipeline exports the tidy star schema (`fact_pricing` and dimensions) to `powerbi/data/*.csv` (git-ignored). No `.pbix` file is included.

## Project structure

```text
config/default.yaml              Run settings, opportunity weights and the pricing ground truth
sql/                             Numbered DuckDB models 01-09
src/energy_market_intelligence/
    synthetic_data.py            Market star-schema generator
    pricing_config.py            Typed pricing configuration / ground truth
    pricing_data.py              Pricing generator (waterfall, demand, promotion)
    validation.py                Fail-loud data contracts, including the waterfall identity
    database.py                  DuckDB build and read-only queries
    elasticity.py                Segment elasticity estimation
    promotion.py                 Difference-in-differences promotion uplift
    price_recommendation.py      Capped, margin-floored price steps
    scenario.py                  What-if arithmetic and elasticity-implied volume response
    visualization.py, pricing_visualization.py   Plotly figures
    powerbi_export.py            Star-schema CSV export
    pipeline.py                  End-to-end build and example outputs
app.py, pages/, dashboard_support.py   Streamlit app (pricing pages 01-05, scenario, market pages)
powerbi/measures.md              Power BI model and DAX
tests/                           Unit, SQL, pipeline, page-smoke and repository-hygiene tests
outputs/examples/                Compact CSV and PNG results plus run_metadata.json
DEPLOY.md, requirements.txt      Streamlit Community Cloud deployment
```

## Market-intelligence modules (original scope)

The repository started as a market-intelligence dashboard and keeps it: monthly company share, market growth, competitor momentum, HHI concentration, profitability, a regional Opportunity Score (min-max scaled weights from `config/default.yaml`) and a base-period revenue bridge. Market shares are fractions from 0 to 1 and HHI is the sum of squared shares (labels below 0.15 fragmented, 0.15 to below 0.25 moderate, 0.25 and above concentrated; generic context, not a regulatory assessment). The Opportunity Score is a transparent prioritisation heuristic, not a causal model.

## Confidentiality

This is an independent portfolio project built entirely with synthetic data. It contains no employer data, customer data, proprietary pricing logic or internal business rules; company and region names are fictional. The repository is guarded by `tests/test_repo_hygiene.py`, which scans all tracked text files for real energy-company names, e-mail addresses, local paths, cloud-sync paths and secret-like strings. Generated raw data and the DuckDB file are git-ignored.

## Author

**Mert Can Akdoğan**

## License

[MIT](LICENSE)
