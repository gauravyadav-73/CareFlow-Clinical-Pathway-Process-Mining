import streamlit as st
import pandas as pd
import plotly.express as px


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="CareFlow | Clinical Process Mining",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
        .main-title {
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 0;
        }

        .subtitle {
            font-size: 16px;
            color: #64748b;
            margin-top: 4px;
        }

        div[data-testid="stMetric"] {
            background-color: #f8fafc;
            padding: 18px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("🏥 CareFlow")
    st.caption("Clinical Pathway Process Mining")

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Upload Dataset",
            "Process Discovery",
            "Bottleneck Analysis",
            "Conformance Analysis",
            "Reports"
        ]
    )

    st.divider()

    st.caption("Experience Builder")
    st.caption("UI & Integration Lead")


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    '<p class="main-title">Clinical Pathway Dashboard</p>',
    unsafe_allow_html=True
)

st.markdown(
    '<p class="subtitle">Explore patient journeys, process performance, '
    'and potential bottlenecks.</p>',
    unsafe_allow_html=True
)

st.divider()


# --------------------------------------------------
# DATA UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload a clinical pathway CSV file",
    type=["csv"],
    help="Upload a CSV containing patient case IDs, activities, "
         "and timestamps."
)


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

df = None

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        if df.empty:
            st.warning("The uploaded CSV contains no records.")
            df = None

        else:
            st.success(
                f"Dataset loaded successfully: "
                f"{len(df):,} records."
            )

    except Exception as error:
        st.error(f"Unable to read the CSV file: {error}")


# --------------------------------------------------
# DASHBOARD METRICS
# --------------------------------------------------

if df is not None:

    st.subheader("Dataset Overview")

    metric1, metric2, metric3 = st.columns(3)

    with metric1:
        st.metric("Total Records", f"{len(df):,}")

    with metric2:
        st.metric("Total Columns", len(df.columns))

    with metric3:
        st.metric(
            "Missing Values",
            f"{int(df.isna().sum().sum()):,}"
        )

    st.divider()

    # ----------------------------------------------
    # COLUMN SELECTION
    # ----------------------------------------------

    st.subheader("Configure Your Analysis")

    col1, col2 = st.columns(2)

    with col1:
        case_column = st.selectbox(
            "Select patient/case ID column",
            options=list(df.columns)
        )

    with col2:
        activity_column = st.selectbox(
            "Select activity column",
            options=list(df.columns),
            index=min(1, len(df.columns) - 1)
        )

    # ----------------------------------------------
    # CASE AND ACTIVITY METRICS
    # ----------------------------------------------

    unique_cases = df[case_column].nunique(dropna=True)
    unique_activities = df[activity_column].nunique(dropna=True)

    metric4, metric5 = st.columns(2)

    metric4.metric("Unique Cases", f"{unique_cases:,}")
    metric5.metric("Unique Activities", f"{unique_activities:,}")

    st.divider()

    # ----------------------------------------------
    # ACTIVITY FREQUENCY CHART
    # ----------------------------------------------

    st.subheader("Activity Frequency")

    activity_counts = (
        df[activity_column]
        .dropna()
        .astype(str)
        .value_counts()
        .head(15)
        .rename_axis("Activity")
        .reset_index(name="Count")
    )

    if not activity_counts.empty:
        fig = px.bar(
            activity_counts,
            x="Activity",
            y="Count",
            title="Most Frequent Clinical Activities",
            labels={
                "Activity": "Clinical Activity",
                "Count": "Number of Records"
            },
            color="Count",
            color_continuous_scale="Blues"
        )

        fig.update_layout(
            template="plotly_white",
            xaxis_tickangle=-30
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No activity values are available to plot.")

    # ----------------------------------------------
    # DATA PREVIEW
    # ----------------------------------------------

    st.subheader("Dataset Preview")

    st.dataframe(
        df.head(100),
        use_container_width=True,
        hide_index=True
    )

    # ----------------------------------------------
    # DOWNLOAD
    # ----------------------------------------------

    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Dataset as CSV",
        data=csv_data,
        file_name="careflow_dataset.csv",
        mime="text/csv"
    )

else:

    # ----------------------------------------------
    # EMPTY STATE
    # ----------------------------------------------

    st.info(
        "Upload a clinical pathway CSV file to begin your analysis. "
        "You can test the interface with sample data if you do not "
        "have the team's dataset yet."
    )

    st.subheader("Dashboard Capabilities")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📊 Process Overview")
        st.write(
            "Explore dataset records, patient cases, "
            "and clinical activities."
        )

    with col2:
        st.markdown("### 🔄 Process Discovery")
        st.write(
            "Display process graphs produced by the "
            "process-mining component."
        )

    with col3:
        st.markdown("### 🚨 Bottleneck Analysis")
        st.write(
            "Present waiting-time metrics and potential "
            "bottlenecks when backend results are available."
        )

    st.caption(
        "Process graphs, bottleneck results, and conformance "
        "metrics will be connected to the team's backend outputs."
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "CareFlow | Clinical Pathway Process Mining | "
    "UI & Integration Lead"
)