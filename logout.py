import streamlit as st


def show_logout_button():
    """Display a logout button and clear the current session."""

    username = st.session_state.get("username", "User")

    st.caption(f"Signed in as {username}")

    if st.button(
        "🚪 Logout",
        use_container_width=True,
        key="careflow_logout",
    ):
        # Clear the authentication state.
        st.session_state["authenticated"] = False
        st.session_state.pop("username", None)

        # Clear the uploaded dataset from this session.
        st.session_state.pop("careflow_dataset", None)
        st.session_state.pop("careflow_filename", None)

        # Return to the login screen.
        st.rerun()