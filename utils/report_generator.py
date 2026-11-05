from collections.abc import Sequence
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

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


def report_to_pdf_bytes(
    title: str,
    dataset_name: str,
    summary: pd.DataFrame,
    findings: Sequence[str],
) -> bytes:
    """Render a concise, printable PDF summary of the report."""

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=title,
        author="CareFlow",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CareFlowTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#102A43"),
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    section_style = ParagraphStyle(
        "CareFlowSection",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0F766E"),
        spaceBefore=14,
        spaceAfter=7,
    )
    body_style = ParagraphStyle(
        "CareFlowBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
    )

    def safe_text(value: object) -> str:
        return escape(str(value).encode("cp1252", "replace").decode("cp1252"))

    content = [
        Paragraph(safe_text(title), title_style),
        Paragraph(f"Dataset: {safe_text(dataset_name)}", body_style),
        Spacer(1, 12),
        Paragraph("Analysis Summary", section_style),
    ]

    table_data = [
        [
            Paragraph("<b>Metric</b>", body_style),
            Paragraph("<b>Value</b>", body_style),
        ]
    ]
    table_data.extend(
        [
            Paragraph(safe_text(row["Metric"]), body_style),
            Paragraph(safe_text(row["Value"]), body_style),
        ]
        for _, row in summary.iterrows()
    )
    summary_table = Table(
        table_data,
        colWidths=[2.5 * inch, 4.0 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6FFFB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102A43")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    content.append(summary_table)
    content.append(Paragraph("Key Findings", section_style))
    content.extend(
        Paragraph(f"&bull; {safe_text(finding)}", body_style)
        for finding in findings
    )

    document.build(content)
    return buffer.getvalue()