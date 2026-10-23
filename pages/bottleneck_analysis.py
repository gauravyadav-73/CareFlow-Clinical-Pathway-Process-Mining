import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import COLORS, apply_chart_theme
from utils.analytics import calculate_event_gaps, summarize_activity_gaps
from utils.insights import generate_gap_insights


def _event_gaps(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> pd.DataFrame:
    """Return elapsed time from each event to the next event in its case."""
    return calculate_event_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )


def render_bottleneck_analysis(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render an event-gap analysis using the selected event-log columns."""

    st.title("Bottleneck Analysis")
    st.write(
        "Find activities followed by the longest gaps before the next "
        "recorded event in the same case."
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

    gaps = _event_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    if gaps.empty:
        st.info(
            "No consecutive valid events were found. Check that cases have "
            "at least two activities with valid timestamps."
        )
        return

    summary = summarize_activity_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )

    metric_options = {
        "90th percentile gap": "90th percentile gap (hours)",
        "Median gap": "Median gap (hours)",
        "Average gap": "Average gap (hours)",
    }
    selected_metric = st.selectbox(
        "Rank activities by",
        options=list(metric_options),
        key="bottleneck_rank_metric",
    )
    ranking_column = metric_options[selected_metric]
    summary = summary.sort_values(
        ranking_column,
        ascending=False,
        kind="mergesort",
    )

    case_count = int(gaps[case_column].nunique())
    overall_median = float(gaps["Elapsed Hours"].median())
    overall_p90 = float(gaps["Elapsed Hours"].quantile(0.9))
    leading_activity = str(summary.iloc[0]["Preceding activity"])
    leading_gap = float(summary.iloc[0][ranking_column])

    metric_columns = st.columns(4)
    metric_columns[0].metric("Cases analysed", f"{case_count:,}")
    metric_columns[1].metric("Event transitions", f"{len(gaps):,}")
    metric_columns[2].metric("Overall median gap", f"{overall_median:.1f} h")
    metric_columns[3].metric("Overall 90th percentile", f"{overall_p90:.1f} h")

    st.subheader("Activities with the longest event gaps")
    chart_data = summary.head(10).sort_values(
        ranking_column,
        ascending=True,
        kind="mergesort",
    )
    fig = px.bar(
        chart_data,
        x=ranking_column,
        y="Preceding activity",
        orientation="h",
        text=ranking_column,
        labels={
            ranking_column: selected_metric.title() + " (hours)",
            "Preceding activity": "Preceding activity",
        },
    )
    fig.update_traces(
        marker_color=COLORS["orange"],
        texttemplate="%{x:.1f}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b><br>"
            + selected_metric.title()
            + ": %{x:.2f} hours<extra></extra>"
        ),
    )
    fig = apply_chart_theme(fig, height=max(320, len(chart_data) * 38))
    fig.update_layout(
        showlegend=False,
        xaxis_title=f"{selected_metric.title()} (hours)",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Highest-ranked activity: {leading_activity} "
        f"({leading_gap:.1f} hours by {selected_metric.lower()})."
    )

    st.subheader("Activity gap summary")
    st.dataframe(
        summary.round(
            {
                "Average gap (hours)": 2,
                "Median gap (hours)": 2,
                "90th percentile gap (hours)": 2,
                "Total gap (hours)": 2,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Observed data insights"):
        for insight in generate_gap_insights(summary):
            st.write(f"- {insight}")
    st.download_button(
        "Download bottleneck summary",
        data=summary.to_csv(index=False).encode("utf-8"),
        file_name="careflow_bottleneck_summary.csv",
        mime="text/csv",
        key="download_bottleneck_summary",
    )
    st.caption(
        "These are elapsed times between consecutive recorded events, "
        "attributed to the preceding activity. They are not necessarily "
        "queue times, treatment durations or confirmed clinical bottlenecks."
    )