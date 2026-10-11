[![Tests](https://github.com/mertcanakdogan/energy-market-intelligence-dashboard/actions/workflows/tests.yml/badge.svg)](https://github.com/mertcanakdogan/energy-market-intelligence-dashboard/actions/workflows/tests.yml)

# Tavra Enerji: Pricing and Revenue Analytics

A case study for a **fictional Turkish electricity retailer**. It answers one business question: *where should the company change its prices, and what is that worth?* The data are synthetic, so every result can be checked against the true answer.

**[Open the live app](https://northstar-pricing.streamlit.app)** (the app text is in Turkish; this README is in English).

All money is in Turkish lira (TL) at **constant 2025 prices**, so the numbers contain no inflation. The data cover January 2023 to December 2025; "the latest 12 months" means calendar year 2025.

## Türkçe özet

Bu proje, kurgusal bir elektrik perakende şirketi (Tavra Enerji) için fiyatlama ve gelir analitiği vaka çalışmasıdır. Tüm veriler sentetiktir; şirket ve bölge adları kurgusaldır, tutarlar sabit 2025 fiyatlarıyla TL'dir.

- 2025'te liste fiyatlı 5,50 milyar TL'lik satıştan 4,69 milyar TL cebe kalmıştır (fiyat gerçekleşme oranı %85,2). Kayıp en çok sanayide: liste fiyatın %21,9'u.
- Dört bölgede indirimler izin verilen sınırı aşıyor; bu fazladan indirim yılda 23,4 milyon TL tutuyor.
- Net ciro 186,9 milyon TL artmış, brüt kâr ise 36,3 milyon TL azalmış: enerji maliyeti artışı (122,4 milyon TL) fiyat artışlarından büyük.
- Talep segmente göre farklı: mesken fiyata duyarlı (esneklik -1,60), sanayi çok az duyarlı (-0,61).
- Öneri: segmentlere göre en fazla %5'lik, sınırlı fiyat adımları ve politika dışı indirimlerin kapatılması. Brüt kârın yılda yaklaşık 145,2 milyon TL (%14,9) artması beklenir (aralık: 139,6 ile 150,9 milyon TL); hacim kaybı %2,9 ile %5,0 arasındadır.

## Key terms

| Term | Plain meaning |
|---|---|
| **List price** | The price on the price list, in TL per MWh (megawatt-hour of electricity). |
| **Price waterfall** | A chart that walks from the list price down to the money the company really keeps, one deduction at a time. |
| **Pocket price** | What is left after every discount, rebate, payment-term cost and service cost. This is the price that matters for profit. |
| **Price realization** | Pocket revenue divided by list revenue: how much of the list price survives. |
| **PVM bridge** | Price-volume-mix bridge. It splits a change in revenue or profit into a price effect, a volume effect and a product/customer mix effect (and a unit-cost effect for profit). |
| **Elasticity** | How much sales volume falls when the price rises by 1%. An elasticity of -1.6 means a 1% price rise loses about 1.6% of volume. Below -1 the segment is "elastic" (price sensitive). |
| **DiD (difference-in-differences)** | Compares regions that ran a promotion with regions that did not, to isolate the extra volume the promotion really created. |
| **95% CI (confidence interval)** | The range in which the true value should lie in 95 out of 100 repeated draws. |
| **Gross margin** | Net revenue minus energy cost, divided by net revenue. |

## Executive summary

**Business question:** where should Tavra Enerji change prices, and what is it worth?

![Price waterfall by customer segment](outputs/examples/price_waterfall.png)

All figures are for 2025 (compared with 2024 where stated), in constant 2025 TL, and come from [`outputs/examples/`](outputs/examples/) and `run_metadata.json`.

**Three findings**

1. **15% of the list price never reaches the company.** Of TL 5.50bn list revenue, TL 4.69bn is kept (price realization 85.2%). The gap is widest for industrial customers (Sanayi): list price 3,735 TL/MWh, pocket price 2,918 TL/MWh, a 21.9% gap, against 9.7% for households (Mesken) and 14.4% for small businesses (Ticarethane / KOBİ). In four regions (Ege Kuzey, Batı Akdeniz, Doğu Akdeniz, Doğu Anadolu Kuzey; 12 region-segment cases) discounts exceed the policy limit, worth TL 23.4m a year. Industrial customers in the weakest regions earn a pocket margin of only 7.1% to 10.6%.
2. **Revenue grew, gross profit did not.** Net revenue rose TL 186.9m (volume +130.4m, price +57.9m, mix -1.4m), but gross profit fell TL 36.3m because unit energy cost rose TL 122.4m. Price increases recovered about 47% of the cost increase.
3. **Demand differs sharply by segment, and the model finds it.** Estimated elasticities are Mesken -1.60 (elastic), Ticarethane / KOBİ -1.10 (borderline; its 95% CI of -1.23 to -0.98 includes -1) and Sanayi -0.61 (inelastic). The 8% volume uplift of the January-April 2025 discount campaign is estimated at 8.7% (95% CI 7.9% to 9.6%) after adjusting for price, while a naive before/after comparison reports 12.0%.

**Recommendation:** take a capped pocket-price step in every segment (Sanayi +5.0%, Ticarethane / KOBİ +4.8%, Mesken +3.3%, limited by the 5% step cap and a 5% volume-loss guard) and close the discount leakage in the four regions above. The model expects gross profit to rise by TL 145.2m a year (+14.9% on a TL 973.1m baseline; TL 139.6m to 150.9m across the elasticity confidence interval) for a 2.9% to 5.0% volume loss. This is a decision aid built on constant-elasticity assumptions; see [Limitations](#limitations).

![Recommended price step and expected gross-profit change](outputs/examples/price_recommendation.png)

## How we know the model works

The generator's true parameters are known, so the estimators are tested for recovery. Elasticities come from a log-log regression per customer segment (month-of-year dummies, region x product fixed effects, trend, log competitor price, region-clustered standard errors):

| Segment | True elasticity | Estimate | Std. error | 95% CI | Truth inside CI |
|---|---:|---:|---:|---|:---:|
| Mesken (residential) | -1.60 | -1.598 | 0.075 | [-1.758, -1.439] | yes |
| Ticarethane / KOBİ (SME) | -1.10 | -1.103 | 0.059 | [-1.228, -0.977] | yes |
| Sanayi (industrial) | -0.60 | -0.605 | 0.035 | [-0.680, -0.531] | yes |

Promotion uplift by difference-in-differences (5 treated and 13 control regions, months 25 to 28, that is January to April 2025):

| Estimator | True uplift | Estimate | 95% CI | Truth inside CI |
|---|---:|---:|---|:---:|
| Naive 2 x 2 DiD | 8.0% | 12.0% | [10.2%, 13.8%] | no (biased: counts the campaign price cut and list-price drift) |
| Price-adjusted two-way fixed-effects DiD | 8.0% | 8.7% | [7.9%, 9.6%] | yes |

| Elasticity recovery | Promotion DiD |
|---|---|
| ![Elasticity recovery](outputs/examples/elasticity_recovery.png) | ![Promotion DiD](outputs/examples/promo_did.png) |

**Which random stream is used, and why.** The default run uses seed 20260815. It is the seed of the original market generator (version 1.0.0), set before any pricing analysis existed, and it has not been changed to flatter the estimators. The Turkish rescaling in version 2.1.0 (TL prices, new names) leaves every estimate above unchanged to three decimals, because elasticities and promotion uplift do not depend on the currency scale.

One draw can still miss: a 95% interval misses the truth about 1 time in 20. `tests/test_elasticity.py` therefore also re-draws the pricing noise for six other seeds and requires at least 85% coverage and a mean bias below 0.08. In the current data, 16 of those 18 intervals contain the truth (89%) and the mean bias is at most 0.03.

## The fictional Turkish setting

Everything is invented. Names follow Turkish geography and language but refer to no real company.

| Item | Setting |
|---|---|
| Focus company | **Tavra Enerji** |
| Six competitors | Veyra Enerji, Ormena Enerji, Kuvara Enerji, Yelkara Enerji, Ozvela Enerji, Alvora Enerji |
| 18 sales regions | İstanbul Avrupa, İstanbul Anadolu, Trakya, Marmara Güney, Ege Kuzey, Ege Güney, Batı Akdeniz, Doğu Akdeniz, İç Anadolu Batı, Ankara, İç Anadolu Doğu, Batı Karadeniz, Orta Karadeniz, Doğu Karadeniz, Doğu Anadolu Kuzey, Doğu Anadolu Güney, Güneydoğu Batı, Güneydoğu Doğu (Istanbul, Ankara and the Aegean are the largest) |
| Customer segments | **Mesken** (households, "Residential"), **Ticarethane / KOBİ** (shops, offices and small and medium businesses, "SME"), **Sanayi** (industry, "Industrial") |
| Products | Sabit Fiyatlı (fixed price), Değişken Fiyatlı (PTF+) (spot-price-linked), Yeşil Enerji (YEK-G) (renewable certificate), Kurumsal Paket (corporate bundle) |
| Currency | TL per MWh and TL totals, constant 2025 prices (no inflation modelled) |
| Price level | List prices about 3,280 to 4,200 TL/MWh, unit energy cost about 2,160 to 2,810 TL/MWh. Gross margin is 20.7% overall, 15% to 24% by segment and 7% to 28% for individual region-segment cases |
| Calendar | 36 months, January 2023 to December 2025. Seasonality peaks in summer (cooling) and winter (heating) |

The company names were screened with web searches for each name followed by "Enerji"; none matched an existing Turkish energy or electricity company. This is a screening, not a trademark search, and `tests/test_repo_hygiene.py` blocks a list of real Turkish and international energy, distribution and fuel brands from ever entering the repository.

Display convention: entity names (companies, regions, products, segments) are Turkish in the data. Codes produced by SQL or the estimators (for example `Gaining`, `elastic`) stay English in the data and are translated for display in `localization.py`. The segment dimension carries the English gloss in `customer_segment_en`.

## The app

The Streamlit app is fully in Turkish and has two sidebar sections: **Fiyatlama / Pricing** (price waterfall, revenue bridge, elasticity, promotion impact, price recommendation, scenario analysis) and **Pazar / Market** (executive summary, market performance, competition, profitability, regional opportunity). Every page opens with "Bu sayfa ne gösteriyor?" (what this shows) and a data-driven "Ne anlama geliyor?" (what it means) box, and the home page has a glossary.

## Business questions answered

- Where does list price leak to pocket price, and which regions discount beyond policy? (`vw_price_waterfall`, `vw_discount_policy_flags`)
- Why did revenue and gross profit move: price, volume, mix or cost? (`vw_pvm_bridge`)
- How price-sensitive is each customer segment? (`elasticity.py`)
- Did the discount campaign create incremental volume? (`promotion.py`)
- What price step is worth taking, within margin and volume guard rails? (`price_recommendation.py`)
- Market context: growth, the company's share, competitor momentum, regional opportunity and profitability.

## Run it

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

If `data/energy_market.duckdb` does not exist, the app builds it on first start (see [DEPLOY.md](DEPLOY.md)).

## Technical detail

### Data model

Two synthetic fact tables share the date, region and product dimensions.

| Table | Grain | Purpose |
|---|---|---|
| `fact_sales` | month x region x company x product | Market view: volume, price, revenue and cost for the focus company and six competitors |
| **`fact_pricing`** | **month x region x product x customer segment** | Pricing ledger of the focus company: list, discount, rebate, payment-term and freight cost, pocket price, unit cost, competitor price, promo flag |
| `dim_customer_segment` | segment | Mesken, Ticarethane / KOBİ, Sanayi (with English gloss) |
| `dim_discount_policy` | segment | Policy maximum on-invoice discount depth |
| `dim_date`, `dim_region`, `dim_company`, `dim_product` | | Shared dimensions |

`fact_pricing` has 7,776 rows (36 months x 18 regions x 4 products x 3 segments). Its volume scale is calibrated to the market fact, but it is a separate ledger and not a reconciled split of `fact_sales` (the two differ by about 8% in 2025 revenue).

Ground truth built into the pricing generator (all in `config/default.yaml`, `pricing:` section):

- **Waterfall:** list price, minus on-invoice discount, equals invoice price; minus off-invoice rebate, payment-term cost and service/logistics cost, equals pocket price. Discount depth increases from Mesken to Sanayi, and four leakage regions sit above policy.
- **Identifying price variation:** staggered real list-price increases by region (months 7, 14, 21 and 28: July 2023, February 2024, September 2024, April 2025) plus small random monthly discount noise. One region never changes its list price.
- **Demand:** `log(volume) = region-product-segment intercept + seasonality + trend + elasticity x log(pocket price) + 0.35 x log(competitor price) + log(1.08) x promo + noise`, with true elasticities -1.6, -1.1 and -0.6.
- **Promotion:** 5 treated regions get an extra 3% on-invoice discount and a non-price volume uplift of +8% for four months (January to April 2025); 13 regions are controls.

### SQL layer

Numbered files in [`sql/`](sql/) run in order against registered dataframes:

| File | Content |
|---|---|
| `01_schema.sql` | Star-schema tables and indexes (market and pricing facts) |
| `02_market_metrics.sql` | Company monthly share, market volume, rolling 3/6-month averages, YoY, MoM |
| `03_growth_analysis.sql` | National growth and share trend |
| `04_competitor_intelligence.sql` | Competitor momentum, regional ranks, HHI concentration |
| `05_profitability.sql` | Profitability summaries and the revenue bridge |
| `06_regional_opportunity.sql` | Regional opportunity inputs |
| `07_executive_kpis.sql` | Executive KPI view |
| `08_price_waterfall.sql` | Pricing detail, list-to-pocket waterfall, leakage, policy flags and ranking |
| `09_pvm_bridge.sql` | Price-volume-mix bridge for net revenue and gross profit |

### Methods and assumptions

**Price waterfall.** Per-MWh values are volume-weighted (`SUM(amount) / SUM(volume)`). Leakage = (list - pocket) / list. A region-segment case breaches policy when its list-weighted on-invoice discount depth exceeds the segment maximum; revenue above policy = excess depth x list revenue.

**PVM bridge.** 2025 versus 2024 at product x segment level, on net (pocket) revenue and on gross profit. With total volumes VT0/VT1, cell shares s and cell net prices P0/P1:

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

Expected volume change is `(1 + price change)^e - 1`; gross-profit bounds use the elasticity confidence limits. With this data the unconstrained optimum for the elastic segments is far outside the observed price range, so the step cap and volume guard decide the result. Four Sanayi cases (Doğu Anadolu Kuzey, Doğu Akdeniz, Ege Kuzey, Güneydoğu Doğu) cannot reach the 15% floor in one step.

**Scenario page.** Arithmetic what-if on the 2025 baseline of a region and product family. The volume response is derived from the estimated elasticity of a chosen customer segment (with a sensitivity table over its confidence interval) or entered manually.

### Market-intelligence modules (original scope)

The repository started as a market-intelligence dashboard and keeps it: monthly company share, market growth, competitor momentum, HHI concentration, profitability, a regional Opportunity Score (min-max scaled weights from `config/default.yaml`) and a base-period revenue bridge. Market shares are fractions from 0 to 1 and HHI is the sum of squared shares (below 0.15 fragmented, 0.15 to below 0.25 moderate, 0.25 and above concentrated; generic context, not a regulatory assessment). The Opportunity Score is a transparent prioritisation heuristic, not a causal model.

### Power BI

[`powerbi/measures.md`](powerbi/measures.md) documents the data model (relationships) and DAX measures: Pocket Price, Price Realization %, Discount Leakage, Discount Above Policy, Gross Margin %, YoY, rolling 12 months and the PVM components with a reconciliation check. The pipeline exports the tidy star schema (`fact_pricing` and dimensions) to `powerbi/data/*.csv` (git-ignored). No `.pbix` file is included.

### Project structure

```text
config/default.yaml              Run settings, opportunity weights and the pricing ground truth
sql/                             Numbered DuckDB models 01-09
src/energy_market_intelligence/
    synthetic_data.py            Market star-schema generator (fictional names, TL prices)
    pricing_config.py            Typed pricing configuration / ground truth
    pricing_data.py              Pricing generator (waterfall, demand, promotion)
    validation.py                Fail-loud data contracts, including the waterfall identity
    database.py                  DuckDB build and read-only queries
    elasticity.py                Segment elasticity estimation
    promotion.py                 Difference-in-differences promotion uplift
    price_recommendation.py      Capped, margin-floored price steps
    scenario.py                  What-if arithmetic and elasticity-implied volume response
    localization.py              Turkish number formats, labels and display order
    insights.py                  Data-driven Turkish takeaways shown on the app pages
    visualization.py, pricing_visualization.py   Plotly figures (Turkish)
    powerbi_export.py            Star-schema CSV export
    pipeline.py                  End-to-end build and example outputs
app.py, views/, dashboard_support.py   Streamlit app: navigation, pages and shared helpers
powerbi/measures.md              Power BI model and DAX
tests/                           Unit, SQL, pipeline, page-smoke and repository-hygiene tests
outputs/examples/                Compact CSV and PNG results plus run_metadata.json
DEPLOY.md, requirements.txt      Streamlit Community Cloud deployment
```

## Limitations

- All data are synthetic. Results demonstrate method and recovery of known parameters; they are not calibrated to any real market, tariff or regulation (including regulated Turkish tariffs and market-clearing prices).
- Amounts are in constant 2025 TL. Real Turkish prices move with inflation and exchange rates; none of that is modelled.
- Elasticity is constant by construction, in line with the model that is estimated. Real demand is rarely constant-elasticity over large moves, so recommendations are limited to small steps.
- Competitors do not react to the company's price changes, and unit costs are held fixed in the recommendation.
- Estimated elasticities are per customer segment and are applied unchanged to every region and product.
- The pricing ledger is a separate sub-ledger; it is not reconciled to `fact_sales`.
- The promotion regions were assigned by the generator, not randomly; parallel trends is an assumption that must be checked on real data.
- Recommendations are a decision aid, not an automated pricing rule, and ignore contract terms, competitor positioning and regulation.
- The Power BI DAX measures are documented but were not executed in Power BI Desktop for this repository.
- Tables in the app show decimals with a dot (browser table formatting); text and charts use the Turkish comma.

## Confidentiality

This is an independent portfolio project built entirely with synthetic data. It contains no employer data, customer data, proprietary pricing logic or internal business rules; company and region names are fictional. The repository is guarded by `tests/test_repo_hygiene.py`, which scans all tracked text files for real energy-company names, e-mail addresses, local paths, cloud-sync paths and secret-like strings. Generated raw data and the DuckDB file are git-ignored.

## Author

**Mert Can Akdoğan**

## License

[MIT](LICENSE)
