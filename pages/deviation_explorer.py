from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import COLORS, apply_chart_theme
from utils.process_mining import build_case_traces


def _describe_deviation(
    reference: tuple[str, ...],
    observed: tuple[str, ...],
) -> str:
    """Describe the first differing position between two activity traces."""

    shared_length = min(len(reference), len(observed))
    for index in range(shared_length):
        if reference[index] != observed[index]:
            return (
                f"Position {index + 1}: expected "
                f"'{reference[index]}', observed '{observed[index]}'"
            )

    if len(observed) < len(reference):
        return f"Pathway ends early; expected '{reference[len(observed)]}' next"

    if len(observed) > len(reference):
        return f"Unexpected extra activity '{observed[len(reference)]}'"

    return "Matches the reference pathway"


def render_deviation_explorer(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render observed pathway variants and case-level deviation details."""

    st.title("Deviation Explorer")
    st.write(
        "Explore how patient pathways differ from a frequently observed "
        "reference pathway."
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

    case_pathways = [
        (str(case_id), pathway)
        for case_id, pathway in build_case_traces(
        df,
        case_column,
        activity_column,
        timestamp_column,
        )
    ]
    if not case_pathways:
        st.info(
            "No complete case pathways were found. Check the selected "
            "columns for missing or invalid values."
        )
        return

    pathway_counts = Counter(pathway for _, pathway in case_pathways)
    variants = sorted(
        pathway_counts,
        key=lambda pathway: (-pathway_counts[pathway], pathway),
    )
    reference = variants[0]
    max_reference_count = pathway_counts[reference]

    metric_columns = st.columns(3)
    metric_columns[0].metric("Cases analysed", f"{len(case_pathways):,}")
    metric_columns[1].metric("Observed variants", f"{len(variants):,}")
    metric_columns[2].metric(
        "Most common pathway",
        f"{max_reference_count:,} cases",
    )

    st.subheader("Pathway variant distribution")
    visible_variants = variants[:20]
    variant_rows = [
        {
            "Pathway": " → ".join(pathway),
            "Events": len(pathway),
            "Cases": pathway_counts[pathway],
            "Share (%)": pathway_counts[pathway] / len(case_pathways) * 100,
        }
        for pathway in visible_variants
    ]
    variant_df = pd.DataFrame(variant_rows)
    chart_df = variant_df.sort_values(
        "Cases",
        ascending=True,
        kind="mergesort",
    )
    fig = px.bar(
        chart_df,
        x="Cases",
        y="Pathway",
        orientation="h",
        labels={"Cases": "Cases"},
    )
    fig.update_traces(
        marker_color=COLORS["purple"],
        hovertemplate="%{y}<br>Cases: %{x}<extra></extra>",
    )
    fig = apply_chart_theme(fig, height=max(340, len(chart_df) * 36))
    fig.update_layout(showlegend=False, xaxis_title="Cases", yaxis_title="")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        variant_df.round({"Share (%)": 1}),
        width="stretch",
        hide_index=True,
    )

    variant_labels = [
        (
            f"{' → '.join(pathway)} "
            f"({pathway_counts[pathway]} cases)"
        )
        for pathway in variants
    ]
    selected_variant_index = st.selectbox(
        "Inspect a pathway variant",
        options=range(len(variants)),
        format_func=lambda index: variant_labels[index],
        key="deviation_selected_variant",
    )
    selected_pathway = variants[selected_variant_index]
    is_deviation = selected_pathway != reference
    deviation_cases = []
    for case_id, pathway in case_pathways:
        if pathway == selected_pathway:
            deviation_cases.append(
                {
                    "Case ID": case_id,
                    "Events": len(pathway),
                    "First difference from common pathway": (
                        _describe_deviation(reference, pathway)
                    ),
                    "Observed pathway": " → ".join(pathway),
                }
            )

    st.subheader("Selected variant details")
    if is_deviation:
        st.warning(
            "This pathway differs from the most frequently observed pathway."
        )
    else:
        st.success(
            "This is the most frequently observed pathway and is used as "
            "the comparison reference."
        )
    st.caption(f"Reference: {' → '.join(reference)}")
    st.dataframe(
        pd.DataFrame(deviation_cases),
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Download selected variant cases",
        data=pd.DataFrame(deviation_cases).to_csv(index=False).encode("utf-8"),
        file_name="careflow_deviation_cases.csv",
        mime="text/csv",
        key="download_deviation_cases",
    )
    st.caption(
        "The reference is the most frequently observed pathway in this event "
        "log, not a clinically prescribed standard. Pathways use valid events "
        "ordered by timestamp; ties retain their original row order."
    )