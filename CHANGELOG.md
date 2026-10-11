# Changelog

All notable changes to this project are documented here.

## [2.3.1] - 2026-10-11

A design audit of all six pages, at laptop and phone width, and of every exported chart. The data and all numeric results are unchanged.

### Fixed

- Phone layout: charts with two or three panels (price waterfall, revenue bridge, promotion) no longer squeeze their titles and labels into each other. The app shows them as separate charts that stack on a phone; the PNG exports keep the side-by-side layout.
- Price leakage: the chart is now the itemised price breakdown as a horizontal waterfall, with a picker for the whole portfolio or one segment. The policy table puts the amount above policy straight after the names, so it stays visible on a phone.
- Price recommendation: segment names and price steps sit above the bars, so the bars keep the full width and the amounts are never rotated or clipped. The limits moved from the sidebar into a "Change the limits" panel on the page, which phones can reach; the province-level table moved into its own panel.
- Promotion impact: the month axis shows real months, the promotion band is labelled, and the estimate chart starts at zero with the true value drawn as the same hollow diamond as on the elasticity chart.
- Price sensitivity: "unit elasticity (-1)" is replaced by plain labels for the two sides of -1; long axis titles that were cut on phones moved into captions.
- Exports: labels outside bars are no longer clipped, charts without a legend lose the empty band under the title, line charts whose axis does not start at zero say so, the focus company is highlighted in the competitor chart and the palest opportunity bubbles stand out from the page.

### Changed

- One term for the price the company keeps: "pocket price" (the bill line, the segment comparison, the glossary and the charts). The price leakage page shows the leakage rate, like the overview.
- Numbers use a true minus sign (−1.60), money keeps "TRY" and the amount on one line, millions have one decimal (TRY 1.4m) and table percentages one decimal (9.3%).
- Tables show the columns that answer the page's question; standard errors, volumes and prices behind the effects are one click away.
- The province filter is a single choice (all provinces or one) instead of 18 removable chips.
- README: the elasticity and promotion charts are shown full width instead of side by side.
- Typography uses two Office-safe system families and nothing else: bold Arial for page and card titles, Georgia for the introduction line, section headings and chart titles, plain Arial for text and every number (its figures are tabular, so amounts still line up). The app no longer downloads web fonts, and the PNG charts match the app on any Windows or Mac without installing fonts.

## [2.3.0] - 2026-10-11

The whole project and the app are now in English, and the app shows only the pricing story. All numeric results are unchanged: elasticities, promotion uplift, waterfall amounts and recommendation totals are the same as in 2.2.0.

### Fixed

- Exported charts: the title no longer collides with the legend (title pinned to the top, legend below it, wider top margin), recommendation labels clear the bars, the promotion chart's true-value label no longer sits on the estimate, method names use the body face, and the true-value diamond is hollow so the estimate dot stays visible when they coincide.

### Python

- Python 3.14 is the main version; CI tests 3.12 and 3.14 and runs 3.15 as an informational job (DuckDB has no 3.15 wheels yet). The devcontainer uses Python 3.14. Dependency ranges allow pandas 3 and Plotly 7; text columns stored as pandas 3's `str` dtype are now translated in tables too.

### Changed

