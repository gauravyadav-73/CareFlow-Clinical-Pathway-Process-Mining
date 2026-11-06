from collections import Counter
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.process_mining import build_case_traces, conformance_report


def _format_pathway(pathway: tuple[str, ...], max_length: int = 90) -> str:
    text = " → ".join(pathway)
    if len(text) > max_length:
        return text[: max_length - 1] + "…"
    return text


def _render_pathway_row(
    label: str,
    pathway: tuple[str, ...],
    case_count: int,
) -> None:
    steps = "".join(
        f'<span class="cf-flow-step">{escape(activity)}</span>'
        for activity in pathway
    )
    st.markdown(
        f"""
        <div class="cf-flow-row">
            <div class="cf-flow-label">{escape(label)}</div>
            <div class="cf-flow-track">
                <span class="cf-flow-end">Start</span>
                {steps}
                <span class="cf-flow-end">End</span>
            </div>
            <div class="cf-flow-count">{case_count:,} cases</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_conformance_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #F3F6FB;
            color: #172B45;
        }

        .main .block-container {
            max-width: 1440px;
            padding-top: 2rem;
            padding-bottom: 2.5rem;
        }

        .main .block-container h1,
        .main .block-container h2,
        .main .block-container h3 {
            color: #102A43;
        }

        .cf-conformance-header {
            margin-bottom: 1.25rem;
        }

        .cf-conformance-kicker {
            color: #0F8C82;
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.12em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .cf-conformance-title {
            color: #102A43;
            font-size: clamp(1.8rem, 3vw, 2.35rem);
            font-weight: 800;
            letter-spacing: -0.045em;
            line-height: 1.15;
            margin: 0;
        }

        .cf-conformance-subtitle {
            color: #62758B;
            font-size: 0.94rem;
            margin: 0.45rem 0 0;
        }

        .main .block-container [data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border: 1px solid #E1E8F0;
            border-radius: 16px;
            box-shadow: 0 5px 18px rgba(16, 42, 67, 0.045);
        }

        .main .block-container [data-testid="stVerticalBlockBorderWrapper"] h3 {
            font-size: 1rem;
            letter-spacing: -0.02em;
        }

        .cf-card-heading {
            color: #18324E;
            font-size: 1rem;
            font-weight: 750;
            margin: 0 0 0.15rem;
        }

        .cf-card-subtitle {
            color: #73849A;
            font-size: 0.78rem;
            margin: 0 0 0.75rem;
        }

        .cf-result-stat {
            border-bottom: 1px solid #EDF1F6;
            padding: 0.68rem 0;
        }

        .cf-result-stat:last-child {
            border-bottom: 0;
        }

        .cf-result-stat-label {
            color: #6B7E93;
            font-size: 0.76rem;
        }

        .cf-result-stat-value {
            color: #18324E;
            font-size: 1.05rem;
            font-weight: 750;
            margin-top: 0.1rem;
        }

        .cf-status-dot {
            border-radius: 50%;
            display: inline-block;
            height: 0.55rem;
            margin-right: 0.4rem;
            width: 0.55rem;
        }

        .cf-status-line {
            color: #42566D;
            font-size: 0.78rem;
            margin: 0.35rem 0;
        }

        .cf-flow-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.25rem 0 1rem;
        }

        .cf-flow-legend span {
            border-radius: 99px;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.3rem 0.65rem;
        }

        .cf-flow-expected {
            background: #E8F1FF;
            color: #2865B2;
        }

        .cf-flow-observed {
            background: #F1EAFE;
            color: #7045B8;
        }

        .cf-flow-row {
            border-top: 1px solid #EDF1F6;
            padding: 0.9rem 0 0.75rem;
        }

        .cf-flow-label {
            color: #334B65;
            font-size: 0.76rem;
            font-weight: 700;
            margin-bottom: 0.6rem;
        }

        .cf-flow-track {
            align-items: center;
            display: flex;
            gap: 0.35rem;
            overflow-x: auto;
            padding: 0.1rem 0 0.55rem;
            scrollbar-color: #CBD5E1 transparent;
        }

        .cf-flow-step,
        .cf-flow-end {
            border: 1px solid #C8D9F1;
            border-radius: 7px;
            color: #284C78;
            flex: 0 0 auto;
            font-size: 0.69rem;
            font-weight: 650;
            padding: 0.42rem 0.58rem;
            white-space: nowrap;
        }

        .cf-flow-step::after {
            color: #98A9BD;
            content: "→";
            font-size: 0.8rem;
            margin-left: 0.6rem;
        }

        .cf-flow-end {
            background: #E7FAF2;
            border-color: #B7EBD3;
            color: #18764E;
        }

        .cf-flow-count {
            color: #8291A3;
            font-size: 0.7rem;
            margin-top: 0.2rem;
        }

        .main .block-container [data-testid="stDataFrame"] {
            border: 1px solid #E1E8F0;
            border-radius: 12px;
            box-shadow: none;
        }

        .main .block-container [data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid #E1E8F0;
            border-radius: 12px;
        }

        .main .block-container [data-testid="stSelectbox"] label {
            color: #42566D;
            font-weight: 650;
        }

        .main .block-container [data-baseweb="select"] > div {
            background: #FFFFFF;
            border-color: #D6E0EA;
            color: #18324E;
        }

        .main .block-container [data-testid="stCaptionContainer"] {
            color: #73849A;
        }

        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1.25rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_conformance_chart(conformant_count: int, total_cases: int) -> go.Figure:
    deviating_count = total_cases - conformant_count
    conformance_rate = conformant_count / total_cases * 100
    figure = go.Figure(
        go.Pie(
            labels=["Conformant cases", "Deviating cases"],
            values=[conformant_count, deviating_count],
            hole=0.76,
            sort=False,
            direction="clockwise",
            marker=dict(colors=["#16B7A2", "#FF6B61"]),
            textinfo="none",
            hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
        )
    )
    figure.update_layout(
        height=225,
        margin=dict(l=0, r=0, t=4, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Inter, sans-serif", color="#18324E", size=12),
        annotations=[
            dict(
                text=f"<b>{conformance_rate:.0f}%</b>",
                x=0.5,
                y=0.53,
                showarrow=False,
                font=dict(size=30, color="#18324E"),
            ),
            dict(
                text="conformant",
                x=0.5,
                y=0.35,
                showarrow=False,
                font=dict(size=10, color="#73849A"),
            ),
        ],
    )
    return figure


def render_conformance_analysis(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render a case-sequence comparison against a selected reference trace."""

    _apply_conformance_styles()
    st.markdown(
        """
        <header class="cf-conformance-header">
            <div class="cf-conformance-kicker">Clinical pathway intelligence</div>
            <h1 class="cf-conformance-title">Conformance Analysis</h1>
            <p class="cf-conformance-subtitle">
                Compare observed patient pathways with the expected clinical pathway.
            </p>
        </header>
        """,
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

    case_sequences = build_case_traces(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    if not case_sequences:
        st.info(
            "No complete case pathways were found. Check the case, activity "
            "and timestamp columns for missing or invalid values."
        )
        return

    variant_counts = Counter(pathway for _, pathway in case_sequences)
    variants = sorted(
        variant_counts,
        key=lambda pathway: (-variant_counts[pathway], pathway),
    )[:100]

    with st.container(border=True):
        setup_columns = st.columns([1.5, 1])
        with setup_columns[0]:
            reference_index = st.selectbox(
                "Reference pathway",
                options=range(len(variants)),
                format_func=lambda index: (
                    f"{_format_pathway(variants[index])} "
                    f"({variant_counts[variants[index]]} cases; "
                    f"{len(variants[index])} events)"
                ),
                key="conformance_reference_pathway",
            )
        with setup_columns[1]:
            comparison_mode = st.selectbox(
                "Conformance rule",
                options=[
                    "Exact pathway",
                    "Allow additional activities in order",
                ],
                help=(
                    "Exact pathway requires the observed activities to match "
                    "the reference exactly. Allowing additional activities "
                    "requires all reference activities to occur in order."
                ),
                key="conformance_rule",
            )

    reference = variants[reference_index]
    results_df = conformance_report(
        case_sequences,
        reference,
        allow_additional=(
            comparison_mode == "Allow additional activities in order"
        ),
    )
    conformant_count = int(results_df["Conformance"].eq("Conformant").sum())
    total_cases = len(results_df)
    deviating_count = total_cases - conformant_count
    conformance_rate = conformant_count / total_cases * 100
    deviation_mask = results_df["Conformance"].eq("Deviation")

    deviation_pathways: Counter[tuple[str, ...]] = Counter()
    for (_, pathway), (_, result) in zip(
        case_sequences,
        results_df.iterrows(),
    ):
        if result["Conformance"] == "Deviation":
            deviation_pathways[pathway] += 1
    if deviation_pathways:
        observed_pathway, observed_count = deviation_pathways.most_common(1)[0]
    else:
        observed_pathway, observed_count = variant_counts.most_common(1)[0]

    top_columns = st.columns([0.85, 1.35], gap="medium")
    with top_columns[0]:
        with st.container(border=True):
            st.markdown(
                '<div class="cf-card-heading">Conformance Result</div>'
                '<div class="cf-card-subtitle">Case adherence to the selected pathway</div>',
                unsafe_allow_html=True,
            )
            result_columns = st.columns([1.05, 1])
            with result_columns[0]:
                st.plotly_chart(
                    _build_conformance_chart(conformant_count, total_cases),
                    width="stretch",
                    config={"displayModeBar": False},
                )
            with result_columns[1]:
                st.markdown(
                    f"""
                    <div class="cf-result-stat">
                        <div class="cf-status-line">
                            <span class="cf-status-dot" style="background:#16B7A2"></span>
                            Conforming cases
                        </div>
                        <div class="cf-result-stat-value">
                            {conformant_count:,}
                            <span class="cf-result-stat-label">({conformance_rate:.1f}%)</span>
                        </div>
                    </div>
                    <div class="cf-result-stat">
                        <div class="cf-status-line">
                            <span class="cf-status-dot" style="background:#FF6B61"></span>
                            Deviating cases
                        </div>
                        <div class="cf-result-stat-value">
                            {deviating_count:,}
                            <span class="cf-result-stat-label">
                                ({deviating_count / total_cases * 100:.1f}%)
                            </span>
                        </div>
                    </div>
                    <div class="cf-result-stat">
                        <div class="cf-result-stat-label">Total cases</div>
                        <div class="cf-result-stat-value">{total_cases:,}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with top_columns[1]:
        with st.container(border=True):
            st.markdown(
                '<div class="cf-card-heading">Expected vs Observed Process</div>'
                '<div class="cf-card-subtitle">A representative pathway comparison</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="cf-flow-legend">
                    <span class="cf-flow-expected">Expected Model</span>
                    <span class="cf-flow-observed">Observed Model</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            _render_pathway_row(
                "Expected pathway",
                reference,
                variant_counts[reference],
            )
            _render_pathway_row(
                "Observed pathway",
                observed_pathway,
                observed_count,
            )
            if deviating_count:
                st.caption(
                    "Observed model shows the most frequent pathway among "
                    "deviating cases."
                )
            else:
                st.caption(
                    "All cases conform; the observed model shows the most "
                    "frequent pathway."
                )

    st.markdown("### Top Deviations")
    if deviation_mask.any():
        deviation_counts = results_df.loc[deviation_mask, "Reason"].value_counts()
        example_traces = (
            results_df.loc[deviation_mask]
            .drop_duplicates("Reason")
            .set_index("Reason")["Observed pathway"]
            .to_dict()
        )
        deviations_df = pd.DataFrame(
            [
                {
                    "Deviation Type": reason,
                    "Cases": int(count),
                    "Percentage": f"{count / total_cases * 100:.1f}%",
                    "Example Trace": _format_pathway(
                        tuple(example_traces[reason].split(" → "))
                    ),
                }
                for reason, count in deviation_counts.items()
            ]
        ).head(5)
        st.dataframe(
            deviations_df,
            width="stretch",
            hide_index=True,
        )
    else:
        st.success("All analysed cases conform under the selected rule.")

    with st.expander("Case-level conformance details"):
        st.dataframe(results_df, width="stretch", hide_index=True)
        st.download_button(
            "Download conformance results",
            data=results_df.to_csv(index=False).encode("utf-8"),
            file_name="careflow_conformance_results.csv",
            mime="text/csv",
            key="download_conformance_results",
        )

    variants_df = pd.DataFrame(
        [
            {
                "Observed pathway": " → ".join(pathway),
                "Events": len(pathway),
                "Cases": count,
                "Share (%)": count / total_cases * 100,
            }
            for pathway, count in variant_counts.most_common(20)
        ]
    )
    with st.expander("Most frequent observed pathways"):
        st.dataframe(
            variants_df.round({"Share (%)": 1}),
            width="stretch",
            hide_index=True,
        )
    st.caption(
        "Activities are ordered by timestamp. Ties retain their original row "
        "order. Missing/invalid case IDs, activities and timestamps are "
        "excluded from the comparison. A reference is selected from the 100 "
        "most frequent observed variants, not from a prescribed clinical standard."
    )
