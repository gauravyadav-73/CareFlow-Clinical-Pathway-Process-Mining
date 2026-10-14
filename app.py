import streamlit as st
import pandas as pd
import plotly.express as px

from utils.data_loader import load_csv, validate_event_log


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="CareFlow | Clinical Process Mining",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 0;
        }

        .subtitle {
            font-size: 15px;
            color: #64748b;
            margin-top: 5px;
            margin-bottom: 20px;
        }

        .section-caption {
            color: #64748b;
            font-size: 14px;
        }

        div[data-testid="stMetric"] {
            background-color: #f8fafc;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
        }

        .status-label {
            font-size: 13px;
            color: #64748b;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def find_column(columns, keywords, default_index=0):
    """Find a likely column based on its name."""

    for column in columns:
        normalized = str(column).strip().lower().replace("_", " ")

        if any(keyword in normalized for keyword in keywords):
            return column

    return columns[min(default_index, len(columns) - 1)]


def display_placeholder(title, description):
    """Display a feature that awaits backend integration."""

    st.info(description)

    st.markdown("### Integration status")
    st.warning(
        "This feature is awaiting integration with the team's "
        "process-mining backend. No real analysis results are "
        "being generated on this page yet."
    )

    st.markdown("### Expected functionality")
    st.write(title)


def safe_metric(value):
    """Format a numeric metric."""

    return f"{value:,}"


# ============================================================
# 4. SESSION STATE
# ============================================================

if "careflow_dataset" not in st.session_state:
    st.session_state.careflow_dataset = None

if "careflow_filename" not in st.session_state:
    st.session_state.careflow_filename = None


# ============================================================
# 5. SIDEBAR NAVIGATION
# ============================================================

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
            "Reports",
        ],
        key="careflow_navigation",
    )

    st.divider()

    st.markdown("#### Project information")
    st.caption("Experience Builder")
    st.caption("UI & Integration Lead")

    st.divider()

    st.caption("Clinical process analytics")


# ============================================================
# 6. APPLICATION HEADER
# ============================================================

st.markdown(
    '<p class="main-title">CareFlow</p>',
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="subtitle">'
    'Clinical Pathway Process Mining | Patient Journey Analytics'
    '</p>',
    unsafe_allow_html=True,
)


# ============================================================
# 7. DATA UPLOAD
# ============================================================

# The upload widget is available from both the Dashboard
# and Upload Dataset pages.

if page in ["Dashboard", "Upload Dataset"]:

    with st.expander(
        "📂 Upload or replace a clinical dataset",
        expanded=(page == "Upload Dataset"),
    ):

        uploaded_file = st.file_uploader(
            "Choose a clinical pathway CSV file",
            type=["csv"],
            key="careflow_csv_upload",
            help=(
                "Upload an anonymized or synthetic event log. "
                "Do not upload identifiable patient information."
            ),
        )

        if uploaded_file is not None:

            should_load = (
                st.session_state.careflow_filename
                != uploaded_file.name
            )

            if should_load:

                loaded_df, error_message = load_csv(uploaded_file)

                if error_message:
                    st.error(error_message)

                else:
                    st.session_state.careflow_dataset = loaded_df
                    st.session_state.careflow_filename = (
                        uploaded_file.name
                    )

                    st.success(
                        f"Loaded {len(loaded_df):,} records "
                        f"from {uploaded_file.name}."
                    )

        if st.session_state.careflow_dataset is not None:

            st.caption(
                f"Current dataset: "
                f"{st.session_state.careflow_filename}"
            )


# ============================================================
# 8. RETRIEVE DATASET
# ============================================================

df = st.session_state.careflow_dataset


# ============================================================
# 9. DASHBOARD PAGE
# ============================================================

