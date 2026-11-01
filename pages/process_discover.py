from collections import Counter
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import COLORS, apply_chart_theme
from utils.analytics import prepare_event_log
from utils.process_mining import discover_transitions


def _format_frequency(count: int, total_cases: int, mode: str) -> str:
    if mode == "Percent of cases":
        return f"{count / total_cases:.0%}"
    return f"{count:,}"


def _build_process_map(
    transitions: Counter,
    pathways: Counter,
    case_count: int,
    frequency_mode: str,
    layout: str,
    bottleneck_activity: str | None,
) -> go.Figure:
    """Build an interactive, position-based map of observed case transitions."""

    selected_transitions = transitions.most_common(60)
    node_cases: Counter = Counter()
    for pathway, count in pathways.items():
        for step, activity in enumerate(pathway):
            node_cases[(activity, step)] += count

    nodes = {
        node
        for (source, target), _ in selected_transitions
        for node in (source, target)
    }
    ordered_nodes = sorted(
        nodes,
        key=lambda node: (
            node[1],
            -node_cases[node] if layout == "Compact" else 0,
            node[0].casefold(),
        ),
    )
    nodes_by_step: dict[int, list[tuple[str, int]]] = {}
    for node in ordered_nodes:
        nodes_by_step.setdefault(node[1], []).append(node)

    positions = {}
    for step, layer_nodes in nodes_by_step.items():
        for index, node in enumerate(layer_nodes):
            offset = index - (len(layer_nodes) - 1) / 2
            point = (float(step), -offset)
            positions[node] = (
                (point[1], point[0])
                if layout == "Top to bottom"
                else point
            )

    visible_max = max(node_cases[node] for node in nodes)
    bottleneck_color = "#FB7185"
    node_colors = []
    node_labels = []
    node_hover = []
    for activity, step in ordered_nodes:
        count = node_cases[(activity, step)]
        if step == 0:
            color = COLORS["green"]
        elif activity == bottleneck_activity:
            color = bottleneck_color
        elif count >= visible_max * 0.35:
            color = COLORS["teal"]
        else:
            color = COLORS["blue"]
        node_colors.append(color)
        node_labels.append(
            f"{escape(activity)}<br>"
            f"{_format_frequency(count, case_count, frequency_mode)}"
        )
        node_hover.append(
            f"<b>{escape(activity)}</b><br>"
            f"Step: {step + 1}<br>"
            f"Cases: {count:,} ({count / case_count:.1%})"
        )

    max_transition_count = max(count for _, count in selected_transitions)
    alternative_threshold = max_transition_count * 0.35
    edge_groups: dict[str, dict[str, list]] = {
        "common": {"x": [], "y": [], "text": []},
        "alternative": {"x": [], "y": [], "text": []},
    }
    for (source, target), count in selected_transitions:
        group_name = (
            "alternative" if count < alternative_threshold else "common"
        )
        group = edge_groups[group_name]
        source_x, source_y = positions[source]
        target_x, target_y = positions[target]
        group["x"].extend([source_x, target_x, None])
        group["y"].extend([source_y, target_y, None])
        group["text"].extend(
            [
                f"{escape(source[0])} → {escape(target[0])}: "
                f"{count:,} cases ({count / case_count:.1%})",
                f"{escape(source[0])} → {escape(target[0])}: "
                f"{count:,} cases ({count / case_count:.1%})",
                None,
            ]
        )

    fig = go.Figure()
    for key, color, dash, name in (
        ("common", COLORS["teal"], "solid", "Frequent transition"),
        ("alternative", COLORS["blue"], "dash", "Alternative path"),
    ):
        group = edge_groups[key]
        if group["x"]:
            fig.add_trace(
                go.Scatter(
                    x=group["x"],
                    y=group["y"],
                    mode="lines",
                    line=dict(color=color, width=2, dash=dash),
                    text=group["text"],
                    hovertemplate="%{text}<extra></extra>",
                    name=name,
                    connectgaps=False,
                )
            )

    for color, name in (
        (COLORS["green"], "Start activity"),
        (COLORS["blue"], "Normal activity"),
        (COLORS["teal"], "High-frequency activity"),
        (bottleneck_color, "Bottleneck (longest median gap)"),
    ):
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(color=color, size=12),
                name=name,
                hoverinfo="skip",
            )
        )

    x_values = [positions[node][0] for node in ordered_nodes]
    y_values = [positions[node][1] for node in ordered_nodes]
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="markers+text",
            marker=dict(
                color=node_colors,
                size=30,
                line=dict(color="#DCE7F1", width=1),
            ),
            text=node_labels,
            textposition="middle center",
            textfont=dict(color="#FFFFFF", size=9),
            hovertext=node_hover,
            hovertemplate="%{hovertext}<extra></extra>",
            name="Activities",
            showlegend=False,
        )
    )

    fig = apply_chart_theme(fig, height=max(440, min(780, len(nodes) * 28)))
    fig.update_layout(
        title="Discovered clinical pathway",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(
            title="Sequence position" if layout != "Top to bottom" else "",
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        margin=dict(l=25, r=25, t=75, b=20),
    )
    return fig


def _build_activity_frequency_chart(
    pathways: Counter,
    case_count: int,
    frequency_mode: str,
) -> go.Figure:
    activity_cases: Counter = Counter()
    for pathway, count in pathways.items():
        activity_cases.update(
            {activity: count for activity in set(pathway)}
        )
    top_activities = activity_cases.most_common(20)
    labels = [activity for activity, _ in reversed(top_activities)]
    counts = [count for _, count in reversed(top_activities)]
    values = (
        [count / case_count * 100 for count in counts]
        if frequency_mode == "Percent of cases"
        else counts
    )
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=COLORS["teal"],
            customdata=counts,
            hovertemplate=(
                "%{y}<br>Cases: %{customdata:,}"
                f" ({'%{x:.1f}%' if frequency_mode == 'Percent of cases' else '%{x:,}'})"
                "<extra></extra>"
            ),
        )
    )
    fig = apply_chart_theme(fig, height=max(360, min(700, len(labels) * 32)))
    fig.update_layout(
        title="Most frequent clinical activities",
        xaxis_title=(
            "Cases (%)"
            if frequency_mode == "Percent of cases"
            else "Cases"
        ),
        yaxis_title="",
        showlegend=False,
    )
    return fig


