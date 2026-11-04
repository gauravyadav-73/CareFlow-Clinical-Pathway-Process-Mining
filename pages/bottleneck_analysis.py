from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.analytics import calculate_event_gaps, summarize_activity_gaps
from utils.insights import generate_gap_insights


_METRIC_OPTIONS = {
    "Average Waiting Time": "Average gap (hours)",
    "Median Waiting Time": "Median gap (hours)",
    "90th Percentile Waiting Time": "90th percentile gap (hours)",
}

_PAGE_STYLES = """
<style>
.stApp:has(.st-key-bottleneck_analysis_page) .block-container {
    max-width: 1440px;
    padding-top: 1.15rem;
    padding-bottom: 2rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) h1,
.stApp:has(.st-key-bottleneck_analysis_page) h2,
.stApp:has(.st-key-bottleneck_analysis_page) h3,
.stApp:has(.st-key-bottleneck_analysis_page) p,
.stApp:has(.st-key-bottleneck_analysis_page) label,
.stApp:has(.st-key-bottleneck_analysis_page) [data-testid="stMarkdownContainer"] {
    color: #e5edf5;
}
.stApp:has(.st-key-bottleneck_analysis_page) .bottleneck-title {
    color: #f1f5f9;
    font-size: clamp(1.7rem, 3vw, 2.15rem);
    font-weight: 800;
    letter-spacing: -0.055em;
    line-height: 1.2;
    margin: 0 0 0.1rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) .bottleneck-subtitle {
    color: #a2b2c4;
    font-size: 0.9rem;
    margin: 0 0 1rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) .st-key-bottleneck_controls,
.stApp:has(.st-key-bottleneck_analysis_page) .st-key-bottleneck_chart_card,
.stApp:has(.st-key-bottleneck_analysis_page) .st-key-bottleneck_table_card {
    background: #1f2937;
    border: 1px solid #37475a;
    border-radius: 12px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
    padding: 0.7rem 0.9rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) .st-key-bottleneck_controls {
    margin-bottom: 0.9rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) .bottleneck-alert {
    align-items: center;
    background: linear-gradient(105deg, #202b3a, #1d2938);
    border: 1px solid #80522d;
    border-radius: 12px;
    color: #e5edf5;
    display: flex;
    gap: 0.8rem;
    margin: 0.15rem 0 0.9rem;
    padding: 0.85rem 1rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) .bottleneck-alert-icon {
    align-items: center;
    background: #563a22;
    border-radius: 10px;
    color: #fbbf24;
    display: flex;
    flex: 0 0 38px;
    font-size: 1.25rem;
    height: 38px;
    justify-content: center;
}
.stApp:has(.st-key-bottleneck_analysis_page) .bottleneck-alert-title {
    color: #fbbf24;
    font-size: 0.86rem;
    font-weight: 750;
    margin-bottom: 0.15rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) .bottleneck-alert-copy {
    color: #dbe5ef;
    font-size: 0.8rem;
    line-height: 1.5;
}
.stApp:has(.st-key-bottleneck_analysis_page) .bottleneck-card-title {
    color: #f1f5f9;
    font-size: 0.95rem;
    font-weight: 750;
    margin: 0.1rem 0 0.35rem;
}
.stApp:has(.st-key-bottleneck_analysis_page) [data-testid="stCaptionContainer"] {
    color: #a2b2c4;
}
.stApp:has(.st-key-bottleneck_analysis_page) .stButton > button,
.stApp:has(.st-key-bottleneck_analysis_page) .stFormSubmitButton > button {
    background: #1677e8;
    border: 1px solid #1677e8;
    border-radius: 8px;
    color: white;
    min-height: 40px;
    font-weight: 700;
}
.stApp:has(.st-key-bottleneck_analysis_page) .stButton > button:hover,
.stApp:has(.st-key-bottleneck_analysis_page) .stFormSubmitButton > button:hover {
    background: #0c65cb;
    border-color: #0c65cb;
    color: white;
}
.stApp:has(.st-key-bottleneck_analysis_page) [data-baseweb="select"] > div {
    background: #111827;
    border-color: #475569;
}
.stApp:has(.st-key-bottleneck_analysis_page) [data-testid="stDataFrame"] {
    border: 1px solid #37475a;
    border-radius: 8px;
}
</style>
"""


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


def _waiting_time_chart(
    summary: pd.DataFrame,
    ranking_column: str,
    metric_label: str,
) -> go.Figure:
    """Build the ranked horizontal waiting-time chart in days."""
    chart_data = summary.head(20)
    values_in_days = chart_data[ranking_column] / 24
    colors = ["#f59e0b"] + ["#3b82f6"] * (len(chart_data) - 1)

    fig = go.Figure(
        go.Bar(
            x=values_in_days,
            y=chart_data["Preceding activity"],
            orientation="h",
            marker_color=colors,
            text=[f"{value:.1f} d" for value in values_in_days],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                + metric_label
                + ": %{x:.2f} days<extra></extra>"
            ),
        )
    )
    max_value = float(values_in_days.max()) if not values_in_days.empty else 0
    fig.update_layout(
        height=max(300, len(chart_data) * 46 + 45),
        margin=dict(l=8, r=42, t=4, b=36),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#dbe5ef", size=11),
        showlegend=False,
        xaxis=dict(
            title=dict(text=f"{metric_label} (days)", font=dict(size=10)),
            range=[0, max_value * 1.28 if max_value else 1],
            showgrid=True,
            gridcolor="#37475a",
            zeroline=False,
            tickfont=dict(size=10, color="#a2b2c4"),
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            showgrid=False,
            tickfont=dict(size=10, color="#dbe5ef"),
        ),
    )
    return fig


