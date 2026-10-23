import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import COLORS, apply_chart_theme


def _event_gaps(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> pd.DataFrame:
    """Return elapsed time from each event to the next event in its case."""

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
        return pd.DataFrame()

    data[activity_column] = data[activity_column].astype(str)
    data = data.sort_values(
        [case_column, timestamp_column],
        kind="mergesort",
    )
    grouped = data.groupby(case_column, sort=False)
    data["Next Activity"] = grouped[activity_column].shift(-1)
    data["Next Timestamp"] = grouped[timestamp_column].shift(-1)
    data["Elapsed Hours"] = (
        data["Next Timestamp"] - data[timestamp_column]
    ).dt.total_seconds() / 3600

    return data.dropna(subset=["Elapsed Hours"]).copy()


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

    summary = (
        gaps.groupby(activity_column, observed=True)
        .agg(
            **{
                "Average Gap (hours)": ("Elapsed Hours", "mean"),
                "Median Gap (hours)": ("Elapsed Hours", "median"),
                "90th Percentile Gap (hours)": (
                    "Elapsed Hours",
                    lambda values: values.quantile(0.9),
                ),
                "Transitions": ("Elapsed Hours", "size"),
                "Cases": (case_column, "nunique"),
            }
        )
        .reset_index()
        .rename(columns={activity_column: "Preceding Activity"})
    )

    metric_options = {
        "90th percentile gap": "90th Percentile Gap (hours)",
        "Median gap": "Median Gap (hours)",
        "Average gap": "Average Gap (hours)",
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
    leading_activity = str(summary.iloc[0]["Preceding Activity"])
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
        y="Preceding Activity",
        orientation="h",
        text=ranking_column,
        labels={
            ranking_column: selected_metric.title() + " (hours)",
            "Preceding Activity": "Preceding activity",
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
                "Average Gap (hours)": 2,
                "Median Gap (hours)": 2,
                "90th Percentile Gap (hours)": 2,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
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