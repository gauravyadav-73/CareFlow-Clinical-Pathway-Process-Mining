import hashlib

import plotly.express as px
import streamlit as st

from utils.data_loader import load_csv, validate_event_log


SAMPLE_EVENT_LOG = """patient_id,event_name,event_time
P-1001,Emergency department arrival,2025-01-12 08:15:00
P-1001,Initial assessment,2025-01-12 08:42:00
P-1001,Diagnostic imaging,2025-01-12 09:30:00
P-1001,Discharge,2025-01-12 12:10:00
P-1002,Emergency department arrival,2025-01-13 10:05:00
P-1002,Initial assessment,2025-01-13 10:24:00
P-1002,Lab tests,2025-01-13 11:10:00
P-1002,Discharge,2025-01-13 14:35:00
"""


def _find_column(columns: list[object], names: list[str]) -> object | None:
    lookup = {str(column).strip().lower(): column for column in columns}
    return next((lookup[name.lower()] for name in names if name.lower() in lookup), None)


def _column_index(columns: list[object], selected: object | None) -> int:
    if selected in columns:
        return columns.index(selected)
    return 0


def _render_upload_stepper() -> None:
    steps = ("Upload", "Map Columns", "Validate", "Preview")
    step_markup = "".join(
        f"""
        <div class="cf-upload-step">
            <span class="cf-upload-step-number">{index}</span>
            <span class="cf-upload-step-label">{label}</span>
        </div>
        """
        for index, label in enumerate(steps, start=1)
    )
    st.markdown(
        f"""
        <style>
        .cf-upload-header {{ margin: 0 0 1.1rem; }}
        .cf-upload-kicker {{
            color: #0F766E; font-size: 10px; font-weight: 800;
            letter-spacing: 1.35px; text-transform: uppercase; margin-bottom: 5px;
        }}
        .cf-upload-title {{
            color: #102A43; font-size: clamp(26px, 3vw, 35px);
            font-weight: 800; letter-spacing: -1px; line-height: 1.18;
            margin: 0 0 5px;
        }}
        .cf-upload-subtitle {{ color: #627D98; font-size: 13px; margin: 0; }}
        .cf-upload-steps {{
            display: flex; align-items: flex-start; margin: 1.25rem 0 1.4rem;
        }}
        .cf-upload-step {{
            display: flex; align-items: center; flex: 1; position: relative;
            flex-direction: column; gap: 6px; color: #627D98; text-align: center;
        }}
        .cf-upload-step:not(:last-child)::after {{
            content: ""; height: 2px; position: absolute;
            top: 15px; left: calc(50% + 21px); right: calc(-50% + 21px);
            background: #D7E2EE;
        }}
        .cf-upload-step:first-child .cf-upload-step-number {{
            color: #fff; background: #0876D1; border-color: #0876D1;
            box-shadow: 0 3px 8px rgba(8, 118, 209, .2);
        }}
        .cf-upload-step-number {{
            display: flex; align-items: center; justify-content: center;
            width: 31px; height: 31px; border: 1px solid #D7E2EE;
            border-radius: 50%; background: #F7FAFD; color: #506782;
            font-size: 12px; font-weight: 750; z-index: 1;
        }}
        .cf-upload-step-label {{ font-size: 11px; font-weight: 650; }}
        .cf-upload-panel {{
            background: #FFFFFF; border: 1px solid #DCE7F2; border-radius: 14px;
            padding: 17px 18px; min-height: 200px;
            box-shadow: 0 4px 14px rgba(16, 42, 67, .035);
        }}
        .cf-upload-panel-title {{
            color: #102A43; font-size: 14px; font-weight: 750; margin-bottom: 5px;
        }}
        .cf-upload-panel-copy {{ color: #627D98; font-size: 11px; margin-bottom: 14px; }}
        .cf-expected-column {{
            display: flex; align-items: flex-start; gap: 9px;
            color: #334E68; font-size: 11px; line-height: 1.45; margin: 11px 0;
        }}
        .cf-expected-icon {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 22px; height: 22px; flex: 0 0 22px; border-radius: 7px;
            background: #EAF4FF; color: #0876D1; font-weight: 800;
        }}
        .cf-expected-column strong {{ color: #243B53; }}
        .cf-sample-title {{ color: #243B53; font-size: 12px; font-weight: 750; }}
        .cf-sample-copy {{ color: #627D98; font-size: 11px; }}
        @media (max-width: 700px) {{
            .cf-upload-panel {{ min-height: auto; margin-top: 10px; }}
            .cf-upload-step-label {{ font-size: 10px; }}
        }}
        </style>
        <div class="cf-upload-header">
            <div class="cf-upload-kicker">Dataset setup</div>
            <h1 class="cf-upload-title">Upload Clinical Event Log</h1>
            <p class="cf-upload-subtitle">
                Upload and configure your dataset to start the analysis.
            </p>
        </div>
        <div class="cf-upload-steps">{step_markup}</div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_dataset() -> None:
    """Upload a CSV event log, validate its mapping and filter its records."""

    _render_upload_stepper()

    upload_col, info_col = st.columns([1.55, 1], gap="medium")
    with upload_col:
        uploaded_file = st.file_uploader(
            "Upload your event log",
            type=["csv"],
            key="careflow_csv_uploader",
            help="CSV files only. Include a case ID, activity and timestamp column.",
            label_visibility="collapsed",
        )
        st.caption("Supported format: CSV")

    upload_status = (
        "A file is selected. Your event log should include:"
        if uploaded_file is not None
        else "No file uploaded yet. Your event log should include:"
    )
    with info_col:
        st.markdown(
            f"""
            <div class="cf-upload-panel">
                <div class="cf-upload-panel-title">Dataset Information</div>
                <div class="cf-upload-panel-copy">
                    {upload_status}
                </div>
                <div class="cf-expected-column">
                    <span class="cf-expected-icon">ID</span>
                    <span><strong>Case ID</strong><br>e.g., patient_id</span>
                </div>
                <div class="cf-expected-column">
                    <span class="cf-expected-icon">A</span>
                    <span><strong>Activity</strong><br>e.g., event_name</span>
                </div>
                <div class="cf-expected-column">
                    <span class="cf-expected-icon">T</span>
                    <span><strong>Timestamp</strong><br>e.g., event_time</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    sample_col, download_col = st.columns([3, 1])
    with sample_col:
        st.markdown(
            """
            <div class="cf-sample-title">Need a sample file?</div>
            <div class="cf-sample-copy">
                Download a sample event log to see the required format.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with download_col:
        st.download_button(
            "Download Sample",
            data=SAMPLE_EVENT_LOG.encode("utf-8"),
            file_name="careflow_sample_event_log.csv",
            mime="text/csv",
            key="download_sample_event_log",
            use_container_width=True,
        )

    if uploaded_file is not None:
        uploaded_file.seek(0)
        content_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
        current_upload = (
            uploaded_file.name,
            uploaded_file.size,
            content_hash,
        )
        if current_upload != st.session_state.get("careflow_upload_signature"):
            uploaded_file.seek(0)
            dataset, error = load_csv(uploaded_file)
            if error:
                st.error(f"Unable to load the CSV file: {error}")
            elif dataset is None or dataset.empty:
                st.error(
                    "The uploaded CSV is empty. Please upload a file "
                    "containing event records."
                )
            else:
                st.session_state["careflow_dataset"] = dataset
                st.session_state["careflow_filename"] = uploaded_file.name
                st.session_state["careflow_upload_signature"] = current_upload
                for key in (
                    "case_column_select",
                    "activity_column_select",
                    "timestamp_column_select",
                    "selected_cases_filter",
                    "selected_activities_filter",
                ):
                    st.session_state.pop(key, None)
                st.success(f"Successfully loaded {uploaded_file.name}")

    df = st.session_state.get("careflow_dataset")
    if df is None or df.empty:
        st.info("Upload a CSV event log to begin.")
        return

    st.success("Dataset is available for analysis.")
    summary_cols = st.columns(3)
    summary_cols[0].metric("Total records", f"{len(df):,}")
    summary_cols[1].metric("Total columns", f"{len(df.columns):,}")
    summary_cols[2].metric("Missing values", f"{int(df.isna().sum().sum()):,}")
    st.subheader("Dataset preview")
    st.dataframe(df.head(10), width="stretch", hide_index=True)
    with st.expander("View all dataset columns"):
        st.write(list(df.columns))

    columns = list(df.columns)
    case_default = _find_column(
        columns,
        ["case_id", "case id", "case", "patient_id", "patient id", "patient"],
    )
    activity_default = _find_column(
        columns,
        ["activity", "activity_name", "event", "event_name", "concept:name"],
    )
    timestamp_default = _find_column(
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

    st.divider()
    st.subheader("Event-log column mapping")
    st.write(
        "Choose the columns representing the case ID, clinical activity and "
        "event timestamp."
    )
    map_cols = st.columns(3)
    with map_cols[0]:
        case_column = st.selectbox(
            "Case ID column",
            columns,
            index=_column_index(columns, case_default),
            key="case_column_select",
        )
    with map_cols[1]:
        activity_column = st.selectbox(
            "Activity column",
            columns,
            index=_column_index(columns, activity_default),
            key="activity_column_select",
        )
    with map_cols[2]:
        timestamp_column = st.selectbox(
            "Timestamp column",
            columns,
            index=_column_index(columns, timestamp_default),
            key="timestamp_column_select",
        )

    if len({case_column, activity_column, timestamp_column}) != 3:
        st.warning(
            "Choose three different columns for case ID, activity and timestamp."
        )
        return

    validation = validate_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    st.subheader("Validation results")
    validation_cols = st.columns(4)
    validation_cols[0].metric(
        "Valid records",
        f"{validation.get('valid_records', 0):,}",
    )
    validation_cols[1].metric(
        "Unique cases",
        f"{validation.get('unique_cases', 0):,}",
    )
    validation_cols[2].metric(
        "Unique activities",
        f"{validation.get('unique_activities', 0):,}",
    )
    validation_cols[3].metric(
        "Duplicate events",
        f"{validation.get('duplicate_events', 0):,}",
    )
    issues = validation.get("issues", [])
    if issues:
        st.warning("Some data-quality issues were detected.")
        for issue in issues:
            st.write(f"- {issue}")
    elif validation.get("valid", False):
        st.success("The event log passed the available validation checks.")
    else:
        st.info("Review the validation results before process-mining analysis.")

    st.subheader("Filter event log")
    filter_cols = st.columns(2)
    available_cases = df[case_column].dropna().unique().tolist()
    available_activities = df[activity_column].dropna().unique().tolist()
    with filter_cols[0]:
        selected_cases = st.multiselect(
            "Cases",
            available_cases,
            default=available_cases,
            key="selected_cases_filter",
        )
    with filter_cols[1]:
        selected_activities = st.multiselect(
            "Activities",
            available_activities,
            default=available_activities,
            key="selected_activities_filter",
        )

    filtered_df = df[
        df[case_column].isin(selected_cases)
        & df[activity_column].isin(selected_activities)
    ].copy()
    st.write(f"Records after filtering: **{len(filtered_df):,}**")
    st.dataframe(filtered_df.head(100), width="stretch")
    st.download_button(
        "Download filtered event log",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="careflow_filtered_event_log.csv",
        mime="text/csv",
        key="download_filtered_event_log",
    )

    st.subheader("Activity frequency")
    activity_counts = (
        filtered_df[activity_column]
        .dropna()
        .astype(str)
        .value_counts()
        .rename_axis("Activity")
        .reset_index(name="Events")
    )
    if activity_counts.empty:
        st.info("No records match the selected filters.")
    else:
        fig = px.bar(
            activity_counts,
            x="Activity",
            y="Events",
            title="Number of events per activity",
            labels={"Activity": "Clinical activity"},
        )
        fig.update_layout(template="plotly_white", xaxis_tickangle=-35)
        st.plotly_chart(fig, width="stretch")