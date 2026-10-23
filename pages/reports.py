import pandas as pd
import streamlit as st

from utils.data_loader import validate_event_log


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

    total_records = len(df)
    missing_cells = int(df.isna().sum().sum())
    summary_items: list[tuple[str, str | int | float]] = [
        ("Dataset filename", filename or "Uploaded CSV"),
        ("Total records", total_records),
        ("Total columns", len(df.columns)),
        ("Missing cells", missing_cells),
        (
            "Duplicate rows",
            int(df.duplicated().sum()),
        ),
    ]

    has_valid_mapping = (
        case_column in df.columns
        and activity_column in df.columns
        and timestamp_column in df.columns
        and len({case_column, activity_column, timestamp_column}) == 3
    )
    quality_rows = []
    if has_valid_mapping:
        validation = validate_event_log(
            df,
            case_column,
            activity_column,
            timestamp_column,
        )
        summary_items.extend(
            [
                ("Valid event records", int(validation["valid_records"])),
                ("Unique cases", int(validation["unique_cases"])),
                ("Unique activities", int(validation["unique_activities"])),
                (
                    "Duplicate events",
                    int(validation["duplicate_events"]),
                ),
            ]
        )

        for column in [case_column, activity_column, timestamp_column]:
            missing = int(df[column].isna().sum())
            quality_rows.append(
                {
                    "Event-log field": column,
                    "Missing values": missing,
                    "Missing (%)": (
                        missing / total_records * 100 if total_records else 0
                    ),
                }
            )

        parsed_timestamps = pd.to_datetime(
            df[timestamp_column],
            errors="coerce",
            utc=True,
        )
        invalid_timestamp_count = int(
            (df[timestamp_column].notna() & parsed_timestamps.isna()).sum()
        )
        quality_rows[2]["Invalid timestamps"] = invalid_timestamp_count
        valid_timestamp_values = parsed_timestamps.dropna()
        if not valid_timestamp_values.empty:
            summary_items.extend(
                [
                    ("First event timestamp (UTC)", str(valid_timestamp_values.min())),
                    ("Last event timestamp (UTC)", str(valid_timestamp_values.max())),
                ]
            )
    else:
        st.warning(
            "Select distinct case ID, activity and timestamp columns on the "
            "Upload Dataset page to include event-log metrics."
        )

    summary = pd.DataFrame(summary_items, columns=["Metric", "Value"])
    st.subheader("Dataset summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.download_button(
        "Download dataset summary",
        data=summary.to_csv(index=False).encode("utf-8"),
        file_name="careflow_dataset_summary.csv",
        mime="text/csv",
        key="download_dataset_summary",
    )

    st.subheader("Column quality")
    column_quality = pd.DataFrame(
        [
            {
                "Column": column,
                "Data type": str(df[column].dtype),
                "Non-null values": int(df[column].notna().sum()),
                "Missing values": int(df[column].isna().sum()),
                "Unique values": int(df[column].nunique()),
            }
            for column in df.columns
        ]
    )
    st.dataframe(column_quality, use_container_width=True, hide_index=True)
    st.download_button(
        "Download column quality report",
        data=column_quality.to_csv(index=False).encode("utf-8"),
        file_name="careflow_column_quality.csv",
        mime="text/csv",
        key="download_column_quality",
    )

    if quality_rows:
        st.subheader("Selected event-log field quality")
        st.dataframe(
            pd.DataFrame(quality_rows).round({"Missing (%)": 2}),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Dataset preview")
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)