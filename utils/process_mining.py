from collections import Counter
from typing import Any

import pandas as pd

from utils.analytics import prepare_event_log


def build_case_traces(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> list[tuple[Any, tuple[str, ...]]]:
    """Build each valid case's activity trace in timestamp order."""

    data = prepare_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    return [
        (case_id, tuple(events[activity_column].tolist()))
        for case_id, events in data.groupby(case_column, sort=False)
    ]


def discover_transitions(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
    max_steps: int | None = None,
) -> tuple[Counter, Counter]:
    """Count sequence-position transitions and truncated pathway variants."""

    if max_steps is not None and max_steps < 1:
        raise ValueError("max_steps must be a positive integer.")

    traces = build_case_traces(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    transitions: Counter = Counter()
    pathways: Counter = Counter()

    for _, trace in traces:
        activities = trace[:max_steps] if max_steps is not None else trace
        if not activities:
            continue
        pathways[activities] += 1
        for index, (source, target) in enumerate(
            zip(activities, activities[1:])
        ):
            transitions[((source, index), (target, index + 1))] += 1

    return transitions, pathways


def compare_traces(
    first: tuple[str, ...],
    second: tuple[str, ...],
) -> pd.DataFrame:
    """Align two activity traces by sequence position."""

    rows = []
    for index in range(max(len(first), len(second))):
        activity_a = first[index] if index < len(first) else "—"
        activity_b = second[index] if index < len(second) else "—"
        rows.append(
            {
                "Step": index + 1,
                "Pathway A": activity_a,
                "Pathway B": activity_b,
                "Match": "Yes" if activity_a == activity_b else "No",
            }
        )
    return pd.DataFrame(
        rows,
        columns=["Step", "Pathway A", "Pathway B", "Match"],
    )


def compare_to_reference(
    reference: tuple[str, ...],
    observed: tuple[str, ...],
    allow_additional: bool = False,
) -> dict[str, object]:
    """Compare a case trace to a reference, preserving activity order."""

    missing: list[str] = []
    additional: list[str] = []
    matched_positions: set[int] = set()
    cursor = 0
    for activity in reference:
        try:
            position = observed.index(activity, cursor)
        except ValueError:
            missing.append(activity)
            continue
        matched_positions.add(position)
        cursor = position + 1

    additional = [
        activity
        for index, activity in enumerate(observed)
        if index not in matched_positions
    ]
    exact = observed == reference
    ordered_match = not missing
    conforms = ordered_match if allow_additional else exact

    if exact:
        reason = "Matches the reference pathway"
    elif missing:
        reason = "Missing or out-of-order reference activities"
    elif additional:
        reason = "Contains additional activities"
    else:
        reason = "Differs from the reference pathway"

    return {
        "conforms": conforms,
        "exact_match": exact,
        "ordered_match": ordered_match,
        "missing_activities": missing,
        "additional_activities": additional,
        "reason": reason,
    }


def conformance_report(
    cases: list[tuple[Any, tuple[str, ...]]],
    reference: tuple[str, ...],
    allow_additional: bool = False,
) -> pd.DataFrame:
    """Return case-level conformance results against one reference trace."""

    rows = []
    for case_id, observed in cases:
        comparison = compare_to_reference(
            reference,
            observed,
            allow_additional=allow_additional,
        )
        rows.append(
            {
                "Case ID": str(case_id),
                "Events": len(observed),
                "Conformance": (
                    "Conformant" if comparison["conforms"] else "Deviation"
                ),
                "Reason": comparison["reason"],
                "Observed pathway": " → ".join(observed),
                "Missing / out-of-order activities": (
                    " → ".join(comparison["missing_activities"]) or "—"
                ),
                "Additional activities": (
                    " → ".join(comparison["additional_activities"]) or "—"
                ),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Case ID",
            "Events",
            "Conformance",
            "Reason",
            "Observed pathway",
            "Missing / out-of-order activities",
            "Additional activities",
        ],
    )