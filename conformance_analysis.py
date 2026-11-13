"""
conformance_analysis.py
=======================
Task 3 - Conformance & Clinical Insights Analyst
CareFlow-Clinical-Pathway-Process-Mining

What this module does
---------------------
1. Defines the ideal (standard) clinical pathway as a Petri net.
2. Compares actual patient paths with that standard using PM4Py
   (token-based replay + alignments).
3. Identifies protocol deviations (missing / unexpected / out-of-order steps).
4. Finds delay drivers (slow hand-offs between activities) and SLA breaches.
5. Produces ready-to-display tables and plain-English insights for the
   Streamlit UI (Task 4) and the project report.

Input
-----
A pandas DataFrame (or CSV/XES path) with an event log. The standard columns
from the Data Engineer (Task 1) are  Case ID | Activity | Timestamp. Common
name variants and the PM4Py names (case:concept:name, concept:name,
time:timestamp) are also accepted.

Typical use from the UI / other modules
---------------------------------------
    from conformance_analysis import run_conformance_analysis
    result = run_conformance_analysis("data/clean_event_log.csv")
    result["summary"]            # dict of headline KPIs
    result["case_results"]       # one row per patient case
    result["deviation_summary"]  # deviation counts by type/activity
    result["delay_drivers"]      # slowest transitions
    result["insights"]           # list of text insights
"""

from __future__ import annotations

import argparse
import os
import warnings
from collections import Counter
from typing import Dict, List, Optional, Sequence, Union

import pandas as pd

warnings.filterwarnings("ignore")

import pm4py  # noqa: E402

# --------------------------------------------------------------------------- #
# 1. STANDARD CLINICAL PATHWAY DEFINITION
# --------------------------------------------------------------------------- #
# Edit these to match the activity names produced by the Data Engineer.
# mandatory steps: must happen, in this order.
# optional steps : may be skipped; the key is the mandatory activity they
#                  come right AFTER.
STANDARD_MANDATORY: List[str] = [
    "Registration",
    "Triage",
    "Doctor Consultation",
    "Treatment",
    "Discharge",
]
STANDARD_OPTIONAL: Dict[str, List[str]] = {
    "Doctor Consultation": ["Lab Test", "X-Ray"],
}

# Maximum acceptable gap (hours) between consecutive steps (clinical SLAs).
# Unlisted transitions use DEFAULT_SLA_HOURS.
SLA_HOURS: Dict[tuple, float] = {
    ("Registration", "Triage"): 0.5,
    ("Triage", "Doctor Consultation"): 1.0,
    ("Doctor Consultation", "Treatment"): 2.0,
}
DEFAULT_SLA_HOURS = 3.0

CASE, ACT, TS = "case:concept:name", "concept:name", "time:timestamp"

_COLUMN_ALIASES = {
    CASE: ["case id", "case_id", "caseid", "case", "patient id", "patient_id",
           "case:concept:name"],
    ACT: ["activity", "activity name", "event", "concept:name", "task"],
    TS: ["timestamp", "time", "datetime", "date_time", "time:timestamp",
         "start_timestamp", "start time"],
}


