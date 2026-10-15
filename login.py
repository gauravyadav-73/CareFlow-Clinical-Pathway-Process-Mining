import streamlit as st


def apply_login_styles():
    """Apply CareFlow login-page styling."""

    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f3f7fb;
        }

        .login-brand {
            font-size: 42px;
            font-weight: 800;
            color: #0f766e;
            margin-bottom: 0;
        }

        .login-subtitle {
            color: #64748b;
            font-size: 15px;
        }

        .login-panel {
            background: linear-gradient(
                145deg,
                #101d32,
                #17465b
            );
            padding: 38px;
            border-radius: 22px;
            min-height: 390px;
            color: white;
        }

        .login-panel h2 {
            color: white;
            font-size: 30px;
        }

        .login-panel p {
            color: #dbeafe;
            line-height: 1.8;
        }

        div.stButton > button[kind="primary"] {
            background-color: #0f766e;
            color: white;
            border: none;
            border-radius: 9px;
            min-height: 44px;
            font-weight: 600;
        }

        div.stButton > button[kind="primary"]:hover {
            background-color: #115e59;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_login_page():
    """Display the CareFlow login page."""

    apply_login_styles()

    left, right = st.columns([1.1, 1], gap="large")

    with left:
        st.write("")
        st.write("")

        st.markdown(
            """
            <div class="login-panel">
                <h2>Better insights.<br>Better care pathways.</h2>

                <p>
                    Welcome to CareFlow, your clinical pathway
                    process-mining workspace.
                </p>

                <br>

                <h3>Explore. Discover. Improve.</h3>

                <p>
                    Explore patient journeys, understand process
                    performance, and investigate bottlenecks
                    through interactive analytics.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.write("")
        st.write("")
        st.write("")

        st.markdown(
            '<p class="login-brand">CareFlow</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p class="login-subtitle">'
            'Clinical Pathway Intelligence Platform'
            '</p>',
            unsafe_allow_html=True,
        )

        st.divider()

        st.subheader("Welcome back")
        st.write("Sign in to access your workspace.")

        with st.form("careflow_login_form"):

            username = st.text_input(
                "Username",
                placeholder="Enter your username",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            submitted = st.form_submit_button(
                "Sign In →",
                type="primary",
                use_container_width=True,
            )

        if submitted:

            if not username or not password:
                st.warning(
                    "Please enter both your username and password."
                )
                return

            try:
                expected_username = st.secrets["auth"]["username"]
                expected_password = st.secrets["auth"]["password"]

            except (KeyError, FileNotFoundError):
                st.error(
                    "Authentication is not configured. "
                    "Check .streamlit/secrets.toml."
                )
                return

            if (
                username == expected_username
                and password == expected_password
            ):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username

                st.rerun()

            else:
                st.error(
                    "Incorrect username or password. Please try again."
                )

        st.caption("Authorized access only · CareFlow Workspace")


def require_login():
    """
    Protect the dashboard.

    Returns True if authenticated. Otherwise, shows the login
    page and stops execution of the calling Streamlit script.
    """

    if not st.session_state.get("authenticated", False):
        show_login_page()
        st.stop()

    return True