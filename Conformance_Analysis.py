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