# --------------------------------------------------------------------------- #
# 2. LOADING / NORMALISING THE EVENT LOG
# --------------------------------------------------------------------------- #
def load_event_log(source: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """Load a CSV/XES path or DataFrame and normalise to PM4Py column names."""
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        path = str(source)
        if path.lower().endswith((".xes", ".xes.gz")):
            df = pm4py.convert_to_dataframe(pm4py.read_xes(path))
        else:
            df = pd.read_csv(path)

    lookup = {str(c).strip().lower(): c for c in df.columns}
    rename = {}
    for target, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lookup:
                rename[lookup[alias]] = target
                break
    df = df.rename(columns=rename)

    missing = [c for c in (CASE, ACT, TS) if c not in df.columns]
    if missing:
        raise ValueError(
            "Event log must contain Case ID, Activity and Timestamp columns. "
            f"Missing after normalisation: {missing}. Found: {list(df.columns)}"
        )

    df = df[[CASE, ACT, TS] + [c for c in df.columns if c not in (CASE, ACT, TS)]]
    df[CASE] = df[CASE].astype(str).str.strip()
    df[ACT] = df[ACT].astype(str).str.strip()
    df[TS] = pd.to_datetime(df[TS], errors="coerce", utc=True)
    df = df.dropna(subset=[CASE, ACT, TS])
    df = df[df[ACT] != ""]
    # stable sort keeps original order for identical timestamps
    df = df.sort_values([CASE, TS], kind="mergesort").reset_index(drop=True)
    return df


# --------------------------------------------------------------------------- #
# 3. BUILD THE STANDARD PATHWAY MODEL
# --------------------------------------------------------------------------- #
def _tree_string(mandatory: Sequence[str],
                 optional: Dict[str, List[str]]) -> str:
    """Build a PM4Py process-tree string: a sequence with optional steps."""
    parts = []
    for act in mandatory:
        parts.append(f"'{act}'")
        for opt in optional.get(act, []):
            parts.append(f"X('{opt}',tau)")
    return "->(" + ",".join(parts) + ")"


def build_standard_model(
    mandatory: Sequence[str] = STANDARD_MANDATORY,
    optional: Optional[Dict[str, List[str]]] = None,
):
    """Return (petri_net, initial_marking, final_marking) for the ideal pathway."""
    optional = STANDARD_OPTIONAL if optional is None else optional
    tree = pm4py.parse_process_tree(_tree_string(mandatory, optional))
    return pm4py.convert_to_petri_net(tree)


# --------------------------------------------------------------------------- #
# 4. CONFORMANCE CHECKING (variant based => fast)
# --------------------------------------------------------------------------- #
def _case_traces(df: pd.DataFrame) -> Dict[str, tuple]:
    return {cid: tuple(g[ACT]) for cid, g in df.groupby(CASE, sort=False)}


def _classify_alignment(alignment: list) -> Dict[str, list]:
    """Turn a PM4Py alignment into lists of missing / unexpected activities."""
    missing, unexpected = [], []
    for log_move, model_move in alignment:
        if log_move == ">>" and model_move is not None and model_move != ">>":
            missing.append(model_move)    # model expected it, log lacks it
        elif model_move == ">>" and log_move != ">>":
            unexpected.append(log_move)   # log has it, model did not allow it
    return {"missing": missing, "unexpected": unexpected}


def check_conformance(df: pd.DataFrame, net, im, fm) -> pd.DataFrame:
    """Align each distinct trace variant with the model and map back to cases."""
    traces = _case_traces(df)
    variants = sorted(set(traces.values()))

    # one representative case per variant -> alignments computed once each
    rows = []
    base = pd.Timestamp("2000-01-01", tz="UTC")
    for i, var in enumerate(variants):
        for j, act in enumerate(var):
            rows.append({CASE: f"v{i:07d}", ACT: act,
                         TS: base + pd.Timedelta(minutes=j)})
    var_df = pd.DataFrame(rows)

    aligned = pm4py.conformance_diagnostics_alignments(
        var_df, net, im, fm,
        case_id_key=CASE, activity_key=ACT, timestamp_key=TS,
    )

    var_info = {}
    for i, var in enumerate(variants):
        al = aligned[i]
        cls = _classify_alignment(al["alignment"])
        var_info[var] = {
            "fitness": float(al.get("fitness", 0.0)),
            "cost": float(al.get("cost", 0.0)),
            "missing": cls["missing"],
            "unexpected": cls["unexpected"],
        }

    # token-based replay fitness as a second opinion
    try:
        tbr = pm4py.conformance_diagnostics_token_based_replay(
            var_df, net, im, fm,
            case_id_key=CASE, activity_key=ACT, timestamp_key=TS,
        )
        for i, var in enumerate(variants):
            var_info[var]["tbr_fitness"] = float(tbr[i]["trace_fitness"])
    except Exception:  # pragma: no cover
        for var in variants:
            var_info[var]["tbr_fitness"] = var_info[var]["fitness"]

    out = []
    for cid, var in traces.items():
        info = var_info[var]
        missing, unexpected = info["missing"], info["unexpected"]
        both = set(missing) & set(unexpected)

        types = []
        if both:
            types.append("Out-of-order step")
        miss_only = [a for a in missing if a not in both]
        extra_only = [a for a in unexpected if a not in both]
        repeated = [a for a in extra_only if var.count(a) > 1]
        if miss_only:
            types.append("Missing mandatory step")
        if repeated:
            types.append("Repeated step")
        if [a for a in extra_only if a not in repeated]:
            types.append("Unexpected step")

        out.append({
            CASE: cid,
            "trace": " -> ".join(var),
            "fitness": round(info["fitness"], 4),
            "tbr_fitness": round(info["tbr_fitness"], 4),
            # silent (tau) moves carry a tiny non-zero cost in PM4Py, so judge
            # conformance by real deviations instead of cost == 0
            "is_conforming": not missing and not unexpected,
            "missing_activities": ", ".join(sorted(set(miss_only))),
            "unexpected_activities": ", ".join(sorted(set(extra_only))),
            "out_of_order_activities": ", ".join(sorted(both)),
            "deviation_types": "; ".join(types),
            "num_deviations": len(missing) + len(unexpected),
        })
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- #
# 5. TIMING ANALYSIS (throughput, delays, SLA)
# --------------------------------------------------------------------------- #
def compute_case_durations(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(CASE)[TS]
    d = pd.DataFrame({"start": g.min(), "end": g.max()})
    d["throughput_hours"] = (d["end"] - d["start"]).dt.total_seconds() / 3600
    return d.reset_index()


def compute_transition_waits(df: pd.DataFrame) -> pd.DataFrame:
    """Waiting time (hours) for every consecutive activity pair in every case."""
    d = df[[CASE, ACT, TS]].copy()
    d["next_act"] = d.groupby(CASE)[ACT].shift(-1)
    d["next_ts"] = d.groupby(CASE)[TS].shift(-1)
    d = d.dropna(subset=["next_act"])
    d["wait_hours"] = (d["next_ts"] - d[TS]).dt.total_seconds() / 3600
    d = d.rename(columns={ACT: "from_activity", "next_act": "to_activity"})
    return d[[CASE, "from_activity", "to_activity", "wait_hours"]]


_DELAY_COLS = [
    "transition", "from_activity", "to_activity", "cases", "mean_wait_h",
    "median_wait_h", "p90_wait_h", "sla_h", "sla_breach_pct", "total_wait_h",
    "mean_wait_conforming_h", "mean_wait_deviating_h",
]


def analyse_delay_drivers(waits: pd.DataFrame, conforming_ids: set) -> pd.DataFrame:
    """Rank transitions by average wait and flag SLA breaches."""
    if waits.empty:
        return pd.DataFrame(columns=_DELAY_COLS)
    w = waits.copy()
    w["sla"] = [SLA_HOURS.get((a, b), DEFAULT_SLA_HOURS)
                for a, b in zip(w["from_activity"], w["to_activity"])]
    w["breach"] = w["wait_hours"] > w["sla"]
    w["conf"] = w[CASE].isin(conforming_ids)

    rows = []
    for (a, b), g in w.groupby(["from_activity", "to_activity"]):
        c, n = g[g["conf"]], g[~g["conf"]]
        rows.append({
            "transition": f"{a} -> {b}",
            "from_activity": a, "to_activity": b,
            "cases": len(g),
            "mean_wait_h": round(g["wait_hours"].mean(), 2),
            "median_wait_h": round(g["wait_hours"].median(), 2),
            "p90_wait_h": round(g["wait_hours"].quantile(0.9), 2),
            "sla_h": g["sla"].iloc[0],
            "sla_breach_pct": round(100 * g["breach"].mean(), 1),
            "total_wait_h": round(g["wait_hours"].sum(), 1),
            "mean_wait_conforming_h":
                round(c["wait_hours"].mean(), 2) if len(c) else None,
            "mean_wait_deviating_h":
                round(n["wait_hours"].mean(), 2) if len(n) else None,
        })
    return (pd.DataFrame(rows, columns=_DELAY_COLS)
            .sort_values("mean_wait_h", ascending=False)
            .reset_index(drop=True))


# --------------------------------------------------------------------------- #
# 6. DEVIATION SUMMARY
# --------------------------------------------------------------------------- #
def summarise_deviations(case_results: pd.DataFrame) -> pd.DataFrame:
    """Count deviations by (type, activity)."""
    counter: Counter = Counter()
    for _, r in case_results.iterrows():
        for col, label in (("missing_activities", "Missing mandatory step"),
                           ("unexpected_activities", "Unexpected/repeated step"),
                           ("out_of_order_activities", "Out-of-order step")):
            for act in filter(None, [a.strip() for a in r[col].split(",")]):
                counter[(label, act)] += 1
    total = max(len(case_results), 1)
    cols = ["deviation_type", "activity", "cases", "pct_of_cases"]
    rows = [{"deviation_type": t, "activity": a, "cases": n,
             "pct_of_cases": round(100 * n / total, 1)}
            for (t, a), n in counter.items()]
    if not rows:
        return pd.DataFrame(columns=cols)
    return (pd.DataFrame(rows, columns=cols)
            .sort_values("cases", ascending=False).reset_index(drop=True))


# --------------------------------------------------------------------------- #
# 7. INSIGHTS TEXT
# --------------------------------------------------------------------------- #
def generate_insights(summary: dict, dev_summary: pd.DataFrame,
                      delays: pd.DataFrame, case_results: pd.DataFrame) -> List[str]:
    ins: List[str] = []
    ins.append(
        f"{summary['conforming_cases']} of {summary['total_cases']} cases "
        f"({summary['conformance_rate_pct']}%) followed the standard pathway "
        f"exactly; average fitness is {summary['avg_fitness']}.")

    if summary["deviating_cases"] == 0 or dev_summary.empty:
        ins.append("No protocol deviations were found.")
    else:
        top = dev_summary.iloc[0]
        ins.append(
            f"Most common deviation: '{top['deviation_type']}' on "
            f"'{top['activity']}' ({top['cases']} cases, "
            f"{top['pct_of_cases']}%).")
        crit = case_results[case_results["missing_activities"].str.len() > 0]
        if len(crit):
            ins.append(
                f"{len(crit)} cases skipped at least one mandatory step - "
                "review these for patient-safety risk.")

    if not delays.empty:
        worst = delays.iloc[0]
        ins.append(
            f"Biggest bottleneck: {worst['transition']} - mean wait "
            f"{worst['mean_wait_h']} h (SLA {worst['sla_h']} h, "
            f"{worst['sla_breach_pct']}% of cases breach it).")
        breaching = delays[delays["sla_breach_pct"] > 25]
        if len(breaching):
            ins.append("Transitions with >25% SLA breaches: "
                       + ", ".join(breaching["transition"]) + ".")
        diff = delays.dropna(subset=["mean_wait_conforming_h",
                                     "mean_wait_deviating_h"]).copy()
        if len(diff):
            diff["gap"] = (diff["mean_wait_deviating_h"]
                           - diff["mean_wait_conforming_h"])
            d = diff.sort_values("gap", ascending=False).iloc[0]
            if d["gap"] > 0:
                ins.append(
                    f"Delay driver: on {d['transition']}, deviating cases wait "
                    f"{d['gap']:.2f} h longer than conforming cases "
                    f"({d['mean_wait_deviating_h']} h vs "
                    f"{d['mean_wait_conforming_h']} h).")

    if (summary["avg_throughput_deviating_h"] is not None
            and summary["avg_throughput_conforming_h"] is not None):
        ins.append(
            f"Average total stay: conforming "
            f"{summary['avg_throughput_conforming_h']} h vs deviating "
            f"{summary['avg_throughput_deviating_h']} h.")
    return ins


# --------------------------------------------------------------------------- #
# 8. MAIN ENTRY POINT
# --------------------------------------------------------------------------- #
def run_conformance_analysis(
    source: Union[str, pd.DataFrame],
    mandatory: Sequence[str] = STANDARD_MANDATORY,
    optional: Optional[Dict[str, List[str]]] = None,
) -> dict:
    """Run the full Task-3 pipeline and return a dict of results."""
    df = load_event_log(source)
    if df.empty:
        raise ValueError("Event log is empty after cleaning.")

    net, im, fm = build_standard_model(mandatory, optional)
    case_results = check_conformance(df, net, im, fm)

    durations = compute_case_durations(df)
    case_results = case_results.merge(
        durations[[CASE, "start", "end", "throughput_hours"]],
        on=CASE, how="left")
    case_results["throughput_hours"] = case_results["throughput_hours"].round(2)

    conforming_ids = set(case_results.loc[case_results["is_conforming"], CASE])
    waits = compute_transition_waits(df)
    delays = analyse_delay_drivers(waits, conforming_ids)
    dev_summary = summarise_deviations(case_results)

    total = len(case_results)
    conf = int(case_results["is_conforming"].sum())
    conf_t = case_results.loc[case_results["is_conforming"], "throughput_hours"]
    dev_t = case_results.loc[~case_results["is_conforming"], "throughput_hours"]
    summary = {
        "total_cases": total,
        "conforming_cases": conf,
        "deviating_cases": total - conf,
        "conformance_rate_pct": round(100 * conf / total, 1),
        "avg_fitness": round(float(case_results["fitness"].mean()), 4),
        "avg_tbr_fitness": round(float(case_results["tbr_fitness"].mean()), 4),
        "avg_throughput_h": round(float(case_results["throughput_hours"].mean()), 2),
        "avg_throughput_conforming_h":
            round(float(conf_t.mean()), 2) if len(conf_t) else None,
        "avg_throughput_deviating_h":
            round(float(dev_t.mean()), 2) if len(dev_t) else None,
        "distinct_variants": int(case_results["trace"].nunique()),
    }

    variant_conformance = (
        case_results.groupby("trace")
        .agg(cases=(CASE, "count"), fitness=("fitness", "first"),
             conforming=("is_conforming", "first"),
             deviation_types=("deviation_types", "first"),
             avg_throughput_h=("throughput_hours", "mean"))
        .reset_index().sort_values("cases", ascending=False)
        .reset_index(drop=True))
    variant_conformance["avg_throughput_h"] = \
        variant_conformance["avg_throughput_h"].round(2)

    return {
        "summary": summary,
        "case_results": case_results,
        "variant_conformance": variant_conformance,
        "deviation_summary": dev_summary,
        "delay_drivers": delays,
        "insights": generate_insights(summary, dev_summary, delays, case_results),
        "model": (net, im, fm),
        "event_log": df,
    }


def save_model_image(result: dict, path: str = "standard_pathway.png") -> str:
    """Save a picture of the standard pathway Petri net (needs Graphviz)."""
    net, im, fm = result["model"]
    pm4py.save_vis_petri_net(net, im, fm, path)
    return path


def export_results(result: dict, out_dir: str = "output") -> List[str]:
    """Write tables + insights to disk so the report/UI can reuse them."""
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for key in ("case_results", "variant_conformance",
                "deviation_summary", "delay_drivers"):
        p = os.path.join(out_dir, f"{key}.csv")
        result[key].to_csv(p, index=False)
        files.append(p)
    p = os.path.join(out_dir, "insights.txt")
    with open(p, "w", encoding="utf-8") as f:
        for k, v in result["summary"].items():
            f.write(f"{k}: {v}\n")
        f.write("\nKEY INSIGHTS\n")
        for i, line in enumerate(result["insights"], 1):
            f.write(f"{i}. {line}\n")
    files.append(p)
    return files


# --------------------------------------------------------------------------- #
# 9. DEMO DATA (only for testing when Task 1's file is not ready yet)
# --------------------------------------------------------------------------- #
def generate_demo_log(n_cases: int = 300, seed: int = 42) -> pd.DataFrame:
    import random
    rnd = random.Random(seed)
    start = pd.Timestamp("2026-01-01 08:00", tz="UTC")
    rows = []
    for i in range(1, n_cases + 1):
        t = start + pd.Timedelta(minutes=rnd.randint(0, 60 * 24 * 60))
        path = ["Registration", "Triage", "Doctor Consultation"]
        if rnd.random() < 0.5:
            path.append("Lab Test")
        if rnd.random() < 0.3:
            path.append("X-Ray")
        path += ["Treatment", "Discharge"]
        r = rnd.random()
        if r < 0.10:
            path.remove("Triage")                        # skipped triage
        elif r < 0.18:
            path.remove("Doctor Consultation")           # skipped consult
        elif r < 0.25:                                   # treatment before consult
            a, b = path.index("Doctor Consultation"), path.index("Treatment")
            path[a], path[b] = path[b], path[a]
        elif r < 0.32:                                   # repeated lab test
            path.insert(path.index("Treatment"), "Lab Test")
        elif r < 0.36:
            path.insert(path.index("Treatment"), "Surgery")   # unexpected
        slow = r < 0.32
        for act in path:
            rows.append({"Case ID": f"P{i:04d}", "Activity": act, "Timestamp": t})
            lo, hi = (30, 240) if slow else (10, 90)
            if act == "Doctor Consultation":
                hi *= 2
            t += pd.Timedelta(minutes=rnd.randint(lo, hi))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 10. COMMAND LINE
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(
        description="CareFlow conformance & clinical insights analysis")
    ap.add_argument("--input", help="clean event log (.csv or .xes). "
                                    "If omitted, demo data is used.")
    ap.add_argument("--out", default="output", help="output folder")
    ap.add_argument("--image", action="store_true",
                    help="also save a PNG of the standard pathway (Graphviz)")
    args = ap.parse_args()

    src = args.input if args.input else generate_demo_log()
    if not args.input:
        print("No --input given: using generated demo data.\n")
    res = run_conformance_analysis(src)

    print("SUMMARY")
    for k, v in res["summary"].items():
        print(f"  {k}: {v}")
    print("\nKEY INSIGHTS")
    for i, line in enumerate(res["insights"], 1):
        print(f"  {i}. {line}")
    print("\nTOP DEVIATIONS")
    print(res["deviation_summary"].head(10).to_string(index=False))
    print("\nTOP DELAY DRIVERS")
    print(res["delay_drivers"].head(5).to_string(index=False))

    files = export_results(res, args.out)
    if args.image:
        try:
            files.append(save_model_image(res, os.path.join(
                args.out, "standard_pathway.png")))
        except Exception as e:
            print(f"\n(Skipped image: {e})")
    print("\nSaved:", *files, sep="\n  ")


if __name__ == "__main__":
    main()