- Language: the app, README, design notes, Power BI notes and generated data are in English. The README no longer has a Turkish summary.
- Sales areas are now 18 Turkish provinces instead of 18 regions, one province for each former region (for example Istanbul, Ankara, Izmir, Tekirdağ). Their numbers are unchanged. In the tables and SQL the province keeps the internal name "region" (`region_id`, `region_name`).
- Currency is shown as TRY at constant 2025 prices: amounts as TRY 23.4m or TRY 4.69bn, unit prices as TRY/MWh. The older lira abbreviation and the lira sign are no longer used.
- Names: the focus company is renamed from "Tavra Enerji" to "Tavra Energy", and the six competitors are now "<invented word> Energy". Customer segments are Residential, Commercial (SME) and Industrial. Products are Fixed price, Index-linked (PTF+), Green energy (YEK-G) and Corporate bundle. `dim_customer_segment` no longer has a `customer_segment_en` column, because the segment names are already English.
- Codes in the generated data are English: `market_size_band` Small/Medium/Large, `strategic_segment` Develop/Defend/Core, `product_segment` Fixed/Index-linked/Green/Corporate.
- Number formats are English: thousands separated by commas and a decimal point (3,732.61), percentages as 14.8%, money as TRY 23.4m and TRY 4.69bn. The Plotly template uses `separators=".,"`.
- The app has six pricing pages in one flat navigation list: Overview, Price leakage, Revenue bridge, Price sensitivity, Promotion impact and Price recommendation.
- New live URL: <https://tavra-energy-pricing.streamlit.app>. The old subdomain is no longer used.
- `DATASET_VERSION` and the package version are 2.3.0, so a deployed app rebuilds its database (the names changed; the numbers did not).

### Removed

- The market, competition, profitability, regional-opportunity and scenario pages are removed from the app. Their analytics, SQL views (`sql/02` to `sql/07`) and pipeline outputs stay in the repository.

## [2.2.0] - 2026-10-11

Redesign of the Streamlit app around the price breakdown, read like the line items of a bill; analysis results are unchanged.

### Fixed

- A deployed app rebuilds its database when it was built from an earlier dataset version (`DATASET_VERSION` stamp next to the DuckDB file); before, a Streamlit Cloud app kept serving the 2.0.0 data after an update. Streamlit Cloud installs the package in editable mode, so new modules are importable after a push.

### Changed

- Design: the "price leakage" concept with one signature element, the bill-style price breakdown on the landing page. The home page now leads with a computed thesis sentence, the bill next to a matching waterfall, three question cards and a model-trust strip instead of the metric-card row. See `docs/DESIGN.md`.
- Page titles are questions; the sidebar had two sections, pricing and market, with short noun labels; page URLs changed accordingly. Waterfall items are named like bill lines (on-invoice discount, off-invoice premium, service and freight).
- One Plotly template (`tavra`) for all charts and PNG exports; colours have fixed meanings (red only for leakage and breaches, green only for gains). Theme and fonts (Source Sans 3, Barlow Semi Condensed, IBM Plex Mono) are set in `.streamlit/config.toml`; Streamlit 1.65 or newer is required.
- The public URL was set on Streamlit Community Cloud (replaced in 2.3.0).
- Every number used Turkish formatting regardless of the browser locale (replaced by English formats in 2.3.0): tables are formatted through a Styler (sorting still uses raw values), share axes put the percent sign first, month axes show `01/2025`, numeric axes have thousands separators, and percentage sliders use a decimal comma.
- The bill block adapts to its own column width (container queries), so it stays aligned on tablets as well as phones; landing-card titles wrap instead of being cut off.
- Callouts use a top rule like the bill and the landing cards instead of a side stripe. The scenario page hides zero deltas and says plainly when nothing changes.

## [2.1.0] - 2026-10-11

Turkish setting, Turkish lira currency and a clearer app and README. The ground truth is unchanged: all elasticity and promotion estimates are identical to 2.0.0 to three decimals.

### Changed

