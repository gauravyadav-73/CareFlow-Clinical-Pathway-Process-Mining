import pandas as pd


def load_csv(uploaded_file):
    """Load an uploaded CSV file safely."""

    try:
        df = pd.read_csv(uploaded_file)

        # Remove accidental spaces from column names.
        df.columns = df.columns.astype(str).str.strip()

        if df.empty:
            return None, "The uploaded CSV contains no records."

        if len(df.columns) == 0:
            return None, "The CSV does not contain any columns."

        return df, None

    except Exception as error:
        return None, f"Unable to read the CSV file: {error}"


def validate_event_log(df, case_column, activity_column, timestamp_column):
    """
    Validate the minimum columns needed for clinical
    process-mining event logs.
    """

    issues = []

    required_columns = [
        case_column,
        activity_column,
        timestamp_column,
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        return {
            "valid": False,
            "issues": [
                f"Missing required column: {column}"
                for column in missing_columns
            ],
            "data": df.copy(),
        }

    validated_df = df.copy()

    # Check missing case IDs.
    missing_cases = validated_df[case_column].isna().sum()

    if missing_cases:
        issues.append(
            f"{missing_cases} records have missing Case IDs."
        )

    # Check missing activity names.
    missing_activities = (
        validated_df[activity_column].isna().sum()
    )

    if missing_activities:
        issues.append(
            f"{missing_activities} records have missing activities."
        )

    # Convert timestamps to datetime.
    original_timestamps = validated_df[timestamp_column].copy()

    validated_df[timestamp_column] = pd.to_datetime(
        original_timestamps,
        errors="coerce",
        utc=True,
    )

    invalid_timestamps = (
        original_timestamps.notna()
        & validated_df[timestamp_column].isna()
    ).sum()

    missing_timestamps = original_timestamps.isna().sum()

    if missing_timestamps:
        issues.append(
            f"{missing_timestamps} records have missing timestamps."
        )

    if invalid_timestamps:
        issues.append(
            f"{invalid_timestamps} records have invalid timestamps."
        )

    # Count duplicate events without deleting them.
    duplicate_events = validated_df.duplicated(
        subset=required_columns
    ).sum()

    if duplicate_events:
        issues.append(
            f"{duplicate_events} potential duplicate events detected."
        )

    # Determine whether the event log meets minimum requirements.
    valid_rows = validated_df[
        validated_df[case_column].notna()
        & validated_df[activity_column].notna()
        & validated_df[timestamp_column].notna()
    ]

    return {
        "valid": len(valid_rows) > 0,
        "issues": issues,
        "data": validated_df,
        "valid_rows": valid_rows,
        "total_records": len(validated_df),
        "valid_records": len(valid_rows),
        "unique_cases": valid_rows[case_column].nunique(),
        "unique_activities": valid_rows[activity_column].nunique(),
        "duplicate_events": int(duplicate_events),
    }