import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ==========================================================
# CAREFLOW CHART THEME
# ==========================================================

COLORS = {
    "navy": "#102A43",
    "teal": "#0F766E",
    "mint": "#99F6E4",
    "blue": "#3B82F6",
    "purple": "#8B5CF6",
    "orange": "#F59E0B",
    "red": "#EF4444",
    "green": "#16A34A",
    "muted": "#627D98",
    "background": "#FFFFFF",
    "grid": "#E8EEF4",
}


def apply_chart_theme(fig, height=380):
    """
    Apply a consistent CareFlow theme to a Plotly figure.
    """

    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, sans-serif",
            color=COLORS["navy"],
            size=12,
        ),
        title=dict(
            font=dict(
                size=17,
                color=COLORS["navy"],
            ),
            x=0,
            xanchor="left",
        ),
        margin=dict(
            l=15,
            r=15,
            t=55,
            b=25,
        ),
        hoverlabel=dict(
            bgcolor="#102A43",
            font_color="#FFFFFF",
            font_size=12,
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=COLORS["grid"],
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grid"],
        zeroline=False,
    )

    return fig


# ==========================================================
# 1. ACTIVITY FREQUENCY CHART
# ==========================================================

def activity_frequency_chart(
    df,
    activity_column,
    top_n=10,
):
    """
    Display the most frequently recorded clinical activities.
    """

    if df is None or df.empty:
        st.info("Upload a dataset to view activity frequency.")
        return

    if activity_column not in df.columns:
        st.warning("Please select a valid activity column.")
        return

    counts = (
        df[activity_column]
        .dropna()
        .astype(str)
        .value_counts()
        .head(top_n)
        .sort_values()
        .reset_index()
    )

    counts.columns = ["Activity", "Events"]

    if counts.empty:
        st.info("No activity data is available.")
        return

    fig = px.bar(
        counts,
        x="Events",
        y="Activity",
        orientation="h",
        text="Events",
        title="Most Frequent Clinical Activities",
    )

    fig.update_traces(
        marker_color=COLORS["teal"],
        marker_line_width=0,
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Recorded events: %{x}"
            "<extra></extra>"
        ),
    )

    fig = apply_chart_theme(
        fig,
        height=max(320, len(counts) * 38),
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="Number of Events",
        yaxis_title="",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ==========================================================
# 2. PATIENT ACTIVITY DISTRIBUTION
# ==========================================================

def activity_distribution_chart(
    df,
    activity_column,
):
    """
    Display the distribution of recorded activities.
    """

    if df is None or df.empty:
        st.info("No dataset is available.")
        return

    if activity_column not in df.columns:
        st.warning("Please select a valid activity column.")
        return

    counts = (
        df[activity_column]
        .dropna()
        .astype(str)
        .value_counts()
        .reset_index()
    )

    counts.columns = ["Activity", "Events"]

    if counts.empty:
        st.info("No activities are available to display.")
        return

    # A bar chart is easier to read when there are many activities.
    fig = px.pie(
        counts,
        names="Activity",
        values="Events",
        hole=0.65,
        title="Clinical Activity Distribution",
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Events: %{value}<br>"
            "Share: %{percent}"
            "<extra></extra>"
        ),
    )

    fig = apply_chart_theme(fig, height=400)

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ==========================================================
# 3. EVENTS OVER TIME
# ==========================================================

def events_over_time_chart(
    df,
    timestamp_column,
    frequency="D",
):
    """
    Display event counts over time.

    frequency:
        D = Daily
        W = Weekly
        ME = Monthly
    """

    if df is None or df.empty:
        st.info("Upload a dataset to view event trends.")
        return

    if timestamp_column not in df.columns:
        st.warning("Please select a valid timestamp column.")
        return

    data = df[[timestamp_column]].copy()

    data[timestamp_column] = pd.to_datetime(
        data[timestamp_column],
        errors="coerce",
        utc=True,
    )

    data = data.dropna(subset=[timestamp_column])

    if data.empty:
        st.info(
            "No valid timestamps were found in this dataset."
        )
        return

    data = data.set_index(timestamp_column)

    counts = (
        data.resample(frequency)
        .size()
        .reset_index(name="Events")
    )

    if counts.empty:
        st.info("There are no events to display.")
        return

    fig = px.line(
        counts,
        x=timestamp_column,
        y="Events",
        markers=True,
        title="Clinical Events Over Time",
    )

    fig.update_traces(
        line=dict(
            color=COLORS["teal"],
            width=3,
        ),
        marker=dict(size=7),
        hovertemplate=(
            "Date: %{x}<br>"
            "Events: %{y}"
            "<extra></extra>"
        ),
    )

    fig = apply_chart_theme(fig, height=350)

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Events",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ==========================================================
# 4. PATIENT EVENT COUNTS
# ==========================================================

