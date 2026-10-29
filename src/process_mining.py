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
        ext = os.path.splitext(path)[1].lower()
        if ext == ".xes" or path.lower().endswith(".xes.gz"):
                df = pm4py.convert_to_dataframe(pm4py.read_xes(path))
        elif ext == ".csv":
                df = pd.read_csv(path)
        else:
                raise ValueError(f"Unsupported file type: {ext} (use .csv or .xes)")
        return prepare_log(df)
def prepare_log(df: pd.DataFrame) -> pd.DataFrame:
        """Normalise column names, parse timestamps, sort, and add PM4Py columns."""
        df = df.copy()
        rename = {}
        for std, options in _ALIASES.items():
                for opt in options:
                        if opt in df.columns:
                                rename[opt] = std
                                break
        df = df.rename(columns=rename)
        missing = [c for c in (CASE_COL, ACT_COL, TS_COL) if c not in df.columns]
        if missing:
                raise ValueError(
                        f"Event log is missing required columns: {missing}. "
                        f"Found: {list(df.columns)}"
                )
        df[CASE_COL] = df[CASE_COL].astype(str)
        df[ACT_COL] = df[ACT_COL].astype(str).str.strip()
        df[TS_COL] = pd.to_datetime(df[TS_COL], errors="coerce", utc=True).dt.tz_localize(None)
        df = df.dropna(subset=[CASE_COL, ACT_COL, TS_COL])
        df = df.sort_values([CASE_COL, TS_COL], kind="mergesort").reset_index(drop=True)

        # PM4Py's expected column names
        df["case:concept:name"] = df[CASE_COL]
        df["concept:name"] = df[ACT_COL]
        df["time:timestamp"] = df[TS_COL]
        return df

def log_summary(df: pd.DataFrame) -> dict:
        """Headline statistics for the dashboard's overview cards."""
        return {
                "num_cases": int(df[CASE_COL].nunique()),
                "num_events": int(len(df)),
                "num_activities": int(df[ACT_COL].nunique()),
                "num_variants": int(len(pm4py.get_variants(df))),
                "start_date": df[TS_COL].min(),
                "end_date": df[TS_COL].max(),
                "activities": sorted(df[ACT_COL].unique().tolist()),
        }

# --------------------------------------------------------------------------- #
# Process discovery
# --------------------------------------------------------------------------- #

def discover_dfg(df: pd.DataFrame):
        """Frequency Directly-Follows Graph.

        Returns (dfg, start_activities, end_activities) where dfg is
        {(from_activity, to_activity): count}.
    """
        dfg, start, end = pm4py.discover_dfg(df)
        return dict(dfg), dict(start), dict(end)


def dfg_to_dataframe(dfg: dict) -> pd.DataFrame:
