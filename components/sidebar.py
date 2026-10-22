from collections.abc import Sequence

import streamlit as st

from logout import show_logout_button


NAVIGATION_OPTIONS = (
    "Dashboard",
    "Upload Dataset",
    "Process Discovery",
    "Bottleneck Analysis",
    "Conformance Analysis",
    "Reports",
)


def show_sidebar(
    pages: Sequence[str] = NAVIGATION_OPTIONS,
) -> str:
    """Display the CareFlow sidebar and return the selected page."""

    if not pages:
        raise ValueError("At least one navigation page must be provided.")

    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding:12px 0 20px;">
                <div style="font-size:42px;">🏥</div>
                <h2 style="margin:0;">CareFlow</h2>
                <p style="font-size:12px; opacity:0.8;">
                    Clinical Pathway Analytics
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        page = st.radio(
            "Navigation",
            options=list(pages),
            key="careflow_navigation",
        )
        st.divider()
        st.caption("Clinical Pathway Process Mining")
        show_logout_button()

    return page