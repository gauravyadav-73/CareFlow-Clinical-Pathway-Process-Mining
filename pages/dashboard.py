import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import COLORS, apply_chart_theme


def render_dashboard(
    df: pd.DataFrame | None,
    filename: str | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render the CareFlow overview and event-log summary."""

    st.markdown('<p class="main-title">CareFlow</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Clinical Pathway Process Mining and Analysis</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="info-card">
            <h3 style="color:#102a43;">Clinical pathway overview</h3>
            <p style="color:#486581;">
                Review uploaded event-log quality, activity patterns and
                recorded event timing to understand care pathways.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df is None or df.empty:
        st.info(
            "No dataset has been uploaded yet. Open the Upload Dataset page "
            "to get started."
        )
        col1, col2, col3 = st.columns(3)
        col1.markdown("### Upload data")
        col1.write("Import clinical event logs in CSV format.")
        col2.markdown("### Explore pathways")
        col2.write("Review patient activities and pathway variations.")
        col3.markdown("### Investigate delays")
        col3.write("Find long gaps between recorded events.")
        return

    valid_roles = (
        case_column in df.columns
        and activity_column in df.columns
        and timestamp_column in df.columns
        and len({case_column, activity_column, timestamp_column}) == 3
    )

    if valid_roles:
        case_values = df[case_column].dropna()
        activity_values = df[activity_column].dropna()
        valid_timestamps = pd.to_datetime(
            df[timestamp_column],
            errors="coerce",
            utc=True,
        )
        metric_values = [
            ("Total events", f"{len(df):,}"),
            ("Unique cases", f"{case_values.nunique():,}"),
            ("Unique activities", f"{activity_values.nunique():,}"),
            (
                "Valid timestamps",
                f"{int(valid_timestamps.notna().sum()):,}",
            ),
        ]
    else:
        metric_values = [
            ("Total events", f"{len(df):,}"),
            ("Columns", f"{len(df.columns):,}"),
            ("Missing values", f"{int(df.isna().sum().sum()):,}"),
            ("Unique values", f"{int(df.nunique().sum()):,}"),
        ]

    st.subheader("Dataset overview")
    metric_columns = st.columns(len(metric_values))
    for column, (label, value) in zip(metric_columns, metric_values):
        column.metric(label, value)

    if filename:
        st.caption(f"Current dataset: {filename}")

    if valid_roles:
        clean_activities = df[activity_column].dropna().astype(str)
        activity_counts = (
            clean_activities.value_counts()
            .head(12)
            .sort_values()
            .rename_axis("Activity")
            .reset_index(name="Events")
        )

        chart_col, trend_col = st.columns(2)
        with chart_col:
            st.subheader("Most frequent activities")
            if activity_counts.empty:
                st.info("No activity values are available.")
            else:
                fig = px.bar(
                    activity_counts,
                    x="Events",
                    y="Activity",
                    orientation="h",
                    labels={"Events": "Recorded events"},
                )
                fig.update_traces(
                    marker_color=COLORS["teal"],
                    hovertemplate="%{y}<br>Events: %{x}<extra></extra>",
                )
                fig = apply_chart_theme(
                    fig,
                    height=max(320, len(activity_counts) * 34),
                )
                fig.update_layout(
                    showlegend=False,
                    xaxis_title="Recorded events",
                    yaxis_title="",
                )
                st.plotly_chart(fig, use_container_width=True)

        with trend_col:
            st.subheader("Events over time")
            time_data = pd.DataFrame(
                {
                    "Timestamp": valid_timestamps,
                }
            ).dropna()
            if time_data.empty:
                st.info("No valid timestamps are available.")
            else:
                time_data = time_data.set_index("Timestamp")
                event_counts = (
                    time_data.resample("D")
                    .size()
                    .rename("Events")
                    .reset_index()
                )
                fig = px.line(
                    event_counts,
                    x="Timestamp",
                    y="Events",
                    markers=True,
                    labels={"Timestamp": "Date", "Events": "Recorded events"},
                )
                fig.update_traces(
                    line=dict(color=COLORS["blue"], width=3),
                    hovertemplate="%{x}<br>Events: %{y}<extra></extra>",
                )
                fig = apply_chart_theme(fig, height=350)
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Recorded events",
                )
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent event records")
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        return

    st.warning(
        "Choose distinct case ID, activity and timestamp columns on the "
        "Upload Dataset page to see pathway and timing analytics."
    )
    st.subheader("Recent dataset records")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)