"""
Self-test for process_mining_backend.py.
Generates a synthetic clinical event log (if no CSV is given) and exercises every feature.

Run:  python test_backend.py            (synthetic data)
      python test_backend.py my_log.csv (your Data Engineer's file)
"""

import random
import sys
from datetime import datetime, timedelta

import pandas as pd

from process_mining_backend import ProcessMiner, load_event_log, CASE, ACT


def generate_sample_log(n_cases: int = 300, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)
    rows = []
    start = datetime(2026, 1, 1, 6, 0)
    for i in range(1, n_cases + 1):
        cid = f"P{i:04d}"
        t = start + timedelta(hours=random.uniform(0, 24 * 60))
        path = ["Admission", "Triage"]
        r = random.random()
        if r < 0.55:
            path += ["Doctor Consultation", "Lab Test", "Treatment", "Discharge"]
        elif r < 0.75:
            path += ["Doctor Consultation", "Lab Test", "Imaging", "Treatment", "Discharge"]
        elif r < 0.88:
            path += ["Doctor Consultation", "Treatment", "Discharge"]
        elif r < 0.95:
            path += ["Doctor Consultation", "Lab Test", "Lab Test", "Treatment", "Discharge"]
        else:
            path += ["Doctor Consultation", "Surgery", "Recovery", "Discharge"]
        gaps = {  # mean minutes waited before each activity
            "Triage": 15, "Doctor Consultation": 45, "Lab Test": 30, "Imaging": 120,
            "Treatment": 90, "Surgery": 240, "Recovery": 300, "Discharge": 60,
        }
        for act in path:
            if act != "Admission":
                t += timedelta(minutes=random.expovariate(1 / gaps.get(act, 30)))
            rows.append({"case_id": cid, "activity": act, "timestamp": t.strftime("%Y-%m-%d %H:%M:%S")})
    return pd.DataFrame(rows)


def main():
    if len(sys.argv) > 1:
        df = load_event_log(sys.argv[1])
    else:
        raw = generate_sample_log()
        raw.to_csv("sample_event_log.csv", index=False)
        df = load_event_log("sample_event_log.csv")

    miner = ProcessMiner(df)

    s = miner.summary()
    assert s["num_cases"] > 0 and s["num_events"] >= s["num_cases"]
    print("SUMMARY:", s)

    dfg, start, end = miner.discover_dfg()
    assert dfg and start and end
    print(f"DFG edges: {len(dfg)} | start: {start} | end: {end}")

    v = miner.variants()
    assert v["count"].sum() == s["num_cases"]
    assert abs(v["cumulative_percentage"].iloc[-1] - 100) < 0.5
    print("\nTOP VARIANTS:\n", v[["rank", "count", "percentage", "mean_duration_hours", "path"]].head(5).to_string(index=False))

    t = miner.throughput_summary()
    assert t["max_hours"] >= t["mean_hours"] >= t["min_hours"] >= 0
    print("\nTHROUGHPUT:", t)

    b = miner.bottlenecks(top_n=5)
    assert len(b) > 0
    print("\nBOTTLENECKS:\n", b[["transition", "count", "mean_hours", "max_hours", "share_of_total_wait_pct"]].to_string(index=False))

    alerts = miner.bottleneck_alerts()
    print("\nALERTS:", len(alerts))
    for a in alerts[:3]:
        print(" -", a["severity"], a["message"])

    print("\nACTIVITY WAITING:\n", miner.activity_waiting_times().head(3).to_string(index=False))

    for metric in ("frequency", "performance"):
        dot = miner.dfg_to_dot(metric)
        assert dot.startswith("digraph") and dot.rstrip().endswith("}")

    print("\nPROCESS TREE:", miner.process_tree_text())
    q = miner.model_quality()
    assert 0 <= q["fitness"] <= 1 and 0 <= q["precision"] <= 1
    print("MODEL QUALITY:", q)

    # filters
    top = miner.filter_top_variants(0.8)
    assert top.summary()["num_cases"] <= s["num_cases"]
    f = miner.filter_date_range("2026-01-15", "2026-02-15")
    assert f.summary()["num_cases"] <= s["num_cases"]
    assert miner.filter_activities(["Admission", "Triage", "Discharge"]).summary()["num_activities"] == 3
    d = miner.filter_case_duration(min_hours=1)
    assert d.summary()["num_cases"] <= s["num_cases"]
    assert len(miner.long_running_cases()) > 0
    print(f"\nFilters OK (top-80% variants keeps {top.summary()['num_cases']} of {s['num_cases']} cases)")

    files = miner.export_all("output")
    print("Exported:", list(files))
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
