---
name: Tavra Energy pricing case study
description: A pricing analysis that reads like an itemised electricity bill.
colors:
  grid-navy: "#1F3A5F"
  leak-red: "#C8462B"
  certificate-green: "#2E7D5B"
  transformer-grey: "#6B7480"
  ink: "#1B2430"
  paper: "#FFFFFF"
  panel: "#F2F4F5"
  rule: "#E3E7EA"
  leader-dots: "#AAB2BB"
  interval-blue: "#C5D0DF"
  interval-band: "#7B92B1"
  grey-on-panel: "#5C6570"
  red-on-panel: "#B83F25"
  green-text: "#27704F"
typography:
  display:
    fontFamily: "'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif"
    fontWeight: 700
    lineHeight: 1.12
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 600
  body:
    fontFamily: "'Source Sans 3', sans-serif"
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "'Source Sans 3', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
  data:
    fontFamily: "'IBM Plex Mono', Consolas, Menlo, monospace"
    fontSize: "1.4rem"
    fontWeight: 500
    fontFeature: "tnum"
  bill-title:
    fontFamily: "'Barlow Semi Condensed', 'Arial Narrow', Arial, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    letterSpacing: "0.16em"
rounded:
  none: "0px"
  control: "4px"
spacing:
  callout-y: "0.75rem"
  callout-x: "1.1rem"
  card: "0.9rem 1.1rem 1rem"
  bill: "1rem 1.3rem 1.1rem"
  section: "1.4rem"
components:
  bill:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "{spacing.bill}"
    width: "36rem"
  callout-takeaway:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0.75rem 1.1rem 0.85rem"
  callout-note:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
  callout-breach:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
  question-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.grid-navy}"
    rounded: "{rounded.none}"
    padding: "{spacing.card}"
  metric:
    textColor: "{colors.ink}"
    typography: "{typography.data}"
  segmented-control:
    rounded: "{rounded.control}"
    textColor: "{colors.ink}"
---

# Design System: Tavra Energy pricing case study

## Overview

**Creative North Star: "The Itemised Bill"**

Every screen should read like the breakdown on an electricity bill: line by line, plain, and easy to check. The finding of the case study is that part of the list price never reaches the company, so the app shows price as a bill that starts at the list price, subtracts each leak on its own line and ends at the price the company keeps. That bill, the price breakdown, is the one signature element. Everything around it is quiet, so the reader's eye goes to the numbers.

The system is flat and light. Depth comes from rules, not shadows: a heavy navy rule on top of each container says "this is a unit", thin grey rules separate rows. Colour is semantic, never decorative: navy is price, red is money lost, green is money gained. Numbers sit in a monospaced face with tabular figures so columns of amounts line up like a statement. Page titles are questions a hiring manager would ask; the answer comes first, the chart that proves it second.

**Key Characteristics:**
- One signature element (the price breakdown); all other surfaces are quiet.
- Top rules instead of shadows, side stripes or rounded cards.
- Three semantic colours with fixed meanings on a white page.
- Condensed headings, a humanist body face and monospaced numbers.
- English throughout; numbers as `3,732.61`, `14.8%`, `TRY 23.4m`.

## Colors

A cool, utility-bill palette: one dark navy, two signal colours used sparingly, and greys for structure.

### Primary
- **Grid Navy** (`grid-navy`): prices, headings, page links, the primary chart series and the top rule of every container. It is the colour of "the price".

### Secondary
- **Leak Red** (`leak-red`): only deductions in the price breakdown and waterfalls, the leakage rate and real policy breaches. Never for emphasis or decoration.

### Tertiary
- **Certificate Green** (`certificate-green`): only gains from the recommendation and confirmed positive results (for example "true value inside the interval").

### Neutral
- **Transformer Grey** (`transformer-grey`): secondary text, captions, metric labels, neutral chart series and caveat rules.
- **Ink** (`ink`): body text and numbers.
- **Paper** (`paper`): page and container background.
- **Panel** (`panel`): sidebar and callout background.
- **Rule** (`rule`): gridlines, row separators and container borders.
- **Leader Dots** (`leader-dots`): the dotted leaders between a bill line's label and its amount.
- **Interval Blue** (`interval-blue`): text selection.
- **Interval Band** (`interval-band`): the 95% confidence band on the trust strip; at least 3:1 against white.
- **Grey on Panel** (`grey-on-panel`) and **Red on Panel** (`red-on-panel`): darker twins of transformer grey and leak red for callout labels on the panel grey (4.5:1 or more); same meaning, never used on white.
- **Green Text** (`green-text`): a darker certificate green for small text on a pale green tint, such as the delta under a metric.

### Named Rules
**The One Meaning Rule.** Each colour means one thing. Red is money that leaks or a broken rule; green is money gained or a passed check. A smaller revenue effect in a bridge is not a leak, so neutral bridges use lighter navy and grey.

**The Panel Contrast Rule.** Text on the panel grey must reach 4.5:1: labels there use the on-panel twins, not the base grey or red.

**The Quiet Page Rule.** Red and green together cover a small share of any screen; most of the page is ink on white.

## Typography

