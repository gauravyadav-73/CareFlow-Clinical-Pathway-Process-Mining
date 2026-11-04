import pandas as pd

from utils.analytics import describe_event_log, summarize_activity_gaps


def generate_event_log_insights(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> list[str]:
    """Generate factual, descriptive insights from a mapped event log."""

    metrics = describe_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    if not metrics["valid_events"]:
        return ["No events with complete case, activity and timestamp values were found."]

    insights = [
        (
            f"{metrics['valid_events']:,} of {metrics['total_events']:,} "
            "records have a valid case, activity and timestamp."
        ),
        (
            f"The event log contains {metrics['cases']:,} cases and "
            f"{metrics['activities']:,} distinct activities."
        ),
        f"The valid event log contains {metrics['transitions']:,} consecutive-event transitions.",
    ]

    if metrics["first_timestamp"] is not None:
        insights.append(
            "Valid events range from "
            f"{metrics['first_timestamp']} to {metrics['last_timestamp']}."
        )

    frequencies = (
        df[activity_column]
        .dropna()
        .astype(str)
        .value_counts()
    )
    if not frequencies.empty:
        insights.append(
            f"'{frequencies.index[0]}' is the most frequently recorded "
            f"activity ({int(frequencies.iloc[0]):,} events)."
        )

    return insights


def generate_gap_insights(summary: pd.DataFrame) -> list[str]:
    """Describe the largest observed event gaps without asserting causation."""

    if summary.empty:
        return ["There are not enough consecutive valid events to summarize gaps."]

    longest_average = summary.sort_values(
        "Average gap (hours)",
        ascending=False,
        kind="mergesort",
    ).iloc[0]
    most_transitions = summary.sort_values(
        ["Transitions", "Average gap (hours)"],
        ascending=[False, False],
        kind="mergesort",
    ).iloc[0]

    insights = [
        (
            f"The largest average gap follows '{longest_average['Preceding activity']}' "
            f"({longest_average['Average gap (hours)']:.2f} hours across "
            f"{int(longest_average['Transitions']):,} transitions)."
        ),
        (
            f"'{most_transitions['Preceding activity']}' has the most observed "
            f"transitions ({int(most_transitions['Transitions']):,})."
        ),
    ]
    return insights


def event_log_gap_insights(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> list[str]:
    """Calculate event-gap summaries and return their descriptive insights."""

    summary = summarize_activity_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    return generate_gap_insights(summary)