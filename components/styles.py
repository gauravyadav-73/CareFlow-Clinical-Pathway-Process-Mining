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

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            border-radius: 10px;
            padding: 7px 10px;
            transition: background 0.18s ease;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: rgba(255, 255, 255, 0.09);
        }

        [data-testid="stSidebar"] button {
            border-color: rgba(255, 255, 255, 0.24);
        }

        [data-testid="stSidebar"] button:hover {
            border-color: #5EEAD4;
            color: #FFFFFF;
        }

        [data-testid="stSidebar"] a {
            border-radius: 10px;
        }

        [data-testid="stSidebar"] a[aria-current="page"] {
            background: rgba(45, 212, 191, 0.16);
            border-left: 3px solid #5EEAD4;
        }

        /* -----------------------------------------
           STREAMLIT PAGE POLISH
        ----------------------------------------- */

        .stApp {
            background:
                radial-gradient(
                    circle at 95% 2%,
                    rgba(153, 246, 228, 0.18),
                    transparent 25rem
                ),
                var(--cf-background);
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2.5rem;
        }

        h1, h2, h3 {
            color: var(--cf-navy);
            letter-spacing: -0.035em;
        }

        h1 {
            font-size: clamp(1.8rem, 3vw, 2.45rem);
            font-weight: 800;
        }

        h2 {
            font-size: 1.35rem;
            font-weight: 750;
        }

        h3 {
            font-size: 1.05rem;
            font-weight: 700;
        }

        p, [data-testid="stMarkdownContainer"] {
            line-height: 1.65;
        }

        [data-testid="stMetric"] {
            min-height: 112px;
            box-shadow: 0 5px 18px rgba(16, 42, 67, 0.045);
            transition:
                transform 0.18s ease,
                box-shadow 0.18s ease,
                border-color 0.18s ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: #99F6E4;
            box-shadow: 0 9px 24px rgba(16, 42, 67, 0.08);
        }

        [data-testid="stMetricValue"] {
            color: var(--cf-navy);
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        .stButton > button,
        .stDownloadButton > button {
            min-height: 42px;
            border-radius: 10px;
            font-weight: 650;
            transition: transform 0.16s ease, box-shadow 0.16s ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 14px rgba(15, 118, 110, 0.14);
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div {
            border-radius: 10px;
        }

        [data-testid="stFileUploader"] section {
            background: linear-gradient(145deg, #FFFFFF, #F0FDFA);
            border: 1px dashed #6FBDB3;
            border-radius: 16px;
            padding: 1rem;
        }

        [data-testid="stDataFrame"] {
            box-shadow: 0 4px 16px rgba(16, 42, 67, 0.035);
        }

        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        [data-testid="stTabs"] button {
            font-weight: 650;
        }

        .cf-brand {
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 8px 4px 16px;
        }

        .cf-brand-mark {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            flex: 0 0 42px;
            border: 1px solid rgba(94, 234, 212, 0.45);
            border-radius: 14px;
            background: rgba(45, 212, 191, 0.14);
            color: #5EEAD4;
            font-size: 23px;
        }

        .cf-brand-name {
            color: #FFFFFF;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.6px;
            line-height: 1.15;
        }

        .cf-brand-caption {
            color: #A9C8D1;
            font-size: 10px;
            letter-spacing: 0.7px;
            margin-top: 4px;
            text-transform: uppercase;
        }

        .cf-page-kicker {
            color: var(--cf-primary);
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            margin-bottom: 7px;
            text-transform: uppercase;
        }

        .cf-overview-header {
            margin: 4px 0 14px;
        }

        .cf-overview-title {
            color: var(--cf-navy);
            font-size: clamp(26px, 3vw, 34px);
            letter-spacing: -1.1px;
            line-height: 1.15;
            margin: 0 0 5px;
        }

        .cf-overview-subtitle {
            color: var(--cf-muted);
            font-size: 13px;
            margin: 0;
        }

        .cf-overview-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            margin: 0 0 16px;
        }

        .cf-overview-status {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            border: 1px solid var(--cf-border);
            border-radius: 9px;
            background: #FFFFFF;
            color: var(--cf-text);
            font-size: 11px;
            font-weight: 650;
            max-width: 100%;
            overflow-wrap: anywhere;
            padding: 7px 10px;
        }

        .cf-overview-status-ready {
            border-color: #A7F3D0;
            color: #047857;
        }

        .cf-overview-status-dot {
            width: 7px;
            height: 7px;
            flex: 0 0 7px;
            border-radius: 50%;
            background: #10B981;
        }

        .cf-overview-status-empty .cf-overview-status-dot {
            background: #94A3B8;
        }

        .cf-overview-date {
            color: var(--cf-muted);
            font-size: 11px;
            text-align: right;
        }

        .cf-overview-metric {
            position: relative;
            min-height: 137px;
            overflow: hidden;
            border: 1px solid var(--cf-border);
            border-top: 3px solid var(--cf-accent, var(--cf-primary));
            border-radius: 13px;
            background: #FFFFFF;
            box-shadow: 0 4px 14px rgba(16, 42, 67, 0.04);
            margin-bottom: 10px;
            padding: 13px 15px;
        }

        .cf-accent-blue {
            --cf-accent: #3B82F6;
            --cf-icon-background: #EFF6FF;
        }

        .cf-accent-purple {
            --cf-accent: #8B5CF6;
            --cf-icon-background: #F5F3FF;
        }

        .cf-accent-teal {
            --cf-accent: #0F766E;
            --cf-icon-background: #CCFBF1;
        }

        .cf-accent-orange {
            --cf-accent: #F59E0B;
            --cf-icon-background: #FFF7ED;
        }

        .cf-accent-red {
            --cf-accent: #EF4444;
            --cf-icon-background: #FFF1F2;
        }

        .cf-overview-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            border-radius: 10px;
            background: var(--cf-icon-background, #F1F5F9);
            color: var(--cf-accent, var(--cf-primary));
            font-size: 18px;
            margin-bottom: 9px;
        }

        .cf-overview-label {
            color: var(--cf-muted);
            font-size: 11px;
            font-weight: 650;
        }

        .cf-overview-value {
            color: var(--cf-navy);
            font-size: clamp(22px, 2.3vw, 29px);
            font-weight: 800;
            letter-spacing: -0.7px;
            line-height: 1.2;
            margin-top: 1px;
        }

        .cf-overview-note {
            color: var(--cf-muted);
            font-size: 10px;
            line-height: 1.4;
            margin-top: 4px;
        }

        .cf-process-map-heading {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            margin: 8px 0 9px;
        }

        .cf-process-map-heading h2 {
            color: var(--cf-navy);
            font-size: 18px;
            margin: 0;
        }

        .cf-process-map-heading p {
            color: var(--cf-muted);
            font-size: 11px;
            margin: 2px 0 0;
        }

        .cf-process-map-chip {
            border: 1px solid #DBEAFE;
            border-radius: 8px;
            background: #EFF6FF;
            color: #1D4ED8;
            font-size: 10px;
            font-weight: 650;
            padding: 6px 9px;
        }

        .cf-process-map-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 17px;
            border-top: 1px solid var(--cf-border);
            color: var(--cf-muted);
            font-size: 10px;
            margin-top: 5px;
            padding-top: 11px;
        }

        .cf-process-map-legend span {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .cf-legend-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .cf-legend-start {
            background: #86EFAC;
        }

        .cf-legend-common {
            background: #0F766E;
        }

        .cf-legend-alternative {
            background: #3B82F6;
        }

        .cf-dashboard-hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 22px;
            background:
                radial-gradient(
                    circle at 85% 20%,
                    rgba(45, 212, 191, 0.27),
                    transparent 18rem
                ),
                linear-gradient(118deg, #102A43 0%, #123B55 62%, #0F766E 100%);
            box-shadow: 0 16px 38px rgba(16, 42, 67, 0.16);
            margin-bottom: 23px;
            padding: clamp(23px, 3.6vw, 38px);
        }

        .cf-dashboard-hero:after {
            position: absolute;
            top: -90px;
            right: -35px;
            width: 260px;
            height: 260px;
            border: 1px solid rgba(204, 251, 241, 0.15);
            border-radius: 50%;
            box-shadow:
                0 0 0 28px rgba(204, 251, 241, 0.035),
                0 0 0 58px rgba(204, 251, 241, 0.025);
            content: "";
            pointer-events: none;
        }

        .cf-dashboard-kicker {
            color: #99F6E4;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            margin-bottom: 12px;
            text-transform: uppercase;
        }

        .cf-dashboard-title {
            color: #FFFFFF;
            font-size: clamp(27px, 4vw, 40px);
            font-weight: 800;
            letter-spacing: -1.6px;
            line-height: 1.1;
            margin: 0 0 10px;
        }

        .cf-dashboard-copy {
            color: #D5E9EB;
            font-size: 14px;
            line-height: 1.7;
            margin: 0;
            max-width: 680px;
        }

        .cf-live-pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            border: 1px solid rgba(153, 246, 228, 0.3);
            border-radius: 999px;
            background: rgba(15, 118, 110, 0.25);
            color: #D1FAE5;
            font-size: 11px;
            font-weight: 700;
            margin-top: 20px;
            padding: 7px 11px;
        }

        .cf-live-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #5EEAD4;
            box-shadow: 0 0 0 4px rgba(94, 234, 212, 0.13);
        }

        .cf-footer {
            border-top: 1px solid var(--cf-border);
            margin-top: 26px;
            padding-top: 16px;
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

            [data-testid="stSidebar"] {
                border-right: 0;
            }

            .cf-hero {
                padding: 22px;
                border-radius: 15px;
            }

            .cf-metric-card {
                padding: 15px;
            }

            [data-testid="stMetric"] {
                min-height: 96px;
                padding: 13px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )