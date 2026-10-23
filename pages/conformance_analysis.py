from bisect import bisect_left
from collections import Counter, defaultdict

import pandas as pd
import streamlit as st


def _activity_sequences(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> list[tuple[object, tuple[str, ...]]]:
    """Build chronologically ordered activity sequences for valid cases."""

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
        return []

    data[activity_column] = data[activity_column].astype(str)
    data = data.sort_values(
        [case_column, timestamp_column],
        kind="mergesort",
    )
    return [
        (case_id, tuple(events[activity_column].tolist()))
        for case_id, events in data.groupby(case_column, sort=False)
    ]


def _pathway_diff(
    expected: tuple[str, ...],
    observed: tuple[str, ...],
) -> tuple[list[str], list[str], bool]:
    """Find expected activities missing in order and unmatched observed ones."""

    observed_positions: dict[str, list[int]] = defaultdict(list)
    for index, activity in enumerate(observed):
        observed_positions[activity].append(index)

    matched_positions: set[int] = set()
    missing: list[str] = []
    cursor = 0
    for activity in expected:
        positions = observed_positions.get(activity, [])
        position_index = bisect_left(positions, cursor)
        if position_index == len(positions):
            missing.append(activity)
            continue

        matched_position = positions[position_index]
        matched_positions.add(matched_position)
        cursor = matched_position + 1

    additional = [
        activity
        for index, activity in enumerate(observed)
        if index not in matched_positions
    ]
    is_ordered_subsequence = not missing
    return missing, additional, is_ordered_subsequence


def _format_pathway(pathway: tuple[str, ...], max_length: int = 90) -> str:
    text = " → ".join(pathway)
    if len(text) > max_length:
        return text[: max_length - 1] + "…"
    return text


def render_conformance_analysis(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render a case-sequence comparison against a selected reference trace."""

    st.title("Conformance Analysis")
    st.write(
        "Compare observed case pathways with a reference pathway and review "
        "missing, out-of-order and additional activities."
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

    case_sequences = _activity_sequences(
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

    st.caption(
        "Reference pathways are selected from the 100 most frequent observed "
        "pathway variants. A reference may be any observed variant in this list."
    )
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
    reference = variants[reference_index]

    comparison_mode = st.radio(
        "Conformance rule",
        options=[
            "Exact pathway",
            "Allow additional activities in order",
        ],
        horizontal=True,
        help=(
            "Exact pathway requires the observed activities to match the "
            "reference exactly. The second rule accepts extra activities, "
            "but all reference activities must still occur in order."
        ),
        key="conformance_rule",
    )

    results: list[dict[str, object]] = []
    for case_id, observed in case_sequences:
        missing, additional, is_subsequence = _pathway_diff(reference, observed)
        is_exact = observed == reference
        conforms = (
            is_exact
            if comparison_mode == "Exact pathway"
            else is_subsequence
        )
        results.append(
            {
                "Case ID": str(case_id),
                "Events": len(observed),
                "Conformance": "Conformant" if conforms else "Deviation",
                "Observed pathway": " → ".join(observed),
                "Missing / out-of-order activities": " → ".join(missing) or "—",
                "Additional activities": " → ".join(additional) or "—",
            }
        )

    results_df = pd.DataFrame(results)
    conformant_count = int(results_df["Conformance"].eq("Conformant").sum())
    total_cases = len(results_df)
    conformance_rate = conformant_count / total_cases * 100

    metric_columns = st.columns(4)
    metric_columns[0].metric("Cases analysed", f"{total_cases:,}")
    metric_columns[1].metric("Conformant cases", f"{conformant_count:,}")
    metric_columns[2].metric("Conformance rate", f"{conformance_rate:.1f}%")
    metric_columns[3].metric("Observed variants", f"{len(variant_counts):,}")

    if conformant_count == total_cases:
        st.success("All analysed cases conform under the selected rule.")
    else:
        st.warning(
            f"{total_cases - conformant_count:,} cases deviate from the "
            "selected reference pathway under the selected rule."
        )

    st.subheader("Case-level conformance")
    st.dataframe(results_df, use_container_width=True, hide_index=True)
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
    st.subheader("Most frequent observed pathways")
    st.dataframe(
        variants_df.round({"Share (%)": 1}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Activities are ordered by timestamp. Ties retain their original row "
        "order. Missing/invalid case IDs, activities and timestamps are "
        "excluded from the comparison."
    )