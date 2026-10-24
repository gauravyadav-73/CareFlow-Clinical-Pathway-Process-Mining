import hashlib

import plotly.express as px
import streamlit as st

from utils.data_loader import load_csv, validate_event_log


def _find_column(columns: list[object], names: list[str]) -> object | None:
    lookup = {str(column).strip().lower(): column for column in columns}
    return next((lookup[name.lower()] for name in names if name.lower() in lookup), None)


def _column_index(columns: list[object], selected: object | None) -> int:
    if selected in columns:
        return columns.index(selected)
    return 0


def render_upload_dataset() -> None:
    """Upload a CSV event log, validate its mapping and filter its records."""

    st.title("Upload Clinical Event Log")
    st.write(
        "Upload a CSV where each row represents an event in a patient's "
        "clinical pathway."
    )
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        key="careflow_csv_uploader",
        help="Upload a CSV containing case IDs, activities and timestamps.",
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