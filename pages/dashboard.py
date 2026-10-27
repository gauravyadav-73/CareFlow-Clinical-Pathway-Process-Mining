from collections import Counter
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import COLORS, apply_chart_theme
from utils.analytics import calculate_event_gaps, prepare_event_log, summarize_activity_gaps
from utils.process_mining import build_case_traces


def _format_cycle_time(days: float | None) -> str:
    if days is None or pd.isna(days):
        return "—"
    return f"{days:.1f} days"


def _build_process_map(
    traces: list[tuple[object, tuple[str, ...]]],
    max_steps: int = 6,
    max_variants: int = 10,
) -> go.Figure | None:
    """Build a compact flow map from the most common observed case traces."""

    variant_counts = Counter(trace for _, trace in traces if trace)
    if not variant_counts:
        return None

    node_cases: Counter = Counter()
    edge_cases: Counter = Counter()

    start_node = (-1, "Start")
    end_node = (max_steps + 1, "End")
    node_cases[start_node] = sum(
        count for _, count in variant_counts.most_common(max_variants)
    )

    for trace, count in variant_counts.most_common(max_variants):
        visible_trace = list(trace[:max_steps])
        if len(trace) > max_steps:
            visible_trace.append("More activities")

        path_nodes = []
        for level, activity in enumerate(visible_trace):
            key = (level, str(activity))
            node_cases[key] += count
            path_nodes.append(key)

        edge_cases[(start_node, path_nodes[0])] += count
        for source, target in zip(path_nodes, path_nodes[1:]):
            edge_cases[(source, target)] += count
        if len(trace) <= max_steps:
            node_cases[end_node] += count
            edge_cases[(path_nodes[-1], end_node)] += count

    ordered_nodes = [start_node]
    ordered_nodes.extend(
        sorted(
            node_cases.keys() - {start_node, end_node},
            key=lambda node: (node[0], node[1]),
        )
    )
    if end_node in node_cases:
        ordered_nodes.append(end_node)
    node_indices = {node: index for index, node in enumerate(ordered_nodes)}

    labels = []
    node_colors = []
    for node in ordered_nodes:
        level, activity = node
        if activity == "Start":
            labels.append(f"Start<br>{node_cases[node]:,} cases")
            node_colors.append("#BBF7D0")
        elif activity == "End":
            labels.append(f"End<br>{node_cases[node]:,} cases")
            node_colors.append("#FECDD3")
        else:
            labels.append(f"{escape(activity)}<br>{node_cases[node]:,} cases")
            node_colors.append(
                COLORS["teal"] if node_cases[node] >= max(node_cases.values()) * 0.35
                else COLORS["blue"]
            )

    sources = [node_indices[source] for source, _ in edge_cases]
    targets = [node_indices[target] for _, target in edge_cases]
    values = list(edge_cases.values())
    link_colors = [
        "rgba(15, 118, 110, 0.26)" if value >= max(values) * 0.35
        else "rgba(59, 130, 246, 0.18)"
        for value in values
    ]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=18,
                thickness=17,
                line=dict(color="#D7E3ED", width=0.7),
                label=labels,
                color=node_colors,
                hovertemplate="%{label}<extra></extra>",
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
                hovertemplate=(
                    "%{source.label} → %{target.label}<br>"
                    "Cases: %{value:,}<extra></extra>"
                ),
            ),
        )
    )
    fig = apply_chart_theme(fig, height=340)
    fig.update_layout(
        margin=dict(l=12, r=12, t=14, b=12),
        font=dict(size=11),
    )
    return fig


def _render_metric(label: str, value: str, note: str, icon: str, accent: str) -> None:
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


