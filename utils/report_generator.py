from collections.abc import Sequence
from typing import Any

import pandas as pd

from utils.analytics import describe_event_log
from utils.data_loader import validate_event_log


def build_dataset_report(
    df: pd.DataFrame,
    filename: str | None = None,
    case_column: str | None = None,
    activity_column: str | None = None,
    timestamp_column: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Build summary, column-quality and event-role-quality report tables."""

    if df.empty:
        raise ValueError("Cannot build a report for an empty dataset.")

    summary_rows: list[dict[str, Any]] = [
        {"Metric": "Dataset filename", "Value": filename or "Uploaded CSV"},
        {"Metric": "Total records", "Value": len(df)},
        {"Metric": "Total columns", "Value": len(df.columns)},
        {"Metric": "Missing cells", "Value": int(df.isna().sum().sum())},
        {"Metric": "Duplicate rows", "Value": int(df.duplicated().sum())},
    ]
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
        ],
        columns=[
            "Column",
            "Data type",
            "Non-null values",
            "Missing values",
            "Unique values",
        ],
    )
    event_quality = pd.DataFrame(
        columns=["Event-log field", "Missing values", "Missing (%)"]
    )

    selected_columns: Sequence[str | None] = (
        case_column,
        activity_column,
        timestamp_column,
    )
    if all(column in df.columns for column in selected_columns) and len(
        set(selected_columns)
    ) == 3:
        validation = validate_event_log(
            df,
            case_column,
            activity_column,
            timestamp_column,
        )
        metrics = describe_event_log(
            df,
            case_column,
            activity_column,
            timestamp_column,
        )
        summary_rows.extend(
            [
                {
                    "Metric": "Valid event records",
                    "Value": validation["valid_records"],
                },
                {"Metric": "Unique cases", "Value": metrics["cases"]},
                {
                    "Metric": "Unique activities",
                    "Value": metrics["activities"],
                },
                {
                    "Metric": "Duplicate events",
                    "Value": validation["duplicate_events"],
                },
                {
                    "Metric": "Consecutive-event transitions",
                    "Value": metrics["transitions"],
                },
            ]
        )
        for column in (case_column, activity_column, timestamp_column):
            missing_count = int(df[column].isna().sum())
            event_quality.loc[len(event_quality)] = {
                "Event-log field": column,
                "Missing values": missing_count,
                "Missing (%)": missing_count / len(df) * 100,
            }

        parsed_timestamps = pd.to_datetime(
            df[timestamp_column],
            errors="coerce",
            utc=True,
        )
        invalid_timestamp_count = int(
            (df[timestamp_column].notna() & parsed_timestamps.isna()).sum()
        )
        event_quality.loc[
            event_quality["Event-log field"] == timestamp_column,
            "Invalid timestamps",
        ] = invalid_timestamp_count

        if metrics["first_timestamp"] is not None:
            summary_rows.extend(
                [
                    {
                        "Metric": "First event timestamp (UTC)",
                        "Value": str(metrics["first_timestamp"]),
                    },
                    {
                        "Metric": "Last event timestamp (UTC)",
                        "Value": str(metrics["last_timestamp"]),
                    },
                ]
            )

    summary = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    summary["Value"] = summary["Value"].astype(str)

    return {
        "summary": summary,
        "column_quality": column_quality,
        "event_quality": event_quality,
    }


def dataframe_to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    """Serialize a report table as UTF-8 CSV bytes for download."""

    return dataframe.to_csv(index=False).encode("utf-8")


def combine_report_tables(
    report_tables: dict[str, pd.DataFrame],
) -> bytes:
    """Serialize multiple named tables into one CSV with section headers."""

    if not report_tables:
        raise ValueError("At least one report table is required.")

    sections = []
    for title, table in report_tables.items():
        sections.append(f"# {title}")
        sections.append(table.to_csv(index=False))
    return "\n".join(sections).encode("utf-8")