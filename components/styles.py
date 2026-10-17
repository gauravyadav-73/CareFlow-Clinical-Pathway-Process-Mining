import streamlit as st


def apply_styles():
    """
    Apply the global CareFlow dashboard theme.
    All pages should use this shared design.
    """

    st.markdown(
        """
        <style>
        /* -----------------------------------------
           GLOBAL THEME
        ----------------------------------------- */

        @import url(
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
        );

        :root {
            --cf-primary: #0F766E;
            --cf-primary-dark: #115E59;
            --cf-navy: #102A43;
            --cf-background: #F4F7FB;
            --cf-surface: #FFFFFF;
            --cf-text: #243B53;
            --cf-muted: #627D98;
            --cf-border: #E2E8F0;
            --cf-mint: #CCFBF1;
            --cf-success: #15803D;
            --cf-warning: #B45309;
            --cf-danger: #B91C1C;
        }

        html,
        body,
        [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background: var(--cf-background);
            color: var(--cf-text);
        }

        /* -----------------------------------------
           MAIN CONTENT
        ----------------------------------------- */

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        .cf-page-title {
            color: var(--cf-navy);
            font-size: clamp(27px, 3vw, 38px);
            font-weight: 800;
            letter-spacing: -1.2px;
            line-height: 1.2;
            margin-bottom: 8px;
        }

        .cf-page-subtitle {
            color: var(--cf-muted);
            font-size: 14px;
            line-height: 1.7;
            margin-bottom: 26px;
        }

        .cf-section-title {
            color: var(--cf-navy);
            font-size: 21px;
            font-weight: 700;
            letter-spacing: -0.4px;
            margin-top: 12px;
            margin-bottom: 14px;
        }

        .cf-small-label {
            color: var(--cf-muted);
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }

        /* -----------------------------------------
           HERO BANNER
        ----------------------------------------- */

        .cf-hero {
            position: relative;
            overflow: hidden;
            background: linear-gradient(
                120deg,
                #102A43 0%,
                #115E59 65%,
                #0F766E 100%
            );
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 28px;
            box-shadow: 0 10px 30px rgba(16, 42, 67, 0.10);
        }

        .cf-hero-title {
            color: #FFFFFF;
            font-size: clamp(24px, 3vw, 32px);
            font-weight: 800;
            letter-spacing: -0.8px;
            margin-bottom: 10px;
        }

        .cf-hero-description {
            color: #D9F7F2;
            font-size: 14px;
            line-height: 1.8;
            max-width: 650px;
        }

        .cf-hero-badge {
            display: inline-block;
            color: #CCFBF1;
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.20);
            padding: 6px 12px;
            border-radius: 30px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.8px;
            margin-bottom: 16px;
        }

        /* -----------------------------------------
           METRIC CARDS
        ----------------------------------------- */

        .cf-metric-card {
            background: var(--cf-surface);
            border: 1px solid var(--cf-border);
            border-radius: 16px;
            padding: 20px;
            min-height: 145px;
            box-shadow: 0 4px 15px rgba(16, 42, 67, 0.035);
            transition:
                transform 0.2s ease,
                box-shadow 0.2s ease,
                border-color 0.2s ease;
        }

        .cf-metric-card:hover {
            transform: translateY(-3px);
            border-color: #99F6E4;
            box-shadow: 0 10px 25px rgba(16, 42, 67, 0.08);
        }

        .cf-metric-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            background: #CCFBF1;
            border-radius: 12px;
            font-size: 21px;
            margin-bottom: 15px;
        }

        .cf-metric-label {
            color: var(--cf-muted);
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .cf-metric-value {
            color: var(--cf-navy);
            font-size: 29px;
            font-weight: 800;
            letter-spacing: -0.8px;
            overflow-wrap: anywhere;
        }

        .cf-metric-caption {
            color: var(--cf-muted);
            font-size: 11px;
            margin-top: 7px;
        }

        /* -----------------------------------------
           CONTENT CARDS
        ----------------------------------------- */

        .cf-card {
            background: var(--cf-surface);
            border: 1px solid var(--cf-border);
            border-radius: 16px;
            padding: 22px;
            margin-bottom: 18px;
            box-shadow: 0 4px 15px rgba(16, 42, 67, 0.035);
        }

        .cf-card-title {
            color: var(--cf-navy);
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .cf-card-description {
            color: var(--cf-muted);
            font-size: 13px;
            line-height: 1.7;
        }

        /* -----------------------------------------
           STATUS BADGES
        ----------------------------------------- */

        .cf-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 30px;
            font-size: 11px;
            font-weight: 700;
        }

        .cf-badge-success {
            color: #166534;
            background: #DCFCE7;
        }

        .cf-badge-warning {
            color: #92400E;
            background: #FEF3C7;
        }

        .cf-badge-danger {
            color: #991B1B;
            background: #FEE2E2;
        }

        .cf-badge-neutral {
            color: #334155;
            background: #E2E8F0;
        }

        /* -----------------------------------------
           SIDEBAR
        ----------------------------------------- */

        [data-testid="stSidebar"] {
            background: linear-gradient(
                180deg,
                #102A43 0%,
                #12364E 100%
            );
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        [data-testid="stSidebar"] * {
            color: #F0F9FF;
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, 0.14);
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #B8CCD9;
        }

        /* -----------------------------------------
           BUTTONS
        ----------------------------------------- */

        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            padding: 8px 18px;
            transition: all 0.2s ease;
        }

        .stButton > button[kind="primary"] {
            background: var(--cf-primary);
            border: 1px solid var(--cf-primary);
            color: #FFFFFF;
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--cf-primary-dark);
            border-color: var(--cf-primary-dark);
        }

        /* -----------------------------------------
           INPUTS
        ----------------------------------------- */

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            border-radius: 9px;
        }

        [data-testid="stFileUploader"] {
            background: #FFFFFF;
            border: 1px dashed #99B8C8;
            border-radius: 14px;
            padding: 12px;
        }

        /* -----------------------------------------
           METRICS AND TABLES
        ----------------------------------------- */

        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid var(--cf-border);
            border-radius: 14px;
            padding: 17px;
        }

        div[data-testid="stMetricLabel"] {
            color: var(--cf-muted);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--cf-border);
            border-radius: 12px;
            overflow: hidden;
        }

        /* -----------------------------------------
           EXPANDERS AND ALERTS
        ----------------------------------------- */

        [data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid var(--cf-border);
            border-radius: 12px;
        }

        div[data-testid="stAlert"] {
            border-radius: 12px;
        }

        /* -----------------------------------------
           FOOTER
        ----------------------------------------- */

        .cf-footer {
            text-align: center;
            color: #829AB1;
            font-size: 11px;
            padding: 18px 0 5px;
        }

        /* -----------------------------------------
           RESPONSIVE SPACING
        ----------------------------------------- */

        @media (max-width: 768px) {
            .block-container {
                padding-top: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .cf-hero {
                padding: 22px;
                border-radius: 15px;
            }

            .cf-metric-card {
                padding: 15px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )