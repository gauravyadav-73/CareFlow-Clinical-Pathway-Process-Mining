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
