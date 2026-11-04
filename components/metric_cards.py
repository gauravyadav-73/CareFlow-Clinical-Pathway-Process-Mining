from collections.abc import Sequence

import streamlit as st


Metric = tuple[str, str | int | float | None]


def show_metric_cards(metrics: Sequence[Metric]) -> None:
    """Display a row of Streamlit metric cards."""

    if not metrics:
        return

    columns = st.columns(len(metrics))

    for column, (label, value) in zip(columns, metrics):
        with column:
            st.metric(label=label, value=value)