if page == "Dashboard":

    st.subheader("📊 Clinical Pathway Dashboard")

    st.write(
        "Explore patient cases, clinical activities, "
        "and event-log quality."
    )

    if df is None:

        st.info(
            "Upload a CSV file using the section above or open "
            "'Upload Dataset' from the sidebar to begin."
        )

        st.subheader("Dashboard capabilities")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### 📂 Dataset Analysis")
            st.write(
                "Upload an event log and inspect patient cases "
                "and clinical activities."
            )

        with col2:
            st.markdown("### 🔄 Process Discovery")
            st.write(
                "Integrate the process graph generated by "
                "the process-mining backend."
            )

        with col3:
            st.markdown("### 🚨 Bottleneck Analysis")
            st.write(
                "Display activity durations, waiting times, "
                "and bottleneck alerts when available."
            )

    else:

        # Dataset-level metrics.
        total_records = len(df)
        total_columns = len(df.columns)
        missing_values = int(df.isna().sum().sum())

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric(
            "Total Records",
            safe_metric(total_records),
        )

        metric2.metric(
            "Total Columns",
            safe_metric(total_columns),
        )

        metric3.metric(
            "Missing Values",
            safe_metric(missing_values),
        )

        st.divider()

        st.subheader("Dataset Preview")

        st.dataframe(
            df.head(10),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "For column selection and event-log validation, "
            "open Upload Dataset."
        )


# ============================================================
# 10. UPLOAD DATASET PAGE
# ============================================================

