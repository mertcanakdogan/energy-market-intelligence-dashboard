# Changelog

All notable changes to this project are documented here.

## [Unreleased]

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