def render_dashboard(
    df: pd.DataFrame | None,
    filename: str | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render the CareFlow overview and observed patient-pathway summary."""

    dataset_available = df is not None and not df.empty
    valid_roles = (
        dataset_available
        and case_column in df.columns
        and activity_column in df.columns
        and timestamp_column in df.columns
        and len({case_column, activity_column, timestamp_column}) == 3
    )

    prepared = None
    traces: list[tuple[object, tuple[str, ...]]] = []
    date_range = "Upload a dataset to see its event date range"
    total_cases = activity_count = variant_count = bottleneck_count = None
    cycle_time = None
    bottleneck_note = "Map case, activity and timestamp columns"
    process_map = None

    if valid_roles:
        prepared = prepare_event_log(
            df,
            case_column,
            activity_column,
            timestamp_column,
        )
        traces = build_case_traces(
            df,
            case_column,
            activity_column,
            timestamp_column,
        )
        total_cases = int(prepared[case_column].nunique())
        activity_count = int(prepared[activity_column].nunique())
        variant_counts = Counter(trace for _, trace in traces if trace)
        variant_count = len(variant_counts)
        process_map = _build_process_map(traces)

        if not prepared.empty:
            first_timestamp = prepared[timestamp_column].min()
            last_timestamp = prepared[timestamp_column].max()
            date_range = (
                f"{first_timestamp.strftime('%b %d, %Y')} – "
                f"{last_timestamp.strftime('%b %d, %Y')}"
            )

            case_durations = (
                prepared.groupby(case_column, sort=False)[timestamp_column]
                .agg(lambda values: values.max() - values.min())
                .dt.total_seconds()
                .div(86_400)
            )
            if not case_durations.empty:
                cycle_time = float(case_durations.mean())

            gaps = calculate_event_gaps(
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
            if not gaps.empty and not gap_summary.empty:
                median_activity_gap = float(
                    gap_summary["Average gap (hours)"].median()
                )
                bottleneck_count = int(
                    (gap_summary["Average gap (hours)"] > median_activity_gap).sum()
                )
                bottleneck_note = (
                    f"Activities above median wait · "
                    f"{median_activity_gap:.1f} h median"
                )
            else:
                bottleneck_count = 0
                bottleneck_note = "No consecutive event times to compare"

    st.markdown(
        """
        <div class="cf-overview-header">
            <div>
                <div class="cf-page-kicker">Clinical pathway intelligence</div>
                <h1 class="cf-overview-title">Clinical Operations Overview</h1>
                <p class="cf-overview-subtitle">
                    Discover how patients move through clinical pathways and
                    identify opportunities to improve care flow.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    status_text = (
        f"Dataset loaded · {escape(filename)}"
        if dataset_available and filename
        else "Dataset loaded"
        if dataset_available
        else "No dataset loaded"
    )
    status_class = "cf-overview-status-ready" if dataset_available else "cf-overview-status-empty"
    st.markdown(
        f"""
        <div class="cf-overview-toolbar">
            <span class="cf-overview-status {status_class}">
                <span class="cf-overview-status-dot"></span>{status_text}
            </span>
            <span class="cf-overview-date">{escape(date_range)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not dataset_available:
        st.info(
            "Upload a clinical event log and map its case ID, activity and "
            "timestamp columns to populate the overview."
        )
    elif not valid_roles:
        st.info(
            "Choose distinct case ID, activity and timestamp columns on the "
            "Upload Dataset page to calculate pathway metrics."
        )

    first_row = st.columns(3, gap="small")
    metric_specs = (
        (
            "Total cases",
            f"{total_cases:,}" if total_cases is not None else "—",
            "Unique patient journeys",
            "👥",
            "blue",
        ),
        (
            "Activities",
            f"{activity_count:,}" if activity_count is not None else "—",
            "Unique clinical activities",
            "▦",
            "purple",
        ),
        (
            "Pathway variants",
            f"{variant_count:,}" if variant_count is not None else "—",
            "Distinct observed sequences",
            "⌘",
            "teal",
        ),
    )
    for column, metric in zip(first_row, metric_specs):
        with column:
            _render_metric(*metric)

    second_row = st.columns(2, gap="small")
    second_metrics = (
        (
            "Average cycle time",
            _format_cycle_time(cycle_time),
            "Mean first-to-last event duration",
            "◷",
            "orange",
        ),
        (
            "Bottleneck activities",
            f"{bottleneck_count:,}" if bottleneck_count is not None else "—",
            bottleneck_note,
            "⚠",
            "red",
        ),
    )
    for column, metric in zip(second_row, second_metrics):
        with column:
            _render_metric(*metric)

    st.markdown(
        """
        <div class="cf-process-map-heading">
            <div>
                <h2>Process Map (Overview)</h2>
                <p>Observed patient flow · links show cases following each transition</p>
            </div>
            <span class="cf-process-map-chip">Most frequent pathways</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if not valid_roles:
            st.caption(
                "The process map will appear here after you upload an event log "
                "and map its required columns."
            )
        elif process_map is None:
            st.info("No complete case pathways with valid timestamps were found.")
        else:
            st.plotly_chart(
                process_map,
                width="stretch",
                config={"displayModeBar": False},
            )
            st.caption(
                "Showing up to 10 most frequent observed pathway variants. "
                "Longer traces are grouped after the first six activities."
            )

        st.markdown(
            """
            <div class="cf-process-map-legend">
                <span><i class="cf-legend-dot cf-legend-start"></i>Start / end</span>
                <span><i class="cf-legend-dot cf-legend-common"></i>Frequent flow</span>
                <span><i class="cf-legend-dot cf-legend-alternative"></i>Alternative path</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