def render_bottleneck_analysis(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render an event-gap analysis using the selected event-log columns."""

    st.markdown(_PAGE_STYLES, unsafe_allow_html=True)
    with st.container(key="bottleneck_analysis_page"):
        st.markdown(
            '<h1 class="bottleneck-title">Bottleneck Analysis</h1>'
            '<p class="bottleneck-subtitle">Identify activities and '
            'transitions that cause delays in the clinical pathway.</p>',
            unsafe_allow_html=True,
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

        gaps = _event_gaps(df, case_column, activity_column, timestamp_column)
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
        if summary.empty:
            st.info("There are no activity transitions to rank.")
            return

        with st.container(key="bottleneck_controls"):
            with st.form("bottleneck_analysis_controls", border=False):
                metric_col, count_col, spacer_col, button_col = st.columns(
                    [1.25, 0.8, 0.8, 0.85],
                    vertical_alignment="bottom",
                )
                with metric_col:
                    metric_label = st.selectbox(
                        "Analysis Type",
                        options=list(_METRIC_OPTIONS),
                        key="bottleneck_analysis_type",
                    )
                with count_col:
                    top_n = st.selectbox(
                        "Top N",
                        options=[5, 10, 15, 20],
                        key="bottleneck_top_n",
                    )
                with spacer_col:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                with button_col:
                    st.form_submit_button(
                        "Run Analysis",
                        type="primary",
                        use_container_width=True,
                    )

        ranking_column = _METRIC_OPTIONS[metric_label]
        summary = summary.sort_values(
            ranking_column,
            ascending=False,
            kind="mergesort",
        ).reset_index(drop=True)
        leading = summary.iloc[0]
        leading_activity = escape(str(leading["Preceding activity"]))
        leading_wait_days = float(leading[ranking_column]) / 24
        affected_cases = int(leading["Cases"])
        visible_summary = summary.head(top_n).copy()

        st.markdown(
            f"""
            <div class="bottleneck-alert">
                <div class="bottleneck-alert-icon">⚠</div>
                <div>
                    <div class="bottleneck-alert-title">Bottleneck Alert</div>
                    <div class="bottleneck-alert-copy">
                        <strong>{leading_activity}</strong> has the highest
                        observed waiting time at <strong>{leading_wait_days:.1f}
                        days</strong>, affecting <strong>{affected_cases:,}
                        cases</strong>. Waiting time is measured between
                        consecutive recorded events.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        chart_col, table_col = st.columns([1.05, 0.95], gap="small")
        with chart_col:
            with st.container(key="bottleneck_chart_card"):
                st.markdown(
                    f'<div class="bottleneck-card-title">{escape(metric_label)} '
                    "by Activity</div>",
                    unsafe_allow_html=True,
                )
                fig = _waiting_time_chart(
                    visible_summary,
                    ranking_column,
                    metric_label,
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        with table_col:
            with st.container(key="bottleneck_table_card"):
                st.markdown(
                    '<div class="bottleneck-card-title">'
                    'Bottleneck Activities (Ranked)</div>',
                    unsafe_allow_html=True,
                )
                display_summary = pd.DataFrame(
                    {
                        "Rank": range(1, len(visible_summary) + 1),
                        "Activity": visible_summary["Preceding activity"].astype(str),
                        "Waiting Time (days)": (
                            visible_summary[ranking_column] / 24
                        ).round(1),
                        "Affected Cases": visible_summary["Cases"].astype(int),
                    }
                )
                st.dataframe(
                    display_summary,
                    width="stretch",
                    hide_index=True,
                    height=min(420, 42 + len(display_summary) * 35),
                    column_config={
                        "Rank": st.column_config.NumberColumn(
                            "Rank",
                            format="%d",
                            width="small",
                        ),
                        "Waiting Time (days)": st.column_config.NumberColumn(
                            "Waiting Time (days)",
                            format="%.1f",
                        ),
                        "Affected Cases": st.column_config.NumberColumn(
                            "Affected Cases",
                            format="%d",
                        ),
                    },
                )
                st.caption(
                    f"Showing the top {len(display_summary)} activities by "
                    f"{metric_label.lower()}."
                )

        with st.expander("Detailed gap statistics and export"):
            st.caption(
                "Gap duration is elapsed time between consecutive valid events, "
                "attributed to the preceding activity. It is not necessarily "
                "queue time, treatment duration or a confirmed clinical bottleneck."
            )
            st.dataframe(
                summary.round(
                    {
                        "Average gap (hours)": 2,
                        "Median gap (hours)": 2,
                        "90th percentile gap (hours)": 2,
                        "Total gap (hours)": 2,
                    }
                ),
                width="stretch",
                hide_index=True,
            )
            st.write("**Observed data insights**")
            for insight in generate_gap_insights(summary):
                st.write(f"- {insight}")
            st.download_button(
                "Download bottleneck summary",
                data=summary.to_csv(index=False).encode("utf-8"),
                file_name="careflow_bottleneck_summary.csv",
                mime="text/csv",
                key="download_bottleneck_summary",
            )