**Display Font:** Barlow Semi Condensed (with Arial Narrow, Arial)
**Body Font:** Source Sans 3 (with the system sans-serif)
**Label/Mono Font:** IBM Plex Mono (with Consolas, Menlo)

**Character:** A condensed, slightly industrial heading face, like the labels on a meter cabinet, over a calm humanist text face; numbers in a plain monospace so they read like a printed statement.

### Hierarchy
- **Display** (700, Streamlit H1 size; 2.1rem below 640px, 1.12 line height, -0.01em): page titles, written as questions, and the overview thesis sentence.
- **Headline** (700, 1.3rem, 1.2): chart titles, rendered as HTML so they wrap on phones.
- **Title** (600, 1.1rem): segment names in the trust strip and the bold labels of callouts (1.05rem).
- **Body** (400, 1.05rem, 1.5): intro lines and callout text; intro lines are capped at 64rem.
- **Label** (400, 0.875–0.92rem): metric labels, captions, the bill's meta line and legends; never below 14px.
- **Data** (500, 1.4rem in metrics, 1.05rem in the bill, tabular figures): every number that the reader compares.

### Named Rules
**The Statement Numbers Rule.** Any number a reader compares sits in IBM Plex Mono with tabular figures, right-aligned when stacked.

**The Question Title Rule.** Page titles are questions; the sidebar uses short nouns.

## Layout

A single reading column inside Streamlit's wide layout, capped at 1360px, with the sidebar holding one flat list of six pages. Each page follows the same order: question title, one-line "What this page shows", a "What it means" takeaway, then the evidence (metrics, charts, tables). On the overview the price breakdown and its matching waterfall sit side by side; three question cards follow in a row, then the trust strip in three columns.

Spacing is compact: 2.4rem top padding, about 1.4rem between blocks, tight padding inside containers. Below 640px columns stack, the trust strip becomes one column and the H1 drops to 2.1rem. The price breakdown adapts to its own width with container queries: under 27rem it hides the percentage column and narrows the amount column, so it stays aligned in a tablet column as well as on a phone.

## Elevation & Depth

Flat. No shadows anywhere. Depth and grouping come from rules: a 4px navy rule on top of the bill, a 3px navy rule on top of question cards, a 2px rule in the semantic colour on top of callouts, and 1px grey rules between rows and metrics. The panel grey separates callouts and the sidebar from the white page.

### Named Rules
**The Top Rule Rule.** A container is marked by a rule on its top edge, never by a shadow or a coloured side stripe.

## Shapes

Square. Containers (bill, callouts, cards) have no corner radius. Streamlit's own controls (segmented control, select boxes, sliders) keep a small 4px radius from the theme. The only round shapes are data marks: the filled estimate dot and the outlined true-value diamond on the trust strip.

## Components

### Price breakdown (signature)
The bill. White, 1px grey border, 4px navy top rule, max 36rem wide. A letter-spaced "PRICE BREAKDOWN" title with a grey meta line (scope · TRY/MWh · 2025). Each line: an operator column (blank, − or =), the label, dotted leaders, the amount in mono and, when there is room, the share of list price. Deductions are red; the net line sits under a 2px navy rule in bold navy. The leakage rate closes the bill in red mono. Displayed amounts are rounded so the lines add up exactly.

### Callouts
- **Takeaway ("What it means"):** panel background, 2px navy top rule, bold navy label above body text.
- **Note (caveats and assumptions):** same shape with a grey rule and grey label.
- **Breach:** red rule and red label, only for real policy breaches.
- **Gain:** green rule and label, only for confirmed positive results.

### Question cards
White, 1px grey border, 3px navy top rule, square corners. The question is the page link (condensed 1.35rem navy, wraps, arrow after it, underline on hover); one data-driven answer sentence below.

### Metrics
A 1px grey top rule, grey label, value in 1.4rem mono with tabular figures; deltas in small mono and hidden when they round to zero.

### Trust strip
One column per customer segment: segment name, a scale with the 95% interval band, a filled navy dot for the estimate and an outlined ink diamond for the true value, three label/value rows and a green "True value is inside the interval" line.

### Navigation
Streamlit's sidebar navigation on the panel grey: one flat list of six short nouns, the current page highlighted by Streamlit.

### Charts
One Plotly template (`tavra`) shared by the app and the PNG exports: transparent background, grey gridlines, mono tick labels on numeric axes, navy for price series, red only for deductions and breaches, green only for gains. Axes that do not start at zero say so in their caption.

## Do's and Don'ts

### Do:
- **Do** answer the page's question in the title and the takeaway before showing a chart.
- **Do** put every compared number in IBM Plex Mono with tabular figures.
- **Do** mark containers with a top rule (4px bill, 3px cards, 2px callouts).
- **Do** format numbers through the helpers in `localization.py` (`3,732.61`, `14.8%`, `TRY 23.4m`), never the browser locale.
- **Do** keep secondary text at least 14px with at least 4.5:1 contrast on white.

### Don't:
- **Don't** use red or green for anything other than leaks/breaches and gains/passed checks.
- **Don't** add shadows, gradients, rounded containers or coloured side stripes.
- **Don't** add emojis, decorative icons or a dark-mode variant.
- **Don't** add a second signature element; the price breakdown stays the only one.
