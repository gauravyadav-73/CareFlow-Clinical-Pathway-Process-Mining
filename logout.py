import streamlit as st


def show_logout_button():
    """Display a logout button and clear the current session."""

    username = st.session_state.get("username", "User")

    st.caption(f"Signed in as {username}")

    if st.button(
        "🚪 Logout",
        width="stretch",
        key="careflow_logout",
    ):
        # Clear the authentication state.
        st.session_state["authenticated"] = False
        st.session_state.pop("username", None)

        # Clear the uploaded dataset from this session.
        st.session_state.pop("careflow_dataset", None)
        st.session_state.pop("careflow_filename", None)
        st.session_state.pop("careflow_upload_signature", None)
        st.session_state.pop("careflow_csv_uploader", None)
        for key in (
            "case_column_select",
            "activity_column_select",
            "timestamp_column_select",
            "selected_cases_filter",
            "selected_activities_filter",
        ):
            st.session_state.pop(key, None)

        # Return to the login screen.
        st.rerun()