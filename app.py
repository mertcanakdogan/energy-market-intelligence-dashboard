"""Landing page for the Northstar Energy market-intelligence portfolio app."""

import streamlit as st

st.set_page_config(
    page_title="Northstar Energy | Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px;}
    [data-testid="stMetric"] {border-top: 2px solid #1f4e79; padding-top: 0.7rem;}
    h1, h2, h3 {color: #20364d;}
    div[data-testid="stCaptionContainer"] {color: #52606d;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Energy Market Intelligence Dashboard")
st.subheader("Commercial performance and market signals for Northstar Energy")
st.write(
    "A production-style portfolio project that turns a deterministic synthetic market dataset "
    "into SQL-led management decision support. Use the page navigation to examine growth, "
    "competition, profitability, regional priorities, and transparent what-if assumptions."
)

left, middle, right = st.columns(3)
left.markdown(
    "### 36 months\nMonthly commercial history with structured seasonality and market change."
)
middle.markdown(
    "### 18 regions\nComparable market, share, profitability, and concentration diagnostics."
)
right.markdown("### 7 companies\nNorthstar Energy and six entirely fictional competitors.")

st.info(
    "All data and business logic in this repository are newly designed for a public demonstration. "
    "The application does not make automated commercial decisions."
)
