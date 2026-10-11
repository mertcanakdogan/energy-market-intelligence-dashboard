"""Entry point and navigation of the Tavra Enerji pricing and revenue analytics case study."""

import streamlit as st

from dashboard_support import PAGE_SPECS

st.set_page_config(
    page_title="Tavra Enerji | Fiyatlama ve Gelir Analitiği",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px;}
    [data-testid="stMetric"] {border-top: 2px solid #1f4e79; padding-top: 0.7rem;}
    [data-testid="stMetricValue"] {font-size: 1.5rem;}
    [data-testid="stMetricValue"] > div,
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricDelta"] > div {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        overflow-wrap: anywhere;
    }
    h1, h2, h3 {color: #20364d;}
    div[data-testid="stCaptionContainer"] {color: #52606d;}
    </style>
    """,
    unsafe_allow_html=True,
)


def build_navigation() -> dict[str, list[st.Page]]:
    """Group the pages into the sections of the sidebar (home first, then two sections)."""

    sections: dict[str, list[st.Page]] = {}
    for section, path, title, icon, url_path in PAGE_SPECS:
        is_home = path.endswith("home.py")
        page = st.Page(
            path, title=title, icon=icon, url_path=None if is_home else url_path, default=is_home
        )
        sections.setdefault(section, []).append(page)
    return sections


st.navigation(build_navigation()).run()
