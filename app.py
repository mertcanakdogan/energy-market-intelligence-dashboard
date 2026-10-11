"""Entry point and navigation of the Tavra Energy pricing and revenue analytics case study."""

import streamlit as st

from dashboard_style import inject_global_css
from dashboard_support import PAGE_SPECS

st.set_page_config(
    page_title="Tavra Energy | Pricing and revenue analytics",
    page_icon=":material/receipt_long:",
    layout="wide",
    initial_sidebar_state="auto",
)
inject_global_css()


def build_navigation() -> list[st.Page]:
    """One flat list of the six pricing pages, the overview first."""

    pages = []
    for spec in PAGE_SPECS:
        is_home = spec.path.endswith("home.py")
        pages.append(
            st.Page(
                spec.path,
                title=spec.title,
                url_path=None if is_home else spec.url_path,
                default=is_home,
            )
        )
    return pages


st.navigation(build_navigation()).run()
