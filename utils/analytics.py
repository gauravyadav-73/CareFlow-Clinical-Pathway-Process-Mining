import pandas as pd


def prepare_event_log(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> pd.DataFrame:
    """Return valid event rows sorted by case and timestamp."""

    columns = [case_column, activity_column, timestamp_column]
    if len(set(columns)) != 3:
        raise ValueError("Case, activity and timestamp columns must be distinct.")

    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "Missing required event-log columns: "
            + ", ".join(str(column) for column in missing_columns)
        )

    data = df[columns].copy()
    data[timestamp_column] = pd.to_datetime(
        data[timestamp_column],
        errors="coerce",
        utc=True,
    )
    data = data.dropna(subset=columns)
    data[activity_column] = data[activity_column].astype(str)
    return data.sort_values(
        [case_column, timestamp_column],
        kind="mergesort",
    )


def activity_frequency(
    df: pd.DataFrame,
    activity_column: str,
) -> pd.DataFrame:
    """Count non-null events per activity, most frequent first."""

    if activity_column not in df.columns:
        raise ValueError(f"Activity column '{activity_column}' was not found.")

    return (
        df[activity_column]
        .dropna()
        .astype(str)
        .value_counts()
        .rename_axis("Activity")
        .reset_index(name="Events")
    )


def calculate_event_gaps(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> pd.DataFrame:
    """Calculate time between consecutive events, attributed to the earlier event."""

    data = prepare_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    if data.empty:
        return data.assign(
            **{
                "Next Activity": pd.Series(dtype="object"),
                "Next Timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
                "Elapsed Hours": pd.Series(dtype="float64"),
            }
        )

    grouped = data.groupby(case_column, sort=False)
    data["Next Activity"] = grouped[activity_column].shift(-1)
    data["Next Timestamp"] = grouped[timestamp_column].shift(-1)
    data["Elapsed Hours"] = (
        data["Next Timestamp"] - data[timestamp_column]
    ).dt.total_seconds() / 3600
    return data.dropna(subset=["Elapsed Hours"]).copy()


def summarize_activity_gaps(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> pd.DataFrame:
    """Summarize consecutive-event gaps by the preceding activity."""

    gaps = calculate_event_gaps(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    summary_columns = [
        "Preceding activity",
        "Average gap (hours)",
        "Median gap (hours)",
        "90th percentile gap (hours)",
        "Total gap (hours)",
        "Transitions",
        "Cases",
    ]
    if gaps.empty:
        return pd.DataFrame(columns=summary_columns)

    summary = (
        gaps.groupby(activity_column, observed=True)
        .agg(
            **{
                "Average gap (hours)": ("Elapsed Hours", "mean"),
                "Median gap (hours)": ("Elapsed Hours", "median"),
                "90th percentile gap (hours)": (
                    "Elapsed Hours",
                    lambda values: values.quantile(0.9),
                ),
                "Total gap (hours)": ("Elapsed Hours", "sum"),
                "Transitions": ("Elapsed Hours", "size"),
                "Cases": (case_column, "nunique"),
            }
        )
        .reset_index()
        .rename(columns={activity_column: "Preceding activity"})
        .sort_values("Average gap (hours)", ascending=False, kind="mergesort")
    )
    return summary[summary_columns].reset_index(drop=True)


def summarize_pathway_variants(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> pd.DataFrame:
    """Count distinct chronological activity sequences across valid cases."""

    data = prepare_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    columns = ["Pathway", "Events", "Cases", "Share (%)"]
    if data.empty:
        return pd.DataFrame(columns=columns)

    case_pathways = (
        data.groupby(case_column, sort=False)[activity_column]
        .agg(tuple)
    )
    counts = case_pathways.value_counts(sort=True)
    total_cases = int(counts.sum())
    rows = [
        {
            "Pathway": " → ".join(pathway),
            "Events": len(pathway),
            "Cases": int(count),
            "Share (%)": int(count) / total_cases * 100,
        }
        for pathway, count in counts.items()
    ]
    return pd.DataFrame(rows, columns=columns)


def describe_event_log(
    df: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> dict[str, int | float | pd.Timestamp | None]:
    """Calculate key event-log counts and timestamp coverage."""

    data = prepare_event_log(
        df,
        case_column,
        activity_column,
        timestamp_column,
    )
    timestamps = data[timestamp_column]
    return {
        "total_events": len(df),
        "valid_events": len(data),
        "cases": int(data[case_column].nunique()),
        "activities": int(data[activity_column].nunique()),
        "transitions": int(
            data.groupby(case_column, sort=False).size().sub(1).clip(lower=0).sum()
        ),
        "first_timestamp": timestamps.min() if not timestamps.empty else None,
        "last_timestamp": timestamps.max() if not timestamps.empty else None,
    }