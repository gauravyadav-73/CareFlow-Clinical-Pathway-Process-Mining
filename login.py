import hashlib
import hmac
import logging
import re
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

import streamlit as st


logger = logging.getLogger(__name__)
USER_DATABASE = Path(__file__).resolve().parent / ".streamlit" / "users.db"
PASSWORD_HASH_ITERATIONS = 600_000


def _initialize_user_store():
    """Create the local account table when it does not exist yet."""

    USER_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(USER_DATABASE)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    iterations INTEGER NOT NULL
                )
                """
            )

            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(users)"
                ).fetchall()
            }
            if "username" in columns and "email" not in columns:
                connection.execute(
                    "ALTER TABLE users RENAME COLUMN username TO email"
                )
            if "name" not in columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT ''"
                )


def _register_user(email, name, password):
    """Save a new account using a salted, iterated password hash."""

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )

    _initialize_user_store()
    with closing(sqlite3.connect(USER_DATABASE)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO users (email, name, salt, password_hash, iterations)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    email.casefold(),
                    name,
                    salt.hex(),
                    password_hash.hex(),
                    PASSWORD_HASH_ITERATIONS,
                ),
            )


def _authenticate_user(email, password):
    """Check configured credentials and locally registered accounts."""

    try:
        configured_auth = st.secrets["auth"]
        configured_email = configured_auth.get(
            "email",
            configured_auth.get("username"),
        )
        configured_password = configured_auth["password"]
    except (KeyError, FileNotFoundError):
        pass
    else:
        if (
            configured_email is not None
            and hmac.compare_digest(
                email.casefold(),
                str(configured_email).strip().casefold(),
            )
            and hmac.compare_digest(password, str(configured_password))
        ):
            return str(configured_auth.get("name") or configured_email).strip()

    _initialize_user_store()
    with closing(sqlite3.connect(USER_DATABASE)) as connection:
        user = connection.execute(
            """
            SELECT name, salt, password_hash, iterations
            FROM users
            WHERE email = ?
            """,
            (email.casefold(),),
        ).fetchone()

    if user is None:
        return None

    name, salt, stored_hash, iterations = user
    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    )
    if hmac.compare_digest(candidate_hash.hex(), stored_hash):
        return name or email
    return None


def apply_login_styles():
    """Apply CareFlow login-page styling."""

    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at 18% 18%, rgba(45, 212, 191, .12) 0, transparent 28rem),
                #111827;
            color: #E5EDF5;
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(100deg, #0F766E, #0E8B83) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            min-height: 46px;
            font-weight: 700;
            box-shadow: 0 7px 16px rgba(15, 118, 110, .18);
        }

        [data-testid="stFormSubmitButton"] button:hover {
            background: #115E59 !important;
            color: #FFFFFF !important;
            transform: translateY(-1px);
        }

        .login-brand {
            font-size: 38px;
            font-weight: 800;
            color: #F1F5F9;
            letter-spacing: -1.5px;
            margin-bottom: 0;
        }

        .login-subtitle {
            color: #A2B2C4;
            font-size: 14px;
        }

        .login-panel {
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(circle at 82% 24%, rgba(45, 212, 191, .27), transparent 15rem),
                linear-gradient(145deg, #102A43 0%, #123B55 62%, #0F766E 100%);
            border: 1px solid rgba(255, 255, 255, .16);
            box-shadow: 0 22px 55px rgba(16, 42, 67, .2);
            padding: clamp(28px, 5vw, 52px);
            border-radius: 26px;
            min-height: 510px;
            color: white;
        }

        .login-panel:after {
            position: absolute;
            right: -85px;
            bottom: -115px;
            width: 300px;
            height: 300px;
            border: 1px solid rgba(204, 251, 241, .2);
            border-radius: 50%;
            box-shadow:
                0 0 0 26px rgba(204, 251, 241, .04),
                0 0 0 56px rgba(204, 251, 241, .035);
            content: "";
            pointer-events: none;
        }

        .login-eyebrow {
            color: #99F6E4;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.7px;
            text-transform: uppercase;
            margin-bottom: 34px;
        }

        .login-panel h2 {
            color: white;
            font-size: clamp(30px, 4vw, 44px);
            line-height: 1.08;
            letter-spacing: -1.5px;
            max-width: 500px;
        }

        .login-panel h3 {
            color: #FFFFFF;
            font-size: 16px;
            margin-top: 35px;
        }

        .login-panel p {
            color: #D5E9EB;
            line-height: 1.8;
            max-width: 460px;
        }

        .login-feature {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #E6FFFB;
            font-size: 12px;
            font-weight: 600;
            margin: 11px 0;
        }

        .login-feature-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            border: 1px solid rgba(153, 246, 228, .28);
            border-radius: 9px;
            background: rgba(45, 212, 191, .13);
            color: #99F6E4;
        }

        .st-key-login-card {
            background: #1F2937;
            border: 1px solid #37475A;
            border-radius: 22px;
            box-shadow: 0 18px 46px rgba(0, 0, 0, .22);
            padding: 26px clamp(24px, 4vw, 38px) 18px;
        }

        .login-kicker {
            color: #5EEAD4;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.6px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }

        div[data-baseweb="input"] > div {
            border-radius: 10px;
            min-height: 44px;
            background: #182332;
            border-color: #37475A;
        }

        [data-testid="stTextInput"] input {
            color: #E5EDF5;
            background: #182332;
        }

        .stFormSubmitButton > button[kind="primary"],
        div.stButton > button[kind="primary"] {
            background: linear-gradient(100deg, #0F766E, #0E8B83);
            color: white;
            border: none;
            border-radius: 10px;
            min-height: 46px;
            font-weight: 700;
            box-shadow: 0 7px 16px rgba(15, 118, 110, .18);
        }

        div.stButton > button[kind="primary"]:hover {
            background: #115E59;
            color: white;
            transform: translateY(-1px);
        }

        @media (max-width: 768px) {
            .login-panel {
                min-height: auto;
            }
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
                <div class="login-eyebrow">CareFlow · Pathway intelligence</div>
                <h2>See the journey.<br>Improve the care.</h2>
                <p>
                    Turn clinical event logs into a clearer picture of how
                    care moves across every patient pathway.
                </p>
                <div class="login-feature">
                    <span class="login-feature-mark">↗</span>
                    Discover real-world pathway patterns
                </div>
                <div class="login-feature">
                    <span class="login-feature-mark">◷</span>
                    Surface long event-to-event gaps
                </div>
                <div class="login-feature">
                    <span class="login-feature-mark">⌁</span>
                    Compare journeys and process variants
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.write("")
        st.write("")
        with st.container(key="login-card"):
            is_signing_up = st.session_state.get("auth_page") == "signup"
            heading = "Create your account" if is_signing_up else "Welcome back"
            subtitle = (
                "Register for a CareFlow workspace to get started."
                if is_signing_up
                else "Sign in to continue to your CareFlow workspace."
            )
            st.markdown(
                '<div class="login-kicker">Secure workspace</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<p class="login-brand">{heading}</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<p class="login-subtitle">{subtitle}</p>',
                unsafe_allow_html=True,
            )
            st.write("")
            if st.session_state.pop("signup_complete", False):
                st.success("Account created. Please sign in.")

            if is_signing_up:
                with st.form("careflow_signup_form"):
                    email = st.text_input(
                        "Email",
                        placeholder="you@example.com",
                        key="signup_email",
                    )
                    name = st.text_input(
                        "Name",
                        placeholder="Your name",
                        key="signup_name",
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Use at least 8 characters",
                        key="signup_password",
                    )
                    password_confirmation = st.text_input(
                        "Confirm password",
                        type="password",
                        placeholder="Enter your password again",
                        key="signup_password_confirmation",
                    )
                    submitted = st.form_submit_button(
                        "Create account",
                        type="primary",
                        width="stretch",
                    )

                if submitted:
                    email = email.strip().casefold()
                    name = name.strip()
                    valid_email = (
                        len(email) <= 254
                        and re.fullmatch(
                            r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+",
                            email,
                        )
                        is not None
                    )

                    if not valid_email:
                        st.warning(
                            "Enter a valid email address."
                        )
                    elif not name or len(name) > 100:
                        st.warning(
                            "Enter a name between 1 and 100 characters."
                        )
                    elif len(password) < 8 or len(password) > 1024:
                        st.warning(
                            "Your password must be between 8 and 1024 characters."
                        )
                    elif password != password_confirmation:
                        st.warning("The passwords do not match.")
                    else:
                        try:
                            _register_user(email, name, password)
                        except sqlite3.IntegrityError:
                            st.error(
                                "That email is already registered. "
                                "Please sign in instead."
                            )
                        except (sqlite3.Error, OSError):
                            logger.exception("Unable to register a CareFlow account")
                            st.error(
                                "Unable to save your account right now. "
                                "Please try again later."
                            )
                        else:
                            st.session_state["auth_page"] = "login"
                            st.session_state["login_email"] = email
                            st.session_state["signup_complete"] = True
                            st.rerun()

                if st.button(
                    "Already have an account? Sign in",
                    key="show_login",
                    width="stretch",
                ):
                    st.session_state["auth_page"] = "login"
                    st.rerun()

            else:
                with st.form("careflow_login_form"):
                    email = st.text_input(
                        "Email",
                        placeholder="you@example.com",
                        key="login_email",
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Enter your password",
                        key="login_password",
                    )
                    submitted = st.form_submit_button(
                        "Sign in to CareFlow",
                        type="primary",
                        width="stretch",
                    )

                if submitted:
                    if not email or not password:
                        st.warning(
                            "Please enter both your email and password."
                        )
                    else:
                        try:
                            authenticated_name = _authenticate_user(
                                email.strip(),
                                password,
                            )
                        except (sqlite3.Error, OSError):
                            logger.exception("Unable to authenticate a CareFlow account")
                            st.error(
                                "Unable to check your account right now. "
                                "Please try again later."
                            )
                        else:
                            if authenticated_name is not None:
                                st.session_state["authenticated"] = True
                                st.session_state["username"] = authenticated_name
                                st.rerun()
                            else:
                                st.error(
                                    "Incorrect email or password. Please try again."
                                )

                if st.button(
                    "New to CareFlow? Sign up",
                    key="show_signup",
                    width="stretch",
                ):
                    st.session_state["auth_page"] = "signup"
                    st.rerun()

                st.caption(
                    "Authorized access only · Your workspace stays private"
                )


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