def patient_event_count_chart(
    df,
    case_column,
    top_n=10,
):
    """
    Compare the number of recorded events per case.
    """

    if df is None or df.empty:
        st.info("Upload a dataset to view patient event counts.")
        return

    if case_column not in df.columns:
        st.warning("Please select a valid case ID column.")
        return

    counts = (
        df[case_column]
        .dropna()
        .astype(str)
        .value_counts()
        .head(top_n)
        .sort_values()
        .reset_index()
    )

    counts.columns = ["Case ID", "Events"]

    if counts.empty:
        st.info("No valid case IDs were found.")
        return

    fig = px.bar(
        counts,
        x="Events",
        y="Case ID",
        orientation="h",
        text="Events",
        title="Cases with the Most Recorded Events",
    )

    fig.update_traces(
        marker_color=COLORS["blue"],
        textposition="outside",
        cliponaxis=False,
    )

    fig = apply_chart_theme(
        fig,
        height=max(320, len(counts) * 35),
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="Number of Events",
        yaxis_title="Case ID",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ==========================================================
# 5. WAITING TIME BY ACTIVITY
# ==========================================================

def waiting_time_chart(
    df,
    case_column,
    activity_column,
    timestamp_column,
):
    """
    Calculate elapsed time between consecutive recorded events
    within each case, attributed to the preceding activity.

    These gaps are not necessarily actual clinical waiting times.
    """

    required_columns = [
        case_column,
        activity_column,
        timestamp_column,
    ]

    if df is None or df.empty:
        st.info("Upload a dataset to analyse event timing.")
        return

    if any(
        column not in df.columns
        for column in required_columns
    ):
        st.warning(
            "Select valid case, activity and timestamp columns."
        )
        return

    data = df[required_columns].copy()

    data[timestamp_column] = pd.to_datetime(
        data[timestamp_column],
        errors="coerce",
        utc=True,
    )

    data = data.dropna(subset=required_columns)

    data = data.sort_values(
        [case_column, timestamp_column]
    )

    data["Next Timestamp"] = (
        data.groupby(case_column)[timestamp_column].shift(-1)
    )

    data["Elapsed Hours"] = (
        data["Next Timestamp"] - data[timestamp_column]
    ).dt.total_seconds() / 3600

    transitions = data.dropna(
        subset=["Elapsed Hours"]
    ).copy()

    if transitions.empty:
        st.info(
            "Insufficient consecutive timestamped events "
            "to calculate elapsed times."
        )
        return

    summary = (
        transitions.groupby(activity_column)["Elapsed Hours"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .sort_values()
        .reset_index()
    )

    summary.columns = [
        "Activity",
        "Average Elapsed Hours",
    ]

    fig = px.bar(
        summary,
        x="Average Elapsed Hours",
        y="Activity",
        orientation="h",
        title="Activities with the Longest Average Event Gaps",
    )

    fig.update_traces(
        marker_color=COLORS["orange"],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Average gap: %{x:.2f} hours"
            "<extra></extra>"
        ),
    )

    fig = apply_chart_theme(
        fig,
        height=max(320, len(summary) * 38),
    )

    fig.update_layout(
        xaxis_title="Average Elapsed Time (Hours)",
        yaxis_title="",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.caption(
        "Event gaps are attributed to the preceding activity. "
        "They do not necessarily represent actual queue time, "
        "treatment duration or a confirmed clinical bottleneck."
    )


# ==========================================================
# 6. PATIENT PATHWAY TIMELINE
# ==========================================================

def patient_pathway_timeline(
    df,
    case_column,
    activity_column,
    timestamp_column,
):
    """
    Display the recorded events for a selected case.
    """

    required_columns = [
        case_column,
        activity_column,
        timestamp_column,
    ]

    if df is None or df.empty:
        st.info("Upload a dataset to explore patient pathways.")
        return

    if any(
        column not in df.columns
        for column in required_columns
    ):
        st.warning(
            "Select valid case, activity and timestamp columns."
        )
        return

    data = df[required_columns].copy()

    data[timestamp_column] = pd.to_datetime(
        data[timestamp_column],
        errors="coerce",
        utc=True,
    )

    data = data.dropna(
        subset=[
            case_column,
            activity_column,
            timestamp_column,
        ]
    )

    cases = data[case_column].unique().tolist()

    if not cases:
        st.info("No valid patient cases were found.")
        return

    selected_case = st.selectbox(
        "Select a case",
        cases,
        key="careflow_timeline_case",
    )

    patient_data = (
        data[data[case_column] == selected_case]
        .sort_values(timestamp_column)
        .copy()
    )

    patient_data["Event Number"] = range(
        1,
        len(patient_data) + 1,
    )

    patient_data["Activity"] = (
        patient_data[activity_column].astype(str)
    )

    fig = px.scatter(
        patient_data,
        x=timestamp_column,
        y="Event Number",
        color="Activity",
        hover_data=[
            case_column,
            activity_column,
        ],
        title="Recorded Patient Event Timeline",
    )

    fig.update_traces(
        marker=dict(size=12),
    )

    fig = apply_chart_theme(
        fig,
        height=400,
    )

    fig.update_layout(
        xaxis_title="Event Timestamp",
        yaxis_title="Sequence Number",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        patient_data[
            [
                case_column,
                activity_column,
                timestamp_column,
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


# ==========================================================
# 7. COMPARE TWO ACTIVITIES
# ==========================================================

def activity_comparison_chart(
    df,
    activity_column,
    case_column,
):
    """
    Compare the number of distinct cases associated with activities.
    """

    if df is None or df.empty:
        st.info("Upload a dataset to compare activities.")
        return

    if (
        activity_column not in df.columns
        or case_column not in df.columns
    ):
        st.warning(
            "Select valid activity and case ID columns."
        )
        return

    comparison = (
        df.dropna(subset=[activity_column, case_column])
        .groupby(activity_column)[case_column]
        .nunique()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    comparison.columns = [
        "Activity",
        "Distinct Cases",
    ]

    if comparison.empty:
        st.info("No activity comparison data is available.")
        return

    fig = px.bar(
        comparison,
        x="Activity",
        y="Distinct Cases",
        title="Distinct Cases per Activity",
    )

    fig.update_traces(
        marker_color=COLORS["purple"],
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Distinct cases: %{y}"
            "<extra></extra>"
        ),
    )

    fig = apply_chart_theme(
        fig,
        height=380,
    )

    fig.update_layout(
        xaxis_title="Activity",
        yaxis_title="Distinct Cases",
        xaxis_tickangle=-30,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )