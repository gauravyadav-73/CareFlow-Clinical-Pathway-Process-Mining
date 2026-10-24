import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import COLORS, apply_chart_theme
from utils.analytics import summarize_activity_gaps


def render_what_if_simulator(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Estimate the effect of reducing elapsed gaps after one activity."""

    st.title("What-if Simulator")
    st.write(
        "Model a hypothetical reduction in event gaps after a selected "
        "activity and estimate the corresponding time savings."
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

    summary = summarize_activity_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    if summary.empty:
        st.info(
            "At least one case needs two valid, timestamped events to simulate "
            "a gap reduction."
        )
        return

    scenario_cols = st.columns(2)
    activity_options = summary["Preceding activity"].tolist()
    with scenario_cols[0]:
        selected_activity = st.selectbox(
            "Activity whose following gap to reduce",
            activity_options,
            key="what_if_activity",
        )
    with scenario_cols[1]:
        reduction_percent = st.slider(
            "Hypothetical gap reduction",
            min_value=0,
            max_value=90,
            value=20,
            step=5,
            format="%d%%",
            key="what_if_reduction_percent",
        )

    target = summary[
        summary["Preceding activity"] == selected_activity
    ].iloc[0]
    rate = reduction_percent / 100
    average_gap = float(target["Average gap (hours)"])
    median_gap = float(target["Median gap (hours)"])
    total_gap = float(target["Total gap (hours)"])
    projected_average = average_gap * (1 - rate)
    projected_median = median_gap * (1 - rate)
    estimated_total_savings = total_gap * rate
    estimated_savings_per_transition = average_gap * rate

    metrics = st.columns(4)
    metrics[0].metric("Affected transitions", f"{int(target['Transitions']):,}")
    metrics[1].metric("Current average gap", f"{average_gap:.1f} h")
    metrics[2].metric(
        "Projected average gap",
        f"{projected_average:.1f} h",
        delta=f"-{estimated_savings_per_transition:.1f} h",
        delta_color="inverse",
    )
    metrics[3].metric(
        "Estimated total time saved",
        f"{estimated_total_savings:.1f} h",
    )

    st.subheader("Baseline and simulated gap")
    chart_data = pd.DataFrame(
        {
            "Measure": ["Average gap", "Median gap"],
            "Baseline (hours)": [average_gap, median_gap],
            "Simulated (hours)": [projected_average, projected_median],
        }
    )
    chart_long = chart_data.melt(
        id_vars="Measure",
        var_name="Scenario",
        value_name="Elapsed hours",
    )
    fig = px.bar(
        chart_long,
        x="Measure",
        y="Elapsed hours",
        color="Scenario",
        barmode="group",
        color_discrete_map={
            "Baseline (hours)": COLORS["muted"],
            "Simulated (hours)": COLORS["teal"],
        },
    )
    fig = apply_chart_theme(fig, height=350)
    fig.update_layout(xaxis_title="", yaxis_title="Elapsed time (hours)")
    st.plotly_chart(fig, width="stretch")

    result = summary.copy()
    result["Reduction (%)"] = 0
    result["Estimated total savings (hours)"] = 0.0
    selected_mask = result["Preceding activity"] == selected_activity
    result.loc[selected_mask, "Reduction (%)"] = reduction_percent
    result.loc[selected_mask, "Estimated total savings (hours)"] = (
        result.loc[selected_mask, "Total gap (hours)"] * rate
    )
    st.subheader("Activity-level baseline")
    st.dataframe(
        result.round(
            {
                "Average gap (hours)": 2,
                "Median gap (hours)": 2,
                "Total gap (hours)": 2,
                "Estimated total savings (hours)": 2,
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Download scenario results",
        data=result.to_csv(index=False).encode("utf-8"),
        file_name="careflow_what_if_scenario.csv",
        mime="text/csv",
        key="download_what_if_scenario",
    )
    st.caption(
        "This scenario applies the selected percentage uniformly to observed "
        "gaps after the chosen activity. It is a mathematical estimate, not "
        "a forecast or evidence that a process change will achieve that result. "
        "Elapsed event gaps are not necessarily queue or treatment time."
    )