- Fictional Turkish setting: focus company Tavra and six fictional competitors, each an invented word followed by the Turkish word for energy (web-screened against real companies); 18 sales regions based on Turkey's geography (for example European Istanbul, North Aegean, East Black Sea); customer segments with Turkish names for households, small businesses and industry (English gloss in `dim_customer_segment.customer_segment_en`); and Turkish product names. Names and regions were replaced in 2.3.0.
- All money is Turkish lira at constant 2025 prices; prices are lira per MWh at realistic 2025 levels (list about 3,300 to 4,200 per MWh). Seasonality now peaks in summer and winter. The latest 12 months are calendar year 2025.
- Streamlit app is fully Turkish, with `st.navigation` in two sections (pricing and market), readable page titles, a "what this page shows" line and a data-driven "what it means" box on every page, compact KPI cards with help tooltips, a glossary, Turkish charts (lira axes, Turkish number separators) and a scenario baseline restricted to 2025. The `pages/` directory became `views/`; page URLs changed.
- README rewritten for a non-technical reader first: key terms, a Turkish summary (removed in 2.3.0), three findings and one recommendation, a description of the fictional setting and the random stream used.
- SQL and output column names `northstar_*` became `focus_*`, and `vw_northstar_profitability_monthly` became `vw_focus_profitability_monthly`; SQL filters the focus company by `company_type`, not by name.
- `run_metadata.json` is written as UTF-8 without escaping Turkish characters. Power BI measures, DEPLOY.md and the sample-data note describe the new names and units; DEPLOY.md links the live app.

### Added

- `localization.py` (Turkish number, percent, lira and volume formats; column and value labels) and `insights.py` (takeaway sentences computed from the data).
- `generate_management_observations(..., language="tr")`.
- Tests for the Turkish setting (names, prices, calendar), localization, insights, navigation and page explanations; the hygiene test also blocks real Turkish retailers, distribution companies and fuel brands.

## [2.0.0] - 2026-10-11

Repositioned as a pricing and revenue analytics case study for the fictional focus company Northstar Energy. All data remain synthetic.

### Added

- Pricing ledger `fact_pricing` (month x region x product x customer segment) with `dim_customer_segment` and `dim_discount_policy`, generated with a documented ground truth in `config/default.yaml` (`pricing:` section): list-to-pocket price waterfall, staggered list-price increases, constant-elasticity demand, a discount campaign with a known uplift, and unit variable cost.
- SQL models `08_price_waterfall.sql` (waterfall, leakage, discount-policy flags) and `09_pvm_bridge.sql` (price-volume-mix bridge for net revenue and gross profit that reconciles exactly).
- `elasticity.py` (log-log OLS per segment with fixed effects and clustered standard errors, compared with the true elasticity), `promotion.py` (naive and price-adjusted difference-in-differences) and `price_recommendation.py` (profit-maximising or capped price step with margin floor and volume-loss guard).
- Streamlit pages for Price Waterfall, PVM Bridge, Elasticity, Promotion Impact and Price Recommendation; a pricing-first landing page; an elasticity-driven volume response (with manual override) on the scenario page.
- The app builds the synthetic database on first start when none exists, and honours `EMID_DATABASE_PATH`.
- Pipeline outputs: `price_waterfall`, `discount_policy_flags`, `pvm_bridge`, `elasticity_recovery`, `promo_did`, `price_recommendation` (CSV and PNG), pricing headline metrics in `run_metadata.json`, and a Power BI star-schema CSV export to `powerbi/data/`.
- `powerbi/measures.md` (data model and DAX), `DEPLOY.md` and `requirements.txt` for Streamlit Community Cloud.
- Tests for every new module, Streamlit page smoke tests, and a repository hygiene test that scans tracked files for real company names, e-mail addresses, local paths and secret-like strings.
- `statsmodels` dependency.

### Security

- Require pytest 9.0.3 or newer in the development toolchain to address insecure temporary-directory handling in earlier releases.

### Changed

- README rewritten around the pricing case study with an executive summary and a recovery-versus-truth section.
- `scenario.py` gains `volume_response_from_elasticity`; `calculate_scenario` is unchanged.
- `build_dataset` split out of the pipeline so the app can reuse it.

## [1.0.0] - 2026-08-15

### Added

- Deterministic synthetic energy-market star schema covering 36 months and 18 regions.
- DuckDB SQL models for growth, share, competition, concentration, profitability, decomposition, opportunity inputs, and executive KPIs.
- Six-page Streamlit decision-support application and compact example outputs.
- Validation, automated tests, coverage enforcement, Ruff configuration, package build, and GitHub Actions CI.
- Clean-room documentation, scenario disclaimer, and reproducibility metadata.
