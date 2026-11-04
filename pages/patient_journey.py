from html import escape

import pandas as pd
import streamlit as st


_CASE_KEY = "patient_journey_case"
_ACTIVITY_COLORS = (
    "#3B82F6",
    "#8B5CF6",
    "#F59E0B",
    "#EF4444",
    "#14B8A6",
    "#EC4899",
)


def _navigate_case(case_ids: list, offset: int) -> None:
    """Move the case selector by one item, wrapping at either end."""

    selected_case = st.session_state.get(_CASE_KEY, case_ids[0])
    try:
        selected_index = case_ids.index(selected_case)
    except ValueError:
        selected_index = 0
    st.session_state[_CASE_KEY] = case_ids[
        (selected_index + offset) % len(case_ids)
    ]


def _format_duration(hours: float) -> str:
    total_minutes = max(0, round(hours * 60))
    days, remaining_minutes = divmod(total_minutes, 24 * 60)
    whole_hours, minutes = divmod(remaining_minutes, 60)
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if whole_hours:
        parts.append(f"{whole_hours} hour{'s' if whole_hours != 1 else ''}")
    if minutes or not parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts)


def _format_gap(hours: float) -> str:
    total_minutes = max(0, round(hours * 60))
    days, remaining_minutes = divmod(total_minutes, 24 * 60)
    whole_hours, minutes = divmod(remaining_minutes, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if whole_hours:
        parts.append(f"{whole_hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def _render_timeline(
    journey: pd.DataFrame,
    activity_column: str,
    timestamp_column: str,
) -> None:
    events = []
    for index, (_, event) in enumerate(journey.iterrows()):
        color = _ACTIVITY_COLORS[index % len(_ACTIVITY_COLORS)]
        timestamp = event[timestamp_column].strftime("%b %d, %Y · %H:%M")
        gap_hours = event["Hours since previous event"]
        gap = (
            "Start of journey"
            if pd.isna(gap_hours)
            else f"+{_format_gap(gap_hours)}"
        )
        events.append(
            '<div class="cf-journey-event">'
            f'<div class="cf-journey-marker" style="--event-color:{color}">'
            f"{index + 1}</div>"
            '<div class="cf-journey-event-content">'
            '<div class="cf-journey-event-meta">'
            f"<time>{escape(timestamp)}</time>"
            f'<span class="cf-journey-gap">{escape(gap)}</span>'
            "</div>"
            f'<div class="cf-journey-activity">{escape(str(event[activity_column]))}</div>'
            "</div></div>"
        )

    st.markdown(
        """
        <style>
        .cf-journey-timeline { padding: 4px 2px 2px 10px; }
        .cf-journey-event {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            min-height: 66px;
            border-left: 2px solid #DCE7F3;
            padding: 0 0 18px 0;
            margin-left: 13px;
        }
        .cf-journey-event:last-child {
            border-left-color: transparent;
            min-height: 40px;
            padding-bottom: 0;
        }
        .cf-journey-marker {
            display: flex;
            flex: 0 0 28px;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            margin-left: -15px;
            border: 2px solid var(--event-color);
            border-radius: 50%;
            background: #FFFFFF;
            color: var(--event-color);
            font-size: 11px;
            font-weight: 700;
        }
        .cf-journey-event-content { min-width: 0; padding: 1px 0 0; }
        .cf-journey-event-meta {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 7px;
            color: #64748B;
            font-size: 11px;
        }
        .cf-journey-gap {
            padding: 2px 7px;
            border-radius: 999px;
            background: #F1F5F9;
            color: #475569;
            font-size: 10px;
        }
        .cf-journey-activity {
            margin-top: 4px;
            color: #172B4D;
            font-size: 13px;
            font-weight: 650;
            overflow-wrap: anywhere;
        }
        </style>
        <div class="cf-journey-timeline">
        """
        + "".join(events)
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_journey_path(journey: pd.DataFrame, activity_column: str) -> None:
    steps = []
    for index, activity in enumerate(journey[activity_column]):
        color = _ACTIVITY_COLORS[index % len(_ACTIVITY_COLORS)]
        steps.append(
            '<span class="cf-journey-step">'
            f'<span class="cf-journey-step-dot" style="--event-color:{color}"></span>'
            f"{escape(str(activity))}</span>"
        )

    st.markdown(
        '<div class="cf-journey-path">'
        + '<span class="cf-journey-arrow">→</span>'.join(steps)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_patient_journey(
    df: pd.DataFrame | None,
    case_column: str | None,
    activity_column: str | None,
    timestamp_column: str | None,
) -> None:
    """Render a case explorer with an event timeline and journey details."""

    st.title("Case Explorer")
    st.write("Explore individual patient journeys and activity timelines.")

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
    data = data.dropna(subset=[case_column, activity_column, timestamp_column])
    if data.empty:
        st.info(
            "No events with valid case IDs, activities and timestamps were found."
        )
        return

    data[activity_column] = data[activity_column].astype(str)
    data = data.sort_values(timestamp_column, kind="mergesort")
    case_ids = data[case_column].drop_duplicates().tolist()

    if st.session_state.get(_CASE_KEY) not in case_ids:
        st.session_state[_CASE_KEY] = case_ids[0]

    case_col, view_col, previous_col, next_col = st.columns(
        [1.55, 1.15, 0.75, 0.75],
        vertical_alignment="bottom",
    )
    with case_col:
        selected_case = st.selectbox(
            "Select Case ID",
            options=case_ids,
            format_func=str,
            key=_CASE_KEY,
        )
    with view_col:
        view = st.selectbox(
            "View",
            options=("Timeline View", "Event Table"),
            key="patient_journey_view",
        )
    with previous_col:
        st.button(
            "← Previous",
            use_container_width=True,
            on_click=_navigate_case,
            args=(case_ids, -1),
            key="patient_journey_previous",
        )
    with next_col:
        st.button(
            "Next →",
            type="primary",
            use_container_width=True,
            on_click=_navigate_case,
            args=(case_ids, 1),
            key="patient_journey_next",
        )

    journey = data[data[case_column] == selected_case].copy()
    journey = journey.sort_values(timestamp_column, kind="mergesort")
    journey["Event number"] = range(1, len(journey) + 1)
    journey["Hours since previous event"] = (
        journey[timestamp_column].diff().dt.total_seconds() / 3600
    )

    duration_hours = (
        journey[timestamp_column].iloc[-1]
        - journey[timestamp_column].iloc[0]
    ).total_seconds() / 3600
    sequence = tuple(journey[activity_column])
    variants = {}
    for case_id, case_events in data.groupby(case_column, sort=False):
        case_sequence = tuple(case_events[activity_column])
        variants.setdefault(case_sequence, len(variants) + 1)
    variant = f"Variant {variants[sequence]}"

    st.markdown(
        """
        <style>
        .cf-case-details { margin: 0; }
        .cf-case-detail {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 11px 0;
            border-bottom: 1px solid #E8EEF5;
            font-size: 12px;
        }
        .cf-case-detail:last-child { border-bottom: 0; }
        .cf-case-detail dt { color: #64748B; }
        .cf-case-detail dd {
            margin: 0;
            color: #172B4D;
            font-weight: 650;
            text-align: right;
            overflow-wrap: anywhere;
        }
        .cf-journey-path {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 7px;
            padding: 8px 0 3px;
        }
        .cf-journey-step {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 10px;
            border: 1px solid #DFE8F2;
            border-radius: 999px;
            background: #FFFFFF;
            color: #172B4D;
            font-size: 11px;
            font-weight: 600;
        }
        .cf-journey-step-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--event-color);
        }
        .cf-journey-arrow { color: #94A3B8; font-size: 13px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    timeline_col, details_col = st.columns([1.2, 0.9], gap="medium")
    with timeline_col:
        with st.container(border=True):
            st.subheader("Case Timeline")
            st.caption(f"{len(journey):,} recorded events, in timestamp order")
            if view == "Timeline View":
                _render_timeline(journey, activity_column, timestamp_column)
            else:
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
                    displayed_journey.round(
                        {"Hours since previous event": 2}
                    ),
                    width="stretch",
                    hide_index=True,
                )

    with details_col:
        with st.container(border=True):
            st.subheader("Case Details")
            details = (
                ("Case ID", escape(str(selected_case))),
                ("Total Duration", _format_duration(duration_hours)),
                ("Total Activities", f"{len(journey):,}"),
                ("Distinct Activities", f"{journey[activity_column].nunique():,}"),
                ("Variant", variant),
                ("Status", "Recorded"),
            )
            st.markdown(
                '<dl class="cf-case-details">'
                + "".join(
                    '<div class="cf-case-detail">'
                    f"<dt>{label}</dt><dd>{value}</dd></div>"
                    for label, value in details
                )
                + "</dl>",
                unsafe_allow_html=True,
            )
            st.download_button(
                "Download journey events",
                data=journey[
                    [
                        "Event number",
                        activity_column,
                        timestamp_column,
                        "Hours since previous event",
                    ]
                ]
                .rename(
                    columns={
                        activity_column: "Activity",
                        timestamp_column: "Timestamp (UTC)",
                    }
                )
                .to_csv(index=False)
                .encode("utf-8"),
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
                use_container_width=True,
            )

    with st.container(border=True):
        st.subheader("Journey Visualization")
        _render_journey_path(journey, activity_column)

    st.caption(
        "Journey duration and event gaps are calculated from recorded "
        "timestamps; they do not represent active treatment or queue time."
    )
