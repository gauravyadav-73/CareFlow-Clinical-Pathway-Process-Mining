import pandas as pd
import streamlit as st

from utils.insights import generate_event_log_insights
from utils.report_generator import build_dataset_report, dataframe_to_csv_bytes


def render_reports(
    df: pd.DataFrame | None,
    filename: str | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Display and export an event-log summary and data-quality report."""

    st.title("Reports")
    st.write("Review and download a summary of the currently loaded dataset.")

    if df is None or df.empty:
        st.info("Upload a dataset to generate reports.")
        return

    has_valid_mapping = (
        case_column in df.columns
        and activity_column in df.columns
        and timestamp_column in df.columns
        and len({case_column, activity_column, timestamp_column}) == 3
    )
    if not has_valid_mapping:
        st.warning(
            "Select distinct case ID, activity and timestamp columns on the "
            "Upload Dataset page to include event-log metrics."
        )

    report = build_dataset_report(
        df,
        filename,
        case_column if has_valid_mapping else None,
        activity_column if has_valid_mapping else None,
        timestamp_column if has_valid_mapping else None,
    )
    summary = report["summary"]
    st.subheader("Dataset summary")
    st.dataframe(summary, width="stretch", hide_index=True)
    st.download_button(
        "Download dataset summary",
        data=dataframe_to_csv_bytes(summary),
        file_name="careflow_dataset_summary.csv",
        mime="text/csv",
        key="download_dataset_summary",
    )

    st.subheader("Column quality")
    column_quality = report["column_quality"]
    st.dataframe(column_quality, width="stretch", hide_index=True)
    st.download_button(
        "Download column quality report",
        data=dataframe_to_csv_bytes(column_quality),
        file_name="careflow_column_quality.csv",
        mime="text/csv",
        key="download_column_quality",
    )

    event_quality = report["event_quality"]
    if not event_quality.empty:
        st.subheader("Selected event-log field quality")
        st.dataframe(
            event_quality.round({"Missing (%)": 2}),
            width="stretch",
            hide_index=True,
        )
        with st.expander("Event-log insights"):
            for insight in generate_event_log_insights(
                df,
                case_column,
                activity_column,
                timestamp_column,
            ):
                st.write(f"- {insight}")

    st.subheader("Dataset preview")
    st.dataframe(df.head(20), width="stretch", hide_index=True)