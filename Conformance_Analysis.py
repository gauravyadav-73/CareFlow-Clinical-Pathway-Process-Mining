"""
CareFlow - Clinical Pathway Process Mining

What this module does
---------------------
1. Defines the ideal (standard) clinical pathway as a process tree / Petri net.
2. Runs PM4Py token-based replay conformance checking: actual vs. standard.
3. Runs explainable rule-based deviation checks (missing, out-of-order, repeated steps).
4. Finds delay drivers (which transitions are slowest, and slower for deviating cases).
5. Produces plain-English insights + tidy DataFrames the Streamlit UI can display.
Input: an event log DataFrame/CSV with columns
    case_id, activity, timestamp
(column names are configurable, see load_event_log).

Usage from the dashboard (UI Lead):
    from conformance_analysis import load_event_log, run_conformance_analysis
    df = load_event_log("data/event_log.csv")
    result = run_conformance_analysis(df)
    result.summary            # dict of headline KPIs
    result.case_table         # per-case fitness + deviations
    result.deviation_summary  # deviation type counts
    result.delay_table        # slowest transitions
    result.insights           # list[str] ready for the UI

Command line demo:
    python conformance_analysis.py --demo
    python conformance_analysis.py --input data/event_log.csv --output outputs/
"""

from __future__ import annotations

import argparse
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd
import pm4py

# --------------------------------------------------------------------------
# 1. STANDARD CLINICAL PATHWAY (edit this section to match your guidelines)
# --------------------------------------------------------------------------

# Process-tree notation:  ->  sequence,  X  exclusive choice,  +  parallel,  tau = skip
STANDARD_PATHWAY_TREE = (
    "->('Admission','Triage','Doctor Consultation',"
    "X('Lab Test','X-Ray','Lab Test and X-Ray' ,tau),"
    "'Treatment','Discharge')"
)

# NOTE: the line above keeps the parser simple. 'Lab Test and X-Ray' is not an
# activity in the log; it just shows how extra branches could be added.
# Order of the mandatory steps. Used by the rule-based checks.
MANDATORY_STEPS = ["Admission", "Triage", "Doctor Consultation", "Treatment", "Discharge"]

# Expected maximum waiting time (hours) between consecutive steps (clinical targets).
# Anything above the target counts as a delay violation.
WAIT_TARGET_HOURS = {
    ("Admission", "Triage"): 0.5,
    ("Triage", "Doctor Consultation"): 1.0,
    ("Doctor Consultation", "Lab Test"): 1.0,
    ("Doctor Consultation", "X-Ray"): 1.0,
    ("Lab Test", "Treatment"): 2.0,
    ("X-Ray", "Treatment"): 2.0,
    ("Doctor Consultation", "Treatment"): 1.5,
    ("Treatment", "Discharge"): 3.0,
}

# Column names after PM4Py formatting
CASE, ACT, TS = "case:concept:name", "concept:name", "time:timestamp"

# --------------------------------------------------------------------------
# 2. LOADING
# --------------------------------------------------------------------------
def load_event_log(
    source,
    case_col: str = "case_id",
    activity_col: str = "activity",
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """Load a CSV path or DataFrame into PM4Py's standard event-log format."""
    df = pd.read_csv(source) if isinstance(source, (str, os.PathLike)) else source.copy()
    df = df.rename(columns={case_col: "case_id", activity_col: "activity", timestamp_col: "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["case_id", "activity", "timestamp"])
    df["case_id"] = df["case_id"].astype(str)
    df["activity"] = df["activity"].astype(str).str.strip()
    df = pm4py.format_dataframe(
        df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )
    return df.sort_values([CASE, TS]).reset_index(drop=True)


# --------------------------------------------------------------------------
# 3. CONFORMANCE CHECKING (PM4Py token-based replay)
# --------------------------------------------------------------------------

def build_standard_model():
    """Return (petri_net, initial_marking, final_marking) for the standard pathway."""
    tree = pm4py.parse_process_tree(STANDARD_PATHWAY_TREE)
    return pm4py.convert_to_petri_net(tree)


def token_replay(df: pd.DataFrame, net, im, fm) -> pd.DataFrame:
    """Replay every case on the standard model. Returns one row per case."""
    log = pm4py.convert_to_event_log(df)
    diagnostics = pm4py.conformance_diagnostics_token_based_replay(log, net, im, fm)
    rows = []
    for trace, d in zip(log, diagnostics):
        rows.append(
            {
                "case_id": trace.attributes["concept:name"],
                "fitness": round(d["trace_fitness"], 4),
                "is_fit": bool(d["trace_is_fit"]),
                "missing_tokens": d["missing_tokens"],
                "remaining_tokens": d["remaining_tokens"],
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 4. RULE-BASED DEVIATION DETECTION (explainable for clinicians)
# --------------------------------------------------------------------------

def detect_deviations(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (case, deviation) with type and description."""
    out = []
    for case_id, g in df.groupby(CASE):
        acts = g[ACT].tolist()

        # Missing mandatory steps
        for step in MANDATORY_STEPS:
            if step not in acts:
                out.append((case_id, "Missing step", f"'{step}' never happened"))
    # Wrong order: check each pair of mandatory steps that both occurred
    first_pos = {a: acts.index(a) for a in MANDATORY_STEPS if a in acts}
    for i, a in enumerate(MANDATORY_STEPS):
        for b in MANDATORY_STEPS[i + 1:]:
            if a in first_pos and b in first_pos and first_pos[a] > first_pos[b]:
