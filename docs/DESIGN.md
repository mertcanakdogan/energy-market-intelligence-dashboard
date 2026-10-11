# Design notes

## Concept: price leakage

The case study's finding is that a share of the list price never reaches the retailer. The app calls this *price leakage*. The price waterfall therefore reads like the line items of an electricity bill, the *price breakdown*: list price, minus on-invoice discount, minus off-invoice premium, minus payment-term cost, minus service and freight, equals the net (pocket) price, with the leakage rate underneath. The price breakdown is the one signature element of the app; everything else is deliberately quiet.

The page should answer, within 30 seconds, what a hiring manager for a pricing role wants to know: the analyst finds where price leaks, works out what a price change is worth, and proves the model works (the data are synthetic, so the true elasticities are known and the estimates are compared with them).

## Tokens

Each colour has one meaning and is never used for decoration.

| Token | Hex | Meaning |
|---|---|---|
| Grid navy | `#1F3A5F` | Prices, headings, primary series, takeaway callouts |
| Leak red | `#C8462B` | Only deductions, leakage and policy breaches |
| Certificate green | `#2E7D5B` | Only gains from the recommendation and positive outcomes |
| Transformer grey | `#6B7480` | Secondary text and neutral series; `#E3E7EA` for gridlines and borders |
| Text / background / panel | `#1B2430` / `#FFFFFF` / `#F2F4F5` | Body text, page, sidebar and callouts |

Neutral bridges (price-volume-mix, profit bridge) use lighter navy and grey rather than red and green, because a smaller revenue effect is not leakage.

Type: headings in Barlow Semi Condensed (600/700), body in Source Sans 3, numbers and data in IBM Plex Mono with tabular figures. All three cover the Turkish characters used in province names (for example Tekirdağ, Muğla, Diyarbakır). Labels are in sentence case.

Numbers: every number in text, metrics and tables uses English formats through the helpers in `localization.py`, never the browser locale. Thousands are separated by commas and the decimal mark is a point (`3,732.61`). Percentages are written as `14.8%`. Money is written as `TRY 23.4m` or `TRY 4.69bn`, and unit prices in `TRY/MWh`.

## Where the tokens live

- `.streamlit/config.toml`: Streamlit theme (colours, `font`, `headingFont`, `codeFont` via Google Fonts URLs).
- `src/energy_market_intelligence/visualization.py`: the single Plotly template `tavra` (fonts, colours, gridlines, transparent backgrounds, `separators=".,"` for a decimal point and comma thousands). It is the Plotly default, so Streamlit charts and the PNG exports in `outputs/examples/` share it. The PNG export renders offline and falls back to system fonts when the web fonts are not installed.
- `dashboard_style.py`: the one injected stylesheet, the callouts and the HTML for the price breakdown and the trust strip.

## Rules

- Page titles are questions; the sidebar uses short nouns. There is one flat navigation list of six pricing pages, with no sections.
- Every page: an H1 question, a short "What this page shows" line and a "What it means" takeaway (navy top rule, the same device as the price breakdown and the landing cards; no side stripes). Caveats use a grey rule; red is kept for real breaches, green for confirmed positive results.
- No emojis, gradients, decorative icons or dark-mode variants. Keyboard focus outlines are left as Streamlit draws them. Secondary text is at least 14 px and has at least 4.5:1 contrast on white.
- Mobile (about 400 px): columns stack, the price breakdown drops its percentage column and wraps cleanly, chart titles are HTML headings so they wrap.
