# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Hiring managers and recruiters for pricing, revenue management and revenue growth management (RGM) analyst roles. They open the live app from a link on a CV or LinkedIn profile, usually without context and with little time, and should understand within about two minutes what the author can do: find where price leaks between list price and the price the company keeps, size what a price change is worth, and show that the model's estimates can be trusted.

## Product Purpose

A portfolio case study of analytical pricing for a fictional energy retailer, Tavra Energy, built on fully synthetic data. It demonstrates the analysis a pricing analyst does (price waterfall, price-volume-mix bridge, price elasticity, promotion impact, price recommendation) and states each result in plain language. Success: a non-technical reader can retell the main finding and the recommendation after one visit.

## Positioning

Because the data are synthetic, the true price elasticities and the true promotion uplift are known. The app compares every estimate with the truth, which a case study on real data could not do.

## Operating Context

- Read on a laptop or a phone, often straight from a CV PDF or a LinkedIn Featured link.
- Hosted on Streamlit Community Cloud from the public GitHub repository `mertcanakdogan/energy-market-intelligence-dashboard`; the first visit may wait while the database is generated.
- Readers may also open the repository README, which carries the same story.

## Capabilities and Constraints

- Streamlit app with six pages, all about pricing: Overview, Price leakage, Revenue bridge, Price sensitivity, Promotion impact, Price recommendation. Market-share and competitor analyses remain in the code base and pipeline but are not part of the app.
- Everything is in English. Money is shown in TRY at constant 2025 prices; prices in TRY/MWh.
- The setting is Turkey: sales areas are 18 Turkish provinces (for example Istanbul, Ankara, Izmir); company and competitor names are invented and must not match real companies.
- Data are generated deterministically from a fixed seed; estimates must not be tuned to flatter the results.
- Keep it simple: plain words, short sentences, few controls, no jargon without a one-line explanation.

## Brand Commitments

- Company name: Tavra Energy (fictional). Live app: `https://tavra-energy-pricing.streamlit.app`.
- No employer names, employer data or internal figures anywhere; the author's real job is not referenced inside the app.

## Evidence on Hand

- The synthetic dataset, SQL models and analysis outputs in this repository (`outputs/examples/`).
- No real customers, testimonials or benchmarks exist; none may be invented.

## Product Principles

1. Answer the question first, then show the chart that proves it.
2. Plain English over analyst jargon; every technical term gets a one-line explanation.
3. Show that the method works by comparing estimates with the known truth.
4. Fewer pages and controls; nothing that does not serve the pricing story.

## Accessibility & Inclusion

WCAG 2.1 AA: readable contrast, keyboard access and a layout that works on a phone.
