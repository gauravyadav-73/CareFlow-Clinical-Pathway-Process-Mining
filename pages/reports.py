from collections import Counter
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pages.dashboard import _build_process_map
from utils.analytics import describe_event_log, summarize_activity_gaps
from utils.insights import generate_event_log_insights
from utils.process_mining import build_case_traces
from utils.report_generator import (
    build_dataset_report,
    combine_report_tables,
    dataframe_to_csv_bytes,
    report_to_pdf_bytes,
)


def _render_metric(
    label: str,
    value: str,
    note: str,
    icon: str,
    accent: str,
) -> None:
    st.markdown(
        f"""
        <article class="cf-overview-metric cf-accent-{accent}">
            <div class="cf-overview-icon">{icon}</div>
            <div class="cf-overview-label">{escape(label)}</div>
            <div class="cf-overview-value">{escape(value)}</div>
            <div class="cf-overview-note">{escape(note)}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _report_findings(
    df: pd.DataFrame,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
    valid_mapping: bool,
) -> list[str]:
    if (
        not valid_mapping
        or case_column is None
        or activity_column is None
        or timestamp_column is None
    ):
        missing_cells = int(df.isna().sum().sum())
        duplicate_rows = int(df.duplicated().sum())
        return [
            f"The dataset contains {len(df):,} records across {len(df.columns):,} columns.",
            f"{missing_cells:,} cells are missing and {duplicate_rows:,} rows are duplicates.",
            "Map case ID, activity and timestamp columns to include pathway findings.",
        ]

    findings = generate_event_log_insights(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    gap_summary = summarize_activity_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    if not gap_summary.empty:
        bottleneck = gap_summary.iloc[0]
        findings.append(
            f"The longest average wait follows '{bottleneck['Preceding activity']}' "
            f"({bottleneck['Average gap (hours)']:.2f} hours across "
            f"{int(bottleneck['Transitions']):,} transitions)."
        )
    else:
        findings.append("There are not enough consecutive valid events to summarize waits.")
    return findings


def _build_metrics(
    df: pd.DataFrame,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
    valid_mapping: bool,
) -> tuple[list[tuple[str, str, str, str, str]], pd.DataFrame, go.Figure | None]:
    if (
        not valid_mapping
        or case_column is None
        or activity_column is None
        or timestamp_column is None
    ):
        return (
            [
                (
                    "Total cases",
                    "—",
                    "Map event-log fields to calculate",
                    "👥",
                    "blue",
                ),
                (
                    "Activities",
                    "—",
                    "Map event-log fields to calculate",
                    "▦",
                    "purple",
                ),
                (
                    "Process variants",
                    "—",
                    "Map event-log fields to calculate",
                    "⌘",
                    "teal",
                ),
                (
                    "Bottleneck activities",
                    "—",
                    "Map event-log fields to calculate",
                    "⚠",
                    "red",
                ),
            ],
            pd.DataFrame(),
            None,
        )

    metrics = describe_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    pathways = build_case_traces(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    variants = Counter(trace for _, trace in pathways if trace)
    gap_summary = summarize_activity_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    bottleneck_count = (
        int(
            (
                gap_summary["Average gap (hours)"]
                > gap_summary["Average gap (hours)"].median()
            ).sum()
        )
        if not gap_summary.empty
        else 0
    )
    bottleneck_note = (
        "Above median wait · "
        f"{gap_summary['Average gap (hours)'].median():.1f} h median"
        if not gap_summary.empty
        else "No consecutive event times to compare"
    )
    metric_cards = [
        (
            "Total cases",
            f"{metrics['cases']:,}",
            "Unique patient journeys",
            "👥",
            "blue",
        ),
        (
            "Activities",
            f"{metrics['activities']:,}",
            "Unique clinical activities",
            "▦",
            "purple",
        ),
        (
            "Process variants",
            f"{len(variants):,}",
            "Distinct observed sequences",
            "⌘",
            "teal",
        ),
        (
            "Bottleneck activities",
            f"{bottleneck_count:,}",
            bottleneck_note,
            "⚠",
            "red",
        ),
    ]
    process_map = _build_process_map(pathways)
    return metric_cards, gap_summary, process_map


def _render_exports(
    pdf_data: bytes,
    csv_data: bytes,
    process_map_html: str | None,
    suffix: str,
) -> None:
    st.download_button(
        "Download PDF Report",
        data=pdf_data,
        file_name="careflow_report.pdf",
        mime="application/pdf",
        key=f"download_report_pdf_{suffix}",
        width="stretch",
        type="primary",
    )
    st.download_button(
        "Download CSV Results",
        data=csv_data,
        file_name="careflow_report.csv",
        mime="text/csv",
        key=f"download_report_csv_{suffix}",
        width="stretch",
    )
    if process_map_html is not None:
        st.download_button(
            "Download Process Map",
            data=process_map_html,
            file_name="careflow_process_map.html",
            mime="text/html",
            key=f"download_process_map_{suffix}",
            width="stretch",
        )
    else:
        st.button(
            "Process map unavailable",
            key=f"process_map_unavailable_{suffix}",
            width="stretch",
            disabled=True,
        )


def render_reports(
    df: pd.DataFrame | None,
    filename: str | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Display and export an event-log analysis and data-quality report."""

    st.markdown(
        """
        <div class="cf-overview-header">
            <div class="cf-page-kicker">Clinical pathway intelligence</div>
            <h1 class="cf-overview-title">Reports &amp; Export</h1>
            <p class="cf-overview-subtitle">
                Generate comprehensive reports from your process mining analysis.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df is None or df.empty:
        st.info("Upload a dataset to generate reports.")
        return

    valid_mapping = (
        case_column in df.columns
        and activity_column in df.columns
        and timestamp_column in df.columns
        and len({case_column, activity_column, timestamp_column}) == 3
    )
    if not valid_mapping:
        st.warning(
            "Select distinct case ID, activity and timestamp columns on the "
            "Upload Dataset page to include event-log metrics."
        )

    report = build_dataset_report(
        df,
        filename,
        case_column if valid_mapping else None,
        activity_column if valid_mapping else None,
        timestamp_column if valid_mapping else None,
    )
    metric_cards, gap_summary, process_map = _build_metrics(
        df,
        case_column,
        activity_column,
        timestamp_column,
        valid_mapping,
    )
    dataset_name = filename or "Uploaded CSV"
    findings = _report_findings(
        df,
        case_column,
        activity_column,
        timestamp_column,
        valid_mapping,
    )
    pdf_data = report_to_pdf_bytes(
        "CareFlow Clinical Pathway Report",
        dataset_name,
        report["summary"],
        findings,
    )
    csv_data = combine_report_tables(report)
    process_map_html = (
        process_map.to_html(full_html=True, include_plotlyjs=True)
        if process_map is not None
        else None
    )

    summary_tab, detail_tab, process_tab, export_tab = st.tabs(
        ["Executive Summary", "Detailed Analysis", "Process Maps", "Data Export"]
    )

    with summary_tab:
        st.markdown(
            '<h2 class="cf-section-title">Analysis Summary</h2>',
            unsafe_allow_html=True,
        )
        metric_columns = st.columns(4, gap="small")
        for column, metric in zip(metric_columns, metric_cards):
            with column:
                _render_metric(*metric)

        findings_column, exports_column = st.columns([1.55, 1], gap="medium")
        with findings_column:
            with st.container(border=True):
                st.markdown(
                    '<h3 class="cf-card-title">Key Findings</h3>',
                    unsafe_allow_html=True,
                )
                for finding in findings:
                    st.markdown(f"- {finding}")
        with exports_column:
            with st.container(border=True):
                st.markdown(
                    '<h3 class="cf-card-title">Export Report</h3>',
                    unsafe_allow_html=True,
                )
                _render_exports(pdf_data, csv_data, process_map_html, "summary")

    with detail_tab:
        st.subheader("Dataset summary")
        st.dataframe(report["summary"], width="stretch", hide_index=True)
        st.download_button(
            "Download dataset summary",
            data=dataframe_to_csv_bytes(report["summary"]),
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
            if not gap_summary.empty:
                st.subheader("Activity wait-time summary")
                st.dataframe(gap_summary, width="stretch", hide_index=True)

        st.subheader("Dataset preview")
        st.dataframe(df.head(20), width="stretch", hide_index=True)

    with process_tab:
        st.subheader("Observed Process Map")
        if process_map is None:
            st.info(
                "A process map will appear after you upload an event log and "
                "map its case ID, activity and timestamp columns."
            )
        else:
            st.plotly_chart(
                process_map,
                width="stretch",
                config={"displayModeBar": False},
            )
            st.caption(
                "Showing up to 10 of the most frequent observed pathway variants. "
                "Longer traces are grouped after the first six activities."
            )

    with export_tab:
        st.subheader("Download report files")
        st.write(
            "Export the analysis summary, data-quality tables, original dataset, "
            "or observed process map."
        )
        export_columns = st.columns([1, 1])
        with export_columns[0]:
            _render_exports(pdf_data, csv_data, process_map_html, "data")
        with export_columns[1]:
            st.download_button(
                "Download original dataset (CSV)",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="careflow_dataset.csv",
                mime="text/csv",
                key="download_original_dataset",
                width="stretch",
            )
