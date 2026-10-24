import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import COLORS, apply_chart_theme
from utils.analytics import prepare_event_log
from utils.process_mining import discover_transitions


def render_process_discovery(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Discover common activity flows and pathway variants."""

    st.title("Process Discovery")
    st.write(
        "Explore the most common activity transitions and observed case "
        "pathways in the event log."
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
    else:
        selected_transitions = transitions.most_common(60)
        nodes = sorted(
            {
                node
                for (source, target), _ in selected_transitions
                for node in (source, target)
            },
            key=lambda node: (node[1], node[0]),
        )
        node_indices = {node: index for index, node in enumerate(nodes)}
        labels = [f"{activity} · step {step + 1}" for activity, step in nodes]
        sources = [
            node_indices[transition[0]]
            for transition, _ in selected_transitions
        ]
        targets = [
            node_indices[transition[1]]
            for transition, _ in selected_transitions
        ]
        values = [count for _, count in selected_transitions]

        st.subheader("Observed activity flow")
        fig = go.Figure(
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=16,
                    thickness=18,
                    line=dict(color=COLORS["grid"], width=0.5),
                    label=labels,
                    color=COLORS["teal"],
                    hovertemplate="%{label}<extra></extra>",
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color="rgba(15, 118, 110, 0.28)",
                    hovertemplate=(
                        "%{source.label} → %{target.label}<br>"
                        "Cases: %{value}<extra></extra>"
                    ),
                ),
            )
        )
        fig = apply_chart_theme(fig, height=560)
        fig.update_layout(title="Activity transitions by sequence position")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Link widths represent the number of cases with that transition. "
            "Only the 60 most frequent transitions are drawn."
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