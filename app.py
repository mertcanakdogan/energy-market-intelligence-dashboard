"""Entry point and navigation of the Tavra Enerji pricing and revenue analytics case study."""

import streamlit as st

from dashboard_style import inject_global_css
from dashboard_support import PAGE_SPECS

st.set_page_config(
    page_title="Tavra Enerji | Fiyatlama ve gelir analitiği",
    page_icon=":material/receipt_long:",
    layout="wide",
    initial_sidebar_state="auto",
)
inject_global_css()


def build_navigation() -> dict[str, list[st.Page]]:
    """Group the pages into the sidebar sections (home first, then Fiyatlama and Pazar)."""

    sections: dict[str, list[st.Page]] = {}
    for spec in PAGE_SPECS:
        is_home = spec.path.endswith("home.py")
        page = st.Page(
            spec.path,
            title=spec.title,
            url_path=None if is_home else spec.url_path,
            default=is_home,
        )
        sections.setdefault(spec.section, []).append(page)
    return sections


st.navigation(build_navigation()).run()
