import streamlit as st
import pandas as pd
import plotly.express as px

from utils.data_loader import load_csv, validate_event_log
from pages.bottleneck_analysis import render_bottleneck_analysis
from pages.conformance_analysis import render_conformance_analysis
from pages.dashboard import render_dashboard
from pages.deviation_explorer import render_deviation_explorer
from login import require_login
from logout import show_logout_button


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="CareFlow | Clinical Pathway Process Mining",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

# Display the login page if the user is not authenticated.
# This must run after st.set_page_config().
require_login()


# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
        .stApp {
            background-color: #f5f8fc;
        }

        [data-testid="stSidebar"] {
            background-color: #102a43;
        }

        [data-testid="stSidebar"] * {
            color: #ffffff;
        }

        .main-title {
            font-size: 36px;
            font-weight: 750;
            color: #102a43;
            margin-bottom: 0;
        }

        .subtitle {
            color: #627d98;
            font-size: 16px;
            margin-top: 5px;
            margin-bottom: 25px;
        }

        .section-title {
            color: #102a43;
            font-size: 24px;
            font-weight: 700;
        }

        .info-card {
            background-color: #ffffff;
            padding: 18px;
            border-radius: 12px;
            border: 1px solid #d9e2ec;
            margin-bottom: 15px;
        }

        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #d9e2ec;
            padding: 16px;
            border-radius: 12px;
        }

        div.stButton > button {
            border-radius: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "careflow_dataset" not in st.session_state:
    st.session_state["careflow_dataset"] = None

if "careflow_filename" not in st.session_state:
    st.session_state["careflow_filename"] = None


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def find_column(columns, possible_names):
    """Find a column using common column-name variations."""

    column_lookup = {
        str(column).strip().lower(): column
        for column in columns
    }

    for name in possible_names:
        if name.lower() in column_lookup:
            return column_lookup[name.lower()]

    return None


def display_placeholder(title, description):
    """Display a page whose backend functionality is not yet integrated."""

    st.markdown(
        f'<p class="section-title">{title}</p>',
        unsafe_allow_html=True,
    )

    st.info(description)

    st.caption(
        "This section can be connected to the process-mining "
        "backend as the project develops."
    )


def safe_metric(label, value):
    """Display a metric safely."""

    st.metric(label=label, value=value)


# --------------------------------------------------
# DATASET UPLOAD
# --------------------------------------------------

def upload_dataset():
    """Upload and store a CSV event log."""

    st.markdown(
        '<p class="section-title">Upload Clinical Event Log</p>',
        unsafe_allow_html=True,
    )

    st.write(
        "Upload a CSV file containing clinical pathway events. "
        "Each record should represent an event in a patient's journey."
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        key="careflow_csv_uploader",
        help="Upload a CSV containing case IDs, activities and timestamps.",
    )

    if uploaded_file is not None:

        # Reload the file when a different upload is selected.
        current_upload = (
            uploaded_file.name,
            uploaded_file.size,
        )

        previous_upload = st.session_state.get(
            "careflow_upload_signature"
        )

        if current_upload != previous_upload:

            try:
                uploaded_file.seek(0)
                df, error = load_csv(uploaded_file)

                if error:
                    st.error(f"Unable to load the CSV file: {error}")

                elif df is None or df.empty:
                    st.error(
                        "The uploaded CSV is empty. "
                        "Please upload a file containing event records."
                    )

                else:
                    st.session_state["careflow_dataset"] = df
                    st.session_state["careflow_filename"] = (
                        uploaded_file.name
                    )
                    st.session_state["careflow_upload_signature"] = (
                        current_upload
                    )

                    st.success(
                        f"Successfully loaded {uploaded_file.name}"
                    )

            except Exception as exc:
                st.error(f"Error reading the uploaded file: {exc}")

    df = st.session_state.get("careflow_dataset")

    if df is not None:
        st.success("Dataset is available for analysis.")

        col1, col2, col3 = st.columns(3)

        with col1:
            safe_metric("Total Records", len(df))

        with col2:
            safe_metric("Total Columns", len(df.columns))

        with col3:
            safe_metric(
                "Missing Values",
                int(df.isnull().sum().sum()),
            )

        st.subheader("Dataset Preview")
        st.dataframe(df.head(10), use_container_width=True)

        with st.expander("View all dataset columns"):
            st.write(list(df.columns))


# --------------------------------------------------
# DASHBOARD PAGE
# --------------------------------------------------

def show_dashboard():
    render_dashboard(
        st.session_state.get("careflow_dataset"),
        st.session_state.get("careflow_filename"),
        st.session_state.get("case_column_select"),
        st.session_state.get("activity_column_select"),
        st.session_state.get("timestamp_column_select"),
    )


# --------------------------------------------------
# UPLOAD DATASET PAGE
# --------------------------------------------------

def show_upload_page():

    upload_dataset()

    df = st.session_state.get("careflow_dataset")

    if df is None:
        return

    st.divider()

    st.markdown(
        '<p class="section-title">Event Log Validation</p>',
        unsafe_allow_html=True,
    )

    st.write(
        "Select the columns that represent the case ID, activity "
        "and event timestamp in your dataset."
    )

    columns = list(df.columns)

    case_default = find_column(
        columns,
        [
            "case_id",
            "case id",
            "case",
            "patient_id",
            "patient id",
            "patient",
        ],
    )

    activity_default = find_column(
        columns,
        [
            "activity",
            "activity_name",
            "event",
            "event_name",
            "concept:name",
        ],
    )

    timestamp_default = find_column(
        columns,
        [
            "timestamp",
            "time",
            "event_time",
            "event timestamp",
            "datetime",
            "start_timestamp",
            "time:timestamp",
        ],
    )

    def default_index(column, fallback=0):
        if column in columns:
            return columns.index(column)
        return min(fallback, len(columns) - 1)

    col1, col2, col3 = st.columns(3)

    with col1:
        case_column = st.selectbox(
            "Case ID Column",
            columns,
            index=default_index(case_default),
            key="case_column_select",
        )

    with col2:
        activity_column = st.selectbox(
            "Activity Column",
            columns,
            index=default_index(activity_default),
            key="activity_column_select",
        )

    with col3:
        timestamp_column = st.selectbox(
            "Timestamp Column",
            columns,
            index=default_index(timestamp_default),
            key="timestamp_column_select",
        )

    if len({case_column, activity_column, timestamp_column}) < 3:
        st.warning(
            "Please select three different columns for Case ID, "
            "Activity and Timestamp."
        )
        return

    try:
        validation = validate_event_log(
            df,
            case_column,
            activity_column,
            timestamp_column,
        )

        st.subheader("Validation Results")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            safe_metric(
                "Total Records",
                validation.get("total_records", len(df)),
            )

        with col2:
            safe_metric(
                "Valid Records",
                validation.get("valid_records", 0),
            )

        with col3:
            safe_metric(
                "Unique Cases",
                validation.get("unique_cases", 0),
            )

        with col4:
            safe_metric(
                "Unique Activities",
                validation.get("unique_activities", 0),
            )

        issues = validation.get("issues", [])

        if issues:
            st.warning("Some data-quality issues were detected.")

            for issue in issues:
                st.write(f"- {issue}")

        elif validation.get("valid", False):
            st.success("The event log passed the available validation checks.")

        else:
            st.info(
                "Review the validation results before using this "
                "event log for process mining."
            )

        st.subheader("Filter Event Log")

        col1, col2 = st.columns(2)

        with col1:
            available_cases = (
                df[case_column]
                .dropna()
                .unique()
                .tolist()
            )

            selected_cases = st.multiselect(
                "Select Cases",
                available_cases,
                default=available_cases,
                key="selected_cases_filter",
            )

        with col2:
            available_activities = (
                df[activity_column]
                .dropna()
                .unique()
                .tolist()
            )

            selected_activities = st.multiselect(
                "Select Activities",
                available_activities,
                default=available_activities,
                key="selected_activities_filter",
            )

        filtered_df = df[
            df[case_column].isin(selected_cases)
            & df[activity_column].isin(selected_activities)
        ].copy()

        st.subheader("Filtered Event Log")

        st.write(f"Records after filtering: **{len(filtered_df)}**")

        st.dataframe(
            filtered_df.head(100),
            use_container_width=True,
        )

        csv_data = filtered_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Filtered Event Log",
            data=csv_data,
            file_name="careflow_filtered_event_log.csv",
            mime="text/csv",
            key="download_filtered_event_log",
        )

        st.subheader("Activity Frequency")

        activity_counts = (
            filtered_df[activity_column]
            .value_counts()
            .reset_index()
        )

        activity_counts.columns = ["Activity", "Count"]

        if not activity_counts.empty:
            fig = px.bar(
                activity_counts,
                x="Activity",
                y="Count",
                title="Number of Events per Activity",
                labels={
                    "Activity": "Clinical Activity",
                    "Count": "Number of Events",
                },
            )

            fig.update_layout(
                template="plotly_white",
                xaxis_tickangle=-35,
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No records match the selected filters.")

    except Exception as exc:
        st.error(
            f"Unable to validate this event log. Details: {exc}"
        )


# --------------------------------------------------
# PROCESS DISCOVERY PAGE
# --------------------------------------------------

def show_process_discovery():

    display_placeholder(
        "Process Discovery",
        """
        This section will visualise the sequence of clinical activities
        and help identify common patient pathways.

        Process discovery will be connected to the process-mining
        backend after the required integration is completed.
        """,
    )


# --------------------------------------------------
# BOTTLENECK ANALYSIS PAGE
# --------------------------------------------------

def show_bottleneck_analysis():
    render_bottleneck_analysis(
        st.session_state.get("careflow_dataset"),
        st.session_state.get("case_column_select"),
        st.session_state.get("activity_column_select"),
        st.session_state.get("timestamp_column_select"),
    )


# --------------------------------------------------
# CONFORMANCE ANALYSIS PAGE
# --------------------------------------------------

def show_conformance_analysis():
    render_conformance_analysis(
        st.session_state.get("careflow_dataset"),
        st.session_state.get("case_column_select"),
        st.session_state.get("activity_column_select"),
        st.session_state.get("timestamp_column_select"),
    )


# --------------------------------------------------
# REPORTS PAGE
# --------------------------------------------------

def show_reports():

    st.markdown(
        '<p class="section-title">Reports</p>',
        unsafe_allow_html=True,
    )

    df = st.session_state.get("careflow_dataset")

    if df is None:
        st.info("Upload a dataset to generate a dataset summary.")
        return

    summary = pd.DataFrame(
        {
            "Metric": [
                "Dataset Filename",
                "Total Records",
                "Total Columns",
                "Missing Values",
            ],
            "Value": [
                st.session_state.get(
                    "careflow_filename",
                    "Uploaded CSV",
                ),
                len(df),
                len(df.columns),
                int(df.isnull().sum().sum()),
            ],
        }
    )

    st.subheader("Dataset Summary")
    st.dataframe(summary, use_container_width=True)

    report_csv = summary.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Dataset Summary",
        data=report_csv,
        file_name="careflow_dataset_summary.csv",
        mime="text/csv",
        key="download_dataset_summary",
    )


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------

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
        [
            "Dashboard",
            "Upload Dataset",
            "Process Discovery",
            "Bottleneck Analysis",
            "Conformance Analysis",
            "Deviation Explorer",
            "Reports",
        ],
        key="careflow_navigation",
    )

    st.divider()

    st.caption("Clinical Pathway Process Mining")

    # Logout controls from the separate logout.py file.
    show_logout_button()


# --------------------------------------------------
# PAGE ROUTING
# --------------------------------------------------

if page == "Dashboard":
    show_dashboard()

elif page == "Upload Dataset":
    show_upload_page()

elif page == "Process Discovery":
    show_process_discovery()

elif page == "Bottleneck Analysis":
    show_bottleneck_analysis()

elif page == "Conformance Analysis":
    show_conformance_analysis()

elif page == "Deviation Explorer":
    render_deviation_explorer(
        st.session_state.get("careflow_dataset"),
        st.session_state.get("case_column_select"),
        st.session_state.get("activity_column_select"),
        st.session_state.get("timestamp_column_select"),
    )

elif page == "Reports":
    show_reports()


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "CareFlow | Clinical Pathway Process Mining | "
    "Dashboard and integration prototype"
)