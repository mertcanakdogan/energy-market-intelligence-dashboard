# Changelog

All notable changes to this project are documented here.

## [2.2.0] - 2026-10-11

Redesign of the Streamlit app around the fatura dökümü; analysis results are unchanged.

### Changed

- Design: the "fiyat kaçağı" concept with one signature element, the fatura dökümü (bill-style price itemisation) on the landing page. The home page now leads with a computed thesis sentence, the bill next to a matching waterfall, three question cards and a model-trust strip instead of the metric-card row. See `docs/DESIGN.md`.
- Page titles are questions; sidebar sections are "Fiyatlama" and "Pazar" with short noun labels; page URLs changed accordingly. Waterfall items are named like bill lines (Fatura içi iskonto, Fatura dışı prim, Hizmet ve nakliye).
- One Plotly template (`tavra`) for all charts and PNG exports; colours have fixed meanings (red only for leakage and breaches, green only for gains). Theme and fonts (Source Sans 3, Barlow Semi Condensed, IBM Plex Mono) are set in `.streamlit/config.toml`; Streamlit 1.65 or newer is required.
- Public URL is `https://tavra-enerji-fiyatlama.streamlit.app`.
- Every number reads the Turkish way regardless of the browser locale: tables are formatted through a Styler (sorting still uses raw values), share axes show `%10` instead of `10%`, month axes `01/2025`, numeric axes have thousands separators, and percentage sliders show `+%2,5`.
- Callouts use a top rule like the bill and the landing cards instead of a side stripe. The scenario page hides zero deltas and says plainly when nothing changes.

## [2.1.0] - 2026-10-11

Turkish setting, TL currency and a clearer app and README. The ground truth is unchanged: all elasticity and promotion estimates are identical to 2.0.0 to three decimals.

### Changed

- Fictional Turkish setting: focus company Tavra Enerji and six fictional competitors ("<invented word> Enerji", web-screened against real companies), 18 sales regions based on Turkey's geography (for example İstanbul Avrupa, Ege Kuzey, Doğu Karadeniz), customer segments Mesken, Ticarethane / KOBİ and Sanayi (English gloss in `dim_customer_segment.customer_segment_en`) and Turkish product names.
- All money is Turkish lira at constant 2025 prices; prices are TL per MWh at realistic 2025 levels (list about 3,300 to 4,200 TL/MWh). Seasonality now peaks in summer and winter. The latest 12 months are calendar year 2025.
- Streamlit app is fully Turkish, with `st.navigation` in two sections ("Fiyatlama / Pricing", "Pazar / Market"), readable page titles, "Bu sayfa ne gösteriyor?" and data-driven "Ne anlama geliyor?" boxes, compact KPI cards with help tooltips, a glossary, Turkish charts (TL axes, Turkish number separators) and a scenario baseline restricted to 2025. The `pages/` directory became `views/`; page URLs changed.
- README rewritten for a non-technical reader first: key terms, Turkish summary, three findings and one recommendation, a description of the fictional setting and the random stream used.
- SQL and output column names `northstar_*` became `focus_*`, and `vw_northstar_profitability_monthly` became `vw_focus_profitability_monthly`; SQL filters the focus company by `company_type`, not by name.
- `run_metadata.json` is written as UTF-8 without escaping Turkish characters. Power BI measures, DEPLOY.md and the sample-data note describe the new names and units; DEPLOY.md links the live app.

### Added

- `localization.py` (Turkish number, percent, TL and volume formats; column and value labels) and `insights.py` (takeaway sentences computed from the data).
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
