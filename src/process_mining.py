"""
CareFlow - Process Mining Specialist backend
============================================
Process discovery and core analytics built on PM4Py.

Input : an event log with columns  case_id, activity, timestamp
        (CSV or XES, as produced by the Data Engineer).
Output: plain pandas DataFrames / dicts / PM4Py models that the Streamlit
        UI (and the Conformance Analyst) can consume directly.

Public API (all functions are import-safe for Streamlit):
    load_event_log(path)                      -> DataFrame
    prepare_log(df)                           -> DataFrame (PM4Py-ready)
    log_summary(df)                           -> dict
    discover_dfg(df)                          -> (dfg, start_acts, end_acts)
    dfg_to_dataframe(dfg)                     -> DataFrame
    save_dfg_image(df, path, variant)         -> path
    discover_inductive_model(df, noise)       -> (net, im, fm)
    save_petri_image(net, im, fm, path)       -> path
    save_process_tree_image(df, path)         -> path
    get_variants(df, top_n)                   -> DataFrame
    case_throughput(df)                       -> DataFrame
    throughput_summary(df)                    -> dict
    activity_waiting_times(df)                -> DataFrame (edge level)
    find_bottlenecks(df, top_n)               -> DataFrame
    filter_log(df, ...)                       -> DataFrame
    run_full_analysis(df, out_dir)            -> dict of results
"""
from __future__ import annotations
import os
import warnings
from typing import Optional

import pandas as pd
import pm4py

warnings.filterwarnings("ignore")

# Standard column names used across the whole project
CASE_COL = "case_id"

# Accepted aliases so the Data Engineer's file works without renaming
_ALIASES = {
        CASE_COL: ["case_id", "case:concept:name", "Case ID", "case", "patient_id", "caseid"],
    ACT_COL: ["activity", "concept:name", "Activity", "event", "task"],
    TS_COL: ["timestamp", "time:timestamp", "Timestamp", "time", "datetime", "start_time"],
}

# --------------------------------------------------------------------------- #
# Loading & preparation
# --------------------------------------------------------------------------- #
def load_event_log(path: str) -> pd.DataFrame:
        """Load a .csv or .xes event log into a clean DataFrame."""
