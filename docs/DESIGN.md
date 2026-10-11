# Design notes

## Concept: fiyat kaçağı

*Kaçak* (leakage) is everyday electricity vocabulary, and it names the case study's finding: a share of the list price never reaches the retailer. The price waterfall therefore reads like an electricity bill's line items (*fatura dökümü*): list price, minus on-invoice discount, minus off-invoice premium, minus payment-term cost, minus service and freight, equals the net (pocket) price, with the leakage rate underneath. That block is the one signature element of the app; everything else is deliberately quiet.

The page should answer, within 30 seconds, what a hiring manager for a pricing role wants to know: the analyst finds where price leaks, quantifies what a price change is worth, and proves the model works (the data are synthetic, so the true elasticities are known and the estimates are compared to them).

## Tokens

Each colour has one meaning and is never used decoratively.

| Token | Hex | Meaning |
|---|---|---|
| Şebeke laciverti (grid navy) | `#1F3A5F` | Prices, headings, primary series, takeaway callouts |
| Kaçak kırmızısı (leak red) | `#C8462B` | Only deductions, leakage and policy breaches |
| Sertifika yeşili (certificate green) | `#2E7D5B` | Only gains from the recommendation and positive outcomes |
| Trafo grisi (transformer grey) | `#6B7480` | Secondary text and neutral series; `#E3E7EA` for gridlines and borders |
| Text / background / panel | `#1B2430` / `#FFFFFF` / `#F2F4F5` | Body text, page, sidebar and callouts |

Neutral bridges (price-volume-mix, profit bridge) and share changes use lighter navy and grey rather than red and green, because a smaller revenue effect is not leakage.

Type: headings in Barlow Semi Condensed (600/700), body in Source Sans 3, numbers and data in IBM Plex Mono with tabular figures. All three cover Turkish glyphs. Labels are in sentence case.

## Where the tokens live

- `.streamlit/config.toml`: Streamlit theme (colours, `font`, `headingFont`, `codeFont` via Google Fonts URLs).
- `src/energy_market_intelligence/visualization.py`: the single Plotly template `tavra` (fonts, colours, gridlines, transparent backgrounds, `separators=",."` for Turkish decimals). It is the Plotly default, so Streamlit charts and the PNG exports in `outputs/examples/` share it. The PNG export renders offline and falls back to system fonts when the web fonts are not installed.
- `dashboard_style.py`: the one injected stylesheet, the callouts and the bill and trust-strip HTML.

## Rules

- Page titles are questions; the sidebar uses short nouns. Sections: Fiyatlama first, then Pazar.
- Every page: H1 question, a short "Bu sayfa ne gösteriyor?" line and a "Ne anlama geliyor?" takeaway (navy rule). Caveats use a grey rule; red is reserved for real breaches, green for confirmed positive results.
- No emojis, gradients, decorative icons or dark-mode variants. Keyboard focus outlines are left as Streamlit draws them. Secondary text is at least 14 px and at least 4.5:1 contrast on white.
- Mobile (about 400 px): columns stack, the bill block drops its percentage column and wraps cleanly, chart titles are HTML headings so they wrap.