elif page == "Upload Dataset":

    st.subheader("📂 Dataset Upload & Validation")

    st.write(
        "Inspect the event log, select its process-mining columns, "
        "and check its data quality."
    )

    if df is None:

        st.info(
            "Upload a CSV file using the uploader above "
            "to begin dataset validation."
        )

    else:

        columns = list(df.columns)

        st.subheader("1. Dataset Overview")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Records",
            safe_metric(len(df)),
        )

        col2.metric(
            "Total Columns",
            safe_metric(len(columns)),
        )

        col3.metric(
            "Missing Values",
            safe_metric(int(df.isna().sum().sum())),
        )

        st.divider()

        # ----------------------------------------------
        # COLUMN SELECTION
        # ----------------------------------------------

        st.subheader("2. Configure Event Log")

        case_default = find_column(
            columns,
            ["case id", "case", "patient id", "patient", "trace id"],
            0,
        )

        activity_default = find_column(
            columns,
            ["activity", "event", "task", "operation"],
            min(1, len(columns) - 1),
        )

        timestamp_default = find_column(
            columns,
            ["timestamp", "time", "date"],
            min(2, len(columns) - 1),
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            case_column = st.selectbox(
                "Case ID column",
                columns,
                index=columns.index(case_default),
                key="dataset_case_column",
            )

        with col2:
            activity_column = st.selectbox(
                "Activity column",
                columns,
                index=columns.index(activity_default),
                key="dataset_activity_column",
            )

        with col3:
            timestamp_column = st.selectbox(
                "Timestamp column",
                columns,
                index=columns.index(timestamp_default),
                key="dataset_timestamp_column",
            )

        # The same column cannot represent all three fields.
        selected_columns = {
            case_column,
            activity_column,
            timestamp_column,
        }

        if len(selected_columns) != 3:

            st.warning(
                "Select three different columns for Case ID, "
                "Activity, and Timestamp."
            )

        else:

            # ------------------------------------------
            # VALIDATE EVENT LOG
            # ------------------------------------------

            result = validate_event_log(
                df,
                case_column,
                activity_column,
                timestamp_column,
            )

            valid_df = result.get(
                "valid_rows",
                pd.DataFrame(),
            ).copy()

            st.divider()

            st.subheader("3. Data Quality Results")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Total Records",
                safe_metric(len(df)),
            )

            col2.metric(
                "Valid Records",
                safe_metric(len(valid_df)),
            )

            col3.metric(
                "Unique Patient Cases",
                safe_metric(
                    valid_df[case_column].nunique()
                    if not valid_df.empty
                    else 0
                ),
            )

            col4, col5, col6 = st.columns(3)

            col4.metric(
                "Unique Activities",
                safe_metric(
                    valid_df[activity_column].nunique()
                    if not valid_df.empty
                    else 0
                ),
            )

            col5.metric(
                "Missing Values",
                safe_metric(int(df.isna().sum().sum())),
            )

            col6.metric(
                "Potential Duplicates",
                safe_metric(
                    int(result.get("duplicate_events", 0))
                ),
            )

            # ------------------------------------------
            # WARNINGS
            # ------------------------------------------

            issues = result.get("issues", [])

            if issues:

                st.subheader("Data Quality Warnings")

                for issue in issues:
                    st.warning(issue)

            else:

                st.success(
                    "No data-quality issues were detected "
                    "by the configured checks."
                )

            # ------------------------------------------
            # INTERACTIVE FILTERS
            # ------------------------------------------

            st.divider()

            st.subheader("4. Interactive Clinical Activity Filters")

            if valid_df.empty:

                st.warning(
                    "No valid event records are available "
                    "for filtering."
                )

            else:

                filter_col1, filter_col2 = st.columns(2)

                available_cases = sorted(
                    valid_df[case_column]
                    .astype(str)
                    .unique()
                    .tolist()
                )

                available_activities = sorted(
                    valid_df[activity_column]
                    .astype(str)
                    .unique()
                    .tolist()
                )

                with filter_col1:

                    selected_cases = st.multiselect(
                        "Select patient cases",
                        options=available_cases,
                        default=available_cases,
                        key="filter_cases",
                    )

                with filter_col2:

                    selected_activities = st.multiselect(
                        "Select clinical activities",
                        options=available_activities,
                        default=available_activities,
                        key="filter_activities",
                    )

                # Apply the filters.
                filtered_df = valid_df[
                    valid_df[case_column]
                    .astype(str)
                    .isin(selected_cases)
                    &
                    valid_df[activity_column]
                    .astype(str)
                    .isin(selected_activities)
                ].copy()

                # --------------------------------------
                # FILTERED METRICS
                # --------------------------------------

                st.write(
                    f"Filtered records: **{len(filtered_df):,}**"
                )

                metric1, metric2, metric3 = st.columns(3)

                metric1.metric(
                    "Filtered Records",
                    safe_metric(len(filtered_df)),
                )

                metric2.metric(
                    "Patient Cases",
                    safe_metric(
                        filtered_df[case_column].nunique()
                    ),
                )

                metric3.metric(
                    "Clinical Activities",
                    safe_metric(
                        filtered_df[activity_column].nunique()
                    ),
                )

                # --------------------------------------
                # ACTIVITY FREQUENCY CHART
                # --------------------------------------

                st.subheader("5. Clinical Activity Frequency")

                if not filtered_df.empty:

                    activity_counts = (
                        filtered_df[activity_column]
                        .astype(str)
                        .value_counts()
                        .rename_axis("Activity")
                        .reset_index(name="Records")
                    )

                    fig = px.bar(
                        activity_counts,
                        x="Activity",
                        y="Records",
                        title="Frequency of Clinical Activities",
                        labels={
                            "Activity": "Clinical Activity",
                            "Records": "Number of Records",
                        },
                        color="Records",
                        color_continuous_scale="Blues",
                    )

                    fig.update_layout(
                        template="plotly_white",
                        xaxis_tickangle=-30,
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

                else:

                    st.warning(
                        "No records match the selected filters."
                    )

                # --------------------------------------
                # DOWNLOAD FILTERED DATA
                # --------------------------------------

                st.subheader("6. Download Filtered Event Log")

                if not filtered_df.empty:

                    filtered_csv = filtered_df.to_csv(
                        index=False
                    ).encode("utf-8")

                    st.download_button(
                        "⬇️ Download Filtered Dataset",
                        data=filtered_csv,
                        file_name="careflow_filtered_dataset.csv",
                        mime="text/csv",
                        key="download_filtered",
                    )

            # ------------------------------------------
            # DATASET PREVIEW
            # ------------------------------------------

            st.divider()

            st.subheader("7. Validated Dataset Preview")

            if not valid_df.empty:

                st.dataframe(
                    valid_df.head(100),
                    use_container_width=True,
                    hide_index=True,
                )

                validated_csv = valid_df.to_csv(
                    index=False
                ).encode("utf-8")

                st.download_button(
                    "⬇️ Download Validated Event Log",
                    data=validated_csv,
                    file_name="careflow_valid_event_log.csv",
                    mime="text/csv",
                    key="download_validated",
                )

            else:

                st.info(
                    "There are no valid event records to preview."
                )


# ============================================================
# 11. PROCESS DISCOVERY PAGE
# ============================================================

elif page == "Process Discovery":

    st.subheader("🔄 Process Discovery")

    st.write(
        "Explore the sequence of clinical activities "
        "in the patient journey."
    )

    if df is None:

        st.info(
            "Upload a dataset before exploring process discovery."
        )

    else:

        display_placeholder(
            "Display a process graph showing activities, "
            "transitions, and their frequencies.",
            "The process-discovery visualization will appear "
            "here after backend integration.",
        )

        st.markdown(
            """
            **Expected backend integration**

            - Process graph or visualization
            - Activity transitions
            - Transition frequencies
            - Process model output
            """
        )


# ============================================================
# 12. BOTTLENECK ANALYSIS PAGE
# ============================================================

elif page == "Bottleneck Analysis":

    st.subheader("🚨 Bottleneck Analysis")

    st.write(
        "Identify clinical activities associated with "
        "long durations or waiting times."
    )

    if df is None:

        st.info(
            "Upload a dataset before exploring bottleneck analysis."
        )

    else:

        display_placeholder(
            "Display activities with unusually long waiting times, "
            "duration metrics, and bottleneck alerts.",
            "Bottleneck results will appear here after the "
            "team's backend analysis is integrated.",
        )

        st.markdown(
            """
            **Expected backend integration**

            - Average activity duration
            - Waiting-time analysis
            - High-delay activities
            - Bottleneck alerts
            """
        )


# ============================================================
# 13. CONFORMANCE ANALYSIS PAGE
# ============================================================

elif page == "Conformance Analysis":

    st.subheader("📊 Conformance Analysis")

    st.write(
        "Compare observed patient journeys with the "
        "expected clinical process."
    )

    if df is None:

        st.info(
            "Upload a dataset before exploring conformance analysis."
        )

    else:

        display_placeholder(
            "Display conformance metrics and deviations "
            "from the expected process.",
            "Conformance results will appear here after "
            "backend integration.",
        )

        st.markdown(
            """
            **Expected backend integration**

            - Conformance score
            - Deviations from the expected pathway
            - Non-conforming cases
            - Conformance result summaries
            """
        )


# ============================================================
# 14. REPORTS PAGE
# ============================================================

elif page == "Reports":

    st.subheader("📄 CareFlow Reports")

    st.write(
        "Review and download the available dataset and "
        "analysis outputs."
    )

    if df is None:

        st.info(
            "Upload a dataset before generating dataset reports."
        )

    else:

        st.subheader("Dataset Summary")

        summary = pd.DataFrame(
            {
                "Metric": [
                    "Total Records",
                    "Total Columns",
                    "Missing Values",
                ],
                "Value": [
                    len(df),
                    len(df.columns),
                    int(df.isna().sum().sum()),
                ],
            }
        )

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
        )

        summary_csv = summary.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Dataset Summary",
            data=summary_csv,
            file_name="careflow_dataset_summary.csv",
            mime="text/csv",
            key="download_summary",
        )

        st.divider()

        st.info(
            "Process discovery, bottleneck, and conformance reports "
            "will be added when their backend outputs are integrated."
        )


# ============================================================
# 15. FOOTER
# ============================================================

st.divider()

st.caption(
    "CareFlow | Clinical Pathway Process Mining | "
    "UI & Integration Lead"
)