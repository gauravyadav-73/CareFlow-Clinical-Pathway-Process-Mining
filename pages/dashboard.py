from html import escape

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

    dataset_available = df is not None and not df.empty
    dataset_label = (
        escape(filename)
        if dataset_available and filename
        else "Workspace overview"
    )
    status_label = (
        f"Dataset ready · {dataset_label}"
        if dataset_available
        else "Workspace ready · upload an event log to begin"
    )
    st.markdown(
        f"""
        <section class="cf-dashboard-hero">
            <div class="cf-dashboard-kicker">CareFlow · Clinical intelligence</div>
            <h1 class="cf-dashboard-title">Clinical operations overview</h1>
            <p class="cf-dashboard-copy">
                A clearer view of patient pathways, activity patterns, and
                opportunities to improve how care flows.
            </p>
            <div class="cf-live-pill">
                <span class="cf-live-dot"></span>
                {status_label}
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not dataset_available:
        st.info(
            "Your analysis workspace is ready. Upload a clinical event log "
            "and map its case, activity, and timestamp columns to unlock the "
            "pathway analytics."
        )
        st.subheader("Your workflow")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 01 · Bring in your data")
            st.write("Upload a CSV event log and map its key event fields.")
        with col2:
            st.markdown("### 02 · Discover the process")
            st.write("See the activities and routes patients follow.")
        with col3:
            st.markdown("### 03 · Find opportunities")
            st.write("Compare pathways and investigate event-time gaps.")
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

    st.subheader("At a glance")
    metric_columns = st.columns(len(metric_values))
    for column, (label, value) in zip(metric_columns, metric_values):
        column.metric(label, value)

    if filename:
        st.caption(f"Active event log · {filename}")

    if valid_roles:
        clean_activities = df[activity_column].dropna().astype(str)
        activity_counts = (
            clean_activities.value_counts()
            .head(12)
            .sort_values()
            .rename_axis("Activity")
            .reset_index(name="Events")
        )

        st.subheader("Pathway signals")
        chart_col, trend_col = st.columns([1, 1], gap="large")
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
                st.plotly_chart(fig, width="stretch")

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
                st.plotly_chart(fig, width="stretch")

        st.subheader("Recent event records")
        st.dataframe(df.head(10), width="stretch", hide_index=True)
        return

    st.warning(
        "Choose distinct case ID, activity and timestamp columns on the "
        "Upload Dataset page to see pathway and timing analytics."
    )
    st.subheader("Recent dataset records")
    st.dataframe(df.head(10), width="stretch", hide_index=True)