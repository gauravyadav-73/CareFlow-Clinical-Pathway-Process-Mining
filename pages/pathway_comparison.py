from difflib import SequenceMatcher
from html import escape

import pandas as pd
import streamlit as st

from utils.process_mining import compare_traces


def _render_metric(label: str, value: str, note: str, accent: str) -> None:
    st.markdown(
        f"""
        <article class="cf-overview-metric cf-accent-{accent}">
            <div class="cf-overview-label">{escape(label)}</div>
            <div class="cf-overview-value">{escape(value)}</div>
            <div class="cf-overview-note">{escape(note)}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_pathway_card(
    case_id: object,
    pathway: tuple[str, ...],
    duration_hours: float,
    first_timestamp: pd.Timestamp,
    last_timestamp: pd.Timestamp,
) -> None:
    steps = "".join(
        f"""
        <div class="cf-pathway-step">
            <span class="cf-pathway-step-number">{index:02d}</span>
            <span class="cf-pathway-step-name">{escape(activity)}</span>
        </div>
        """
        for index, activity in enumerate(pathway, start=1)
    )
    case_label = escape(str(case_id))
    st.markdown(
        f"""
        <article class="cf-pathway-card">
            <header class="cf-pathway-card-header">
                <div>
                    <span class="cf-pathway-case-label">Patient case</span>
                    <h3>Case {case_label}</h3>
                </div>
                <span class="cf-pathway-duration">{duration_hours:.1f} h</span>
            </header>
            <div class="cf-pathway-steps">{steps}</div>
            <footer class="cf-pathway-card-footer">
                <span>{len(pathway):,} recorded events</span>
                <span>{first_timestamp.strftime("%b %d, %Y %H:%M")} – {
                    last_timestamp.strftime("%b %d, %Y %H:%M")
                } UTC</span>
            </footer>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_pathway_comparison(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render a side-by-side comparison of two case pathways."""

    st.markdown(
        """
        <div class="cf-overview-header">
            <div class="cf-page-kicker">Clinical pathway intelligence</div>
            <h1 class="cf-overview-title">Pathway Comparison</h1>
            <p class="cf-overview-subtitle">
                Compare patient journeys, activity order and elapsed time
                side by side.
            </p>
        </div>
        <style>
            .cf-pathway-card {
                height: 100%;
                overflow: hidden;
                border: 1px solid var(--cf-border);
                border-radius: 14px;
                background: var(--cf-surface);
                margin-bottom: 12px;
            }
            .cf-pathway-card-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                border-bottom: 1px solid var(--cf-border);
                padding: 14px 16px;
            }
            .cf-pathway-case-label {
                color: var(--cf-muted);
                font-size: 10px;
                font-weight: 700;
                letter-spacing: .08em;
                text-transform: uppercase;
            }
            .cf-pathway-card-header h3 {
                margin: 2px 0 0;
                font-size: 16px;
            }
            .cf-pathway-duration {
                flex: 0 0 auto;
                border: 1px solid rgba(45, 212, 191, .3);
                border-radius: 8px;
                background: rgba(45, 212, 191, .1);
                color: var(--cf-primary);
                font-size: 12px;
                font-weight: 700;
                padding: 6px 9px;
            }
            .cf-pathway-steps {
                display: flex;
                flex-wrap: wrap;
                align-items: stretch;
                gap: 8px;
                padding: 16px;
            }
            .cf-pathway-step {
                display: flex;
                min-width: 130px;
                max-width: 100%;
                flex: 1 1 130px;
                align-items: center;
                gap: 8px;
                border: 1px solid var(--cf-border);
                border-radius: 9px;
                background: rgba(15, 23, 42, .24);
                padding: 9px 10px;
            }
            .cf-pathway-step-number {
                display: inline-flex;
                width: 23px;
                height: 23px;
                flex: 0 0 23px;
                align-items: center;
                justify-content: center;
                border-radius: 7px;
                background: rgba(59, 130, 246, .16);
                color: #93C5FD;
                font-size: 10px;
                font-weight: 800;
            }
            .cf-pathway-step-name {
                color: var(--cf-text);
                font-size: 11px;
                font-weight: 600;
                overflow-wrap: anywhere;
            }
            .cf-pathway-card-footer {
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                gap: 6px 12px;
                border-top: 1px solid var(--cf-border);
                color: var(--cf-muted);
                font-size: 10px;
                padding: 10px 16px;
            }
            @media (max-width: 700px) {
                .cf-pathway-card-footer {
                    display: grid;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if df is None or df.empty:
        st.info("Upload an event log on the Upload Dataset page to begin.")
        return

    selected_columns = [case_column, activity_column, timestamp_column]
    if (
        any(column is None or column not in df.columns for column in selected_columns)
        or len(set(selected_columns)) != 3
    ):
        st.info(
            "Select distinct case ID, activity and timestamp columns on the "
            "Upload Dataset page, then return here."
        )
        return

    data = df[[case_column, activity_column, timestamp_column]].copy()
    data[timestamp_column] = pd.to_datetime(
        data[timestamp_column],
        errors="coerce",
        utc=True,
    )
    data = data.dropna(subset=[case_column, activity_column, timestamp_column])
    if data.empty:
        st.info(
            "No events with valid case IDs, activities and timestamps are "
            "available for comparison."
        )
        return

    data[activity_column] = data[activity_column].astype(str)
    data = data.sort_values([case_column, timestamp_column], kind="mergesort")
    case_ids = data[case_column].drop_duplicates().tolist()
    if len(case_ids) < 2:
        st.info("At least two cases with valid events are needed to compare.")
        return

    st.markdown(
        """
        <div class="cf-process-map-heading">
            <div>
                <h2>Select cases to compare</h2>
                <p>Choose two patient journeys from the uploaded event log.</p>
            </div>
            <span class="cf-process-map-chip">Case-to-case analysis</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        case_col_a, case_col_b = st.columns(2)
        with case_col_a:
            case_a = st.selectbox(
                "First case",
                case_ids,
                index=0,
                format_func=str,
                key="pathway_comparison_case_a",
            )
        with case_col_b:
            case_b = st.selectbox(
                "Second case",
                case_ids,
                index=1,
                format_func=str,
                key="pathway_comparison_case_b",
            )

    if case_a == case_b:
        st.warning("Choose two different cases to compare their pathways.")
        return

    first = data[data[case_column] == case_a]
    second = data[data[case_column] == case_b]
    first_pathway = tuple(first[activity_column].tolist())
    second_pathway = tuple(second[activity_column].tolist())
    first_duration = (
        first[timestamp_column].iloc[-1] - first[timestamp_column].iloc[0]
    ).total_seconds() / 3600
    second_duration = (
        second[timestamp_column].iloc[-1] - second[timestamp_column].iloc[0]
    ).total_seconds() / 3600
    similarity = SequenceMatcher(
        a=first_pathway,
        b=second_pathway,
        autojunk=False,
    ).ratio() * 100
    comparison = compare_traces(first_pathway, second_pathway)
    matching_steps = int((comparison["Match"] == "Yes").sum())
    total_steps = max(len(first_pathway), len(second_pathway))

    metric_columns = st.columns(4, gap="small")
    metric_specs = (
        (
            "Sequence similarity",
            f"{similarity:.1f}%",
            "Activity order similarity",
            "teal",
        ),
        (
            "Matching positions",
            f"{matching_steps:,} / {total_steps:,}",
            "Same activity at the same step",
            "blue",
        ),
        (
            "Duration difference",
            f"{abs(first_duration - second_duration):.1f} h",
            "Difference in elapsed case time",
            "orange",
        ),
        (
            "Total events",
            f"{len(first_pathway) + len(second_pathway):,}",
            "Across both selected cases",
            "purple",
        ),
    )
    for column, metric in zip(metric_columns, metric_specs):
        with column:
            _render_metric(*metric)

    st.markdown(
        """
        <div class="cf-process-map-heading">
            <div>
                <h2>Observed pathway sequences</h2>
                <p>Activities are shown in timestamp order for each case.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pathway_columns = st.columns(2, gap="small")
    with pathway_columns[0]:
        _render_pathway_card(
            case_a,
            first_pathway,
            first_duration,
            first[timestamp_column].iloc[0],
            first[timestamp_column].iloc[-1],
        )
    with pathway_columns[1]:
        _render_pathway_card(
            case_b,
            second_pathway,
            second_duration,
            second[timestamp_column].iloc[0],
            second[timestamp_column].iloc[-1],
        )

    st.markdown(
        """
        <div class="cf-process-map-heading">
            <div>
                <h2>Position-by-position comparison</h2>
                <p>Review matching activities and differences at each step.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(comparison, width="stretch", hide_index=True)
    st.caption(
        "Sequence similarity compares the order of activity labels. Duration "
        "is the elapsed time between the first and last recorded events; it "
        "does not indicate active treatment time."
    )