def render_process_discovery(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Discover common activity flows and pathway variants."""

    st.markdown(
        '<div class="cf-page-kicker">Clinical pathway analytics</div>',
        unsafe_allow_html=True,
    )
    st.title("Process Discovery")
    st.write(
        "Visualize the discovered clinical pathway from your event log."
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

    data = prepare_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    if data.empty:
        st.info(
            "No complete events with valid timestamps were found for process "
            "discovery."
        )
        return

    max_available_steps = int(
        data.groupby(case_column, sort=False).size().max()
    )
    if max_available_steps < 2:
        st.info(
            "At least one case needs two valid events to discover activity "
            "transitions."
        )
        return

    controls = st.columns(3)
    with controls[0]:
        view_type = st.selectbox(
            "View type",
            ("Process Map", "Activity Frequency"),
            key="process_discovery_view_type",
        )
    with controls[1]:
        frequency_mode = st.selectbox(
            "Frequency",
            ("Case count", "Percent of cases"),
            key="process_discovery_frequency",
        )
    with controls[2]:
        layout = st.selectbox(
            "Layout",
            ("Hierarchical", "Compact", "Top to bottom"),
            key="process_discovery_layout",
        )

    if max_available_steps == 2:
        max_steps = 2
        st.caption("The longest case has two events; both are included.")
    else:
        max_steps = st.slider(
            "Maximum events per case to include",
            min_value=2,
            max_value=min(max_available_steps, 30),
            value=min(max_available_steps, 12),
            key="process_discovery_max_steps",
        )

    transitions, pathways = discover_transitions(
        df,
        case_column,
        activity_column,
        timestamp_column,
        max_steps,
    )
    case_count = int(data[case_column].nunique())
    activity_count = int(data[activity_column].nunique())
    metrics = st.columns(3)
    metrics[0].metric("Cases analysed", f"{case_count:,}")
    metrics[1].metric("Activities", f"{activity_count:,}")
    metrics[2].metric("Distinct pathways", f"{len(pathways):,}")

    if not transitions:
        st.info("At least one case needs two valid events to show transitions.")
        return

    if view_type == "Activity Frequency":
        fig = _build_activity_frequency_chart(
            pathways,
            case_count,
            frequency_mode,
        )
        st.plotly_chart(fig, width="stretch")
    else:
        step_gaps = data.copy()
        step_gaps["_next_timestamp"] = step_gaps.groupby(
            case_column,
            sort=False,
        )[timestamp_column].shift(-1)
        step_gaps["_gap_hours"] = (
            step_gaps["_next_timestamp"] - step_gaps[timestamp_column]
        ).dt.total_seconds() / 3600
        median_gaps = step_gaps.groupby(activity_column)["_gap_hours"].median()
        bottleneck_activity = (
            str(median_gaps.idxmax())
            if median_gaps.notna().any()
            else None
        )
        fig = _build_process_map(
            transitions,
            pathways,
            case_count,
            frequency_mode,
            layout,
            bottleneck_activity,
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Node values show case frequency. Red marks the activity with the "
            "longest median wait to the next event; dashed links show less "
            "frequent observed transitions. Only the 60 most frequent "
            "transitions are drawn."
        )

    pathway_rows = [
        {
            "Pathway": " → ".join(pathway),
            "Events included": len(pathway),
            "Cases": count,
            "Share (%)": count / case_count * 100,
        }
        for pathway, count in pathways.most_common(20)
    ]
    st.subheader("Most frequent observed pathways")
    st.dataframe(
        pd.DataFrame(pathway_rows).round({"Share (%)": 1}),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Events are ordered by timestamp; equal timestamps retain their "
        "original row order. This is an observed process summary, not a "
        "prescribed clinical pathway."
    )
