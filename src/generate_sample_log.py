"""
Synthetic clinical event log generator (stand-in until the Data Engineer
delivers the real file).  Produces data/sample_event_log.csv with columns:
    case_id, activity, timestamp

Includes realistic variants, a deliberate triage->doctor bottleneck, and some
protocol deviations (skipped triage, repeated lab tests, delayed discharge).
"""
import os
import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(42)

# (pathway, probability weight)
VARIANTS = [
    (["Patient Admission", "Triage", "Doctor Consultation", "Lab Test", "Treatment", "Discharge"], 40),
    (["Patient Admission", "Triage", "Doctor Consultation", "Treatment", "Discharge"], 20),
    (["Patient Admission", "Triage", "Doctor Consultation", "Lab Test", "Imaging", "Treatment", "Discharge"], 15),
    (["Patient Admission", "Triage", "Doctor Consultation", "Lab Test", "Treatment", "Re-assessment", "Treatment", "Discharge"], 8),
    (["Patient Admission", "Doctor Consultation", "Lab Test", "Treatment", "Discharge"], 6),  # skipped triage
    (["Patient Admission", "Triage", "Doctor Consultation", "Lab Test", "Lab Test", "Treatment", "Discharge"], 5),  # repeated lab
    (["Patient Admission", "Triage", "Doctor Consultation", "Lab Test", "Surgery", "ICU Stay", "Treatment", "Discharge"], 4),
    (["Patient Admission", "Triage", "Doctor Consultation", "Treatment", "Discharge", "Readmission"], 2),
]

# mean waiting time in minutes before an activity occurs (key = activity)
WAIT_MIN = {
    "Triage": 15,
    "Doctor Consultation": 75,   # bottleneck: long wait after triage
    "Lab Test": 35,
    "Imaging": 50,
    "Treatment": 40,
    "Re-assessment": 60,
    "Surgery": 120,
    "ICU Stay": 45,
    "Discharge": 90,             # delayed discharge paperwork
    "Readmission": 2000,
}
