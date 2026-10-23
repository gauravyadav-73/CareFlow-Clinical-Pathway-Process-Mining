from difflib import SequenceMatcher

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import COLORS, apply_chart_theme
from utils.process_mining import compare_traces


def render_pathway_comparison(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render a side-by-side comparison of two case pathways."""

    st.title("Pathway Comparison")
    st.write(
        "Compare event order, pathway length and elapsed time for two cases."
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
    data = data.dropna(
        subset=[case_column, activity_column, timestamp_column]
    )
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

    metric_cols = st.columns(4)
    metric_cols[0].metric(f"Case {case_a} events", f"{len(first_pathway):,}")
    metric_cols[1].metric(f"Case {case_b} events", f"{len(second_pathway):,}")
    metric_cols[2].metric("Sequence similarity", f"{similarity:.1f}%")
    metric_cols[3].metric(
        "Duration difference",
        f"{abs(first_duration - second_duration):.1f} h",
    )

    st.subheader("Pathway sequences")
    max_steps = max(len(first_pathway), len(second_pathway))
    step_numbers = list(range(1, max_steps + 1))
    first_steps = list(first_pathway) + [None] * (
        max_steps - len(first_pathway)
    )
    second_steps = list(second_pathway) + [None] * (
        max_steps - len(second_pathway)
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=step_numbers,
            y=["Case " + str(case_a)] * max_steps,
            mode="markers+text",
            text=first_steps,
            textposition="middle right",
            name=f"Case {case_a}",
            marker=dict(color=COLORS["teal"], size=13),
            hovertemplate="Step %{x}<br>%{text}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=step_numbers,
            y=["Case " + str(case_b)] * max_steps,
            mode="markers+text",
            text=second_steps,
            textposition="middle right",
            name=f"Case {case_b}",
            marker=dict(color=COLORS["purple"], size=13),
            hovertemplate="Step %{x}<br>%{text}<extra></extra>",
        )
    )
    fig = apply_chart_theme(fig, height=300)
    fig.update_layout(
        xaxis_title="Event sequence position",
        yaxis_title="",
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Position-by-position comparison")
    st.dataframe(
        compare_traces(first_pathway, second_pathway),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Sequence similarity uses the order of activity labels. Duration is "
        "the elapsed time between the first and last recorded events; it does "
        "not indicate active treatment time."
    )