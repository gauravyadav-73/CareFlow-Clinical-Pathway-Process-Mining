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


def generate(n_cases: int = 500) -> pd.DataFrame:
    pathways = [p for p, _ in VARIANTS]
    weights = [w for _, w in VARIANTS]
    rows = []
    base = datetime(2026, 1, 1, 6, 0)
    for i in range(1, n_cases + 1):
        path = random.choices(pathways, weights)[0]
        t = base + timedelta(days=random.randint(0, 270), minutes=random.randint(0, 16 * 60))
        for step, act in enumerate(path):
            if step > 0:
                mean = WAIT_MIN.get(act, 30)
                t += timedelta(minutes=max(2, random.gauss(mean, mean * 0.35)))
            rows.append({"case_id": f"P{i:04d}", "activity": act, "timestamp": t})
    return pd.DataFrame(rows).sort_values(["case_id", "timestamp"]).reset_index(drop=True)
if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "data", "sample_event_log.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df = generate()
    df.to_csv(out, index=False)
