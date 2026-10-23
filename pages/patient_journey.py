import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import apply_chart_theme


def render_patient_journey(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render an event timeline and details for one selected case."""

    st.title("Patient Journey")
    st.write(
        "Review the timestamped events recorded for an individual case."
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
            "No events with valid case IDs, activities and timestamps were found."
        )
        return

    data[activity_column] = data[activity_column].astype(str)
    data = data.sort_values([case_column, timestamp_column], kind="mergesort")
    case_ids = data[case_column].drop_duplicates().tolist()
    selected_case = st.selectbox(
        "Select a case",
        options=case_ids,
        format_func=str,
        key="patient_journey_case",
    )

    journey = data[data[case_column] == selected_case].copy()
    journey = journey.sort_values(timestamp_column, kind="mergesort")
    journey["Event number"] = range(1, len(journey) + 1)
    journey["Hours since previous event"] = (
        journey[timestamp_column].diff().dt.total_seconds() / 3600
    )

    first_event = journey[timestamp_column].iloc[0]
    last_event = journey[timestamp_column].iloc[-1]
    duration_hours = (last_event - first_event).total_seconds() / 3600
    metric_cols = st.columns(3)
    metric_cols[0].metric("Recorded events", f"{len(journey):,}")
    metric_cols[1].metric(
        "Journey duration",
        f"{duration_hours:.1f} h",
    )
    metric_cols[2].metric(
        "Distinct activities",
        f"{journey[activity_column].nunique():,}",
    )

    st.subheader(f"Journey timeline — case {selected_case}")
    fig = px.scatter(
        journey,
        x=timestamp_column,
        y="Event number",
        color=activity_column,
        hover_data={
            activity_column: True,
            timestamp_column: "|%Y-%m-%d %H:%M:%S UTC",
            "Hours since previous event": ":.2f",
            "Event number": True,
        },
        labels={
            timestamp_column: "Event timestamp",
            "Event number": "Sequence position",
            activity_column: "Activity",
        },
    )
    fig.update_traces(
        marker=dict(size=13, line=dict(width=1, color="#FFFFFF")),
    )
    fig = apply_chart_theme(fig, height=max(340, len(journey) * 40))
    fig.update_layout(
        xaxis_title="Event timestamp",
        yaxis_title="Sequence position",
        yaxis=dict(
            tickmode="linear",
            dtick=1,
            autorange="reversed",
        ),
        legend_title_text="Activity",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Event details")
    displayed_journey = journey[
        [
            "Event number",
            activity_column,
            timestamp_column,
            "Hours since previous event",
        ]
    ].rename(
        columns={
            activity_column: "Activity",
            timestamp_column: "Timestamp (UTC)",
        }
    )
    st.dataframe(
        displayed_journey.round({"Hours since previous event": 2}),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download journey events",
        data=displayed_journey.to_csv(index=False).encode("utf-8"),
        file_name=(
            "careflow_journey_"
            + "".join(
                character
                if character.isalnum() or character in "-_"
                else "_"
                for character in str(selected_case)
            )
            + ".csv"
        ),
        mime="text/csv",
        key="download_patient_journey",
    )
    st.caption(
        "The journey duration and event gaps are based on recorded "
        "timestamps. They do not imply active treatment duration or queue time."
    )