"""
CareFlow - Clinical Pathway Process Mining
Task 2: Process Mining Specialist (Workflow Mapper) - PM4Py backend

Responsibilities covered
------------------------
* Discover actual patient pathways from an event log
* Directly-Follows Graphs (frequency + performance) and DOT export for Streamlit
* Inductive Miner (process tree + Petri net)
* Throughput times, bottlenecks and frequent patient variants

Input (produced by the Data Engineer): a CSV/XES file or DataFrame with
Case ID, Activity and Timestamp columns. Column names are auto-detected.

Typical use from the Streamlit UI:

    from process_mining_backend import ProcessMiner, load_event_log
    df = load_event_log("clean_event_log.csv")
    miner = ProcessMiner(df)
    st.graphviz_chart(miner.dfg_to_dot("frequency"))
    st.dataframe(miner.variants())
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import pm4py

CASE = "case:concept:name"
ACT = "concept:name"
TS = "time:timestamp"

_CASE_ALIASES = ["case:concept:name", "case_id", "caseid", "case id", "case", "patient_id", "patientid", "patient id"]
_ACT_ALIASES = ["concept:name", "activity", "event", "event_name", "task", "step"]
_TS_ALIASES = ["time:timestamp", "timestamp", "time", "datetime", "date_time", "start_time", "event_time"]

Edge = Tuple[str, str]


# --------------------------------------------------------------------------- #
# Loading / standardising
# --------------------------------------------------------------------------- #
def _find_col(columns, aliases, label):
    lowered = {str(c).strip().lower(): c for c in columns}
    for a in aliases:
        if a in lowered:
            return lowered[a]
    raise ValueError(
        f"Could not find a {label} column. Columns present: {list(columns)}. "
        f"Expected one of: {aliases}"
    )


def standardize_event_log(
    df: pd.DataFrame,
    case_col: Optional[str] = None,
    activity_col: Optional[str] = None,
    timestamp_col: Optional[str] = None,
) -> pd.DataFrame:
    """Return a clean copy with PM4Py standard columns, sorted by case and time."""
    if df is None or len(df) == 0:
        raise ValueError("The event log is empty.")

    case_col = case_col or _find_col(df.columns, _CASE_ALIASES, "case id")
    activity_col = activity_col or _find_col(df.columns, _ACT_ALIASES, "activity")
    timestamp_col = timestamp_col or _find_col(df.columns, _TS_ALIASES, "timestamp")

    out = df.copy()
    out = out.rename(columns={case_col: CASE, activity_col: ACT, timestamp_col: TS})
    # Drop duplicate columns that may arise when the file already has standard names
    out = out.loc[:, ~out.columns.duplicated()]

    out[CASE] = out[CASE].astype(str).str.strip()
    out[ACT] = out[ACT].astype(str).str.strip()
    out[TS] = pd.to_datetime(out[TS], errors="coerce", utc=True)

    out = out.dropna(subset=[CASE, ACT, TS])
    out = out[(out[CASE] != "") & (out[ACT] != "") & (out[CASE].str.lower() != "nan") & (out[ACT].str.lower() != "nan")]
    if out.empty:
        raise ValueError("No valid rows left after cleaning (check case/activity/timestamp values).")

    out = out.reset_index(drop=True)
    out["_order"] = range(len(out))  # keeps original order for identical timestamps
    out = out.sort_values([CASE, TS, "_order"], kind="mergesort").drop(columns="_order")
    return out.reset_index(drop=True)


def load_event_log(
    source: Union[str, pd.DataFrame],
    case_col: Optional[str] = None,
    activity_col: Optional[str] = None,
    timestamp_col: Optional[str] = None,
) -> pd.DataFrame:
    """Load a CSV / XES file path (or an existing DataFrame) into a standard event log."""
    if isinstance(source, pd.DataFrame):
        df = source
    else:
        path = str(source)
        ext = os.path.splitext(path)[1].lower()
        if ext == ".xes" or path.lower().endswith(".xes.gz"):
            df = pm4py.convert_to_dataframe(pm4py.read_xes(path))
        elif ext in (".csv", ".txt"):
            df = pd.read_csv(path)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    return standardize_event_log(df, case_col, activity_col, timestamp_col)


def _fmt_duration(seconds: float) -> str:
    if seconds is None or pd.isna(seconds):
        return "-"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def _dot_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


# --------------------------------------------------------------------------- #
# Main class
# --------------------------------------------------------------------------- #
class ProcessMiner:
    """Process discovery and analytics on a standardised event log."""

    def __init__(self, event_log: Union[pd.DataFrame, str], **column_kwargs):
        if isinstance(event_log, str) or not self._is_standard(event_log):
            event_log = load_event_log(event_log, **column_kwargs)
        self.df: pd.DataFrame = event_log.copy().reset_index(drop=True)

    @staticmethod
    def _is_standard(df) -> bool:
        return isinstance(df, pd.DataFrame) and {CASE, ACT, TS}.issubset(df.columns) \
            and pd.api.types.is_datetime64_any_dtype(df[TS])

    # ------------------------------------------------------------------ #
    # Filtering (returns a NEW ProcessMiner so the UI can chain filters)
    # ------------------------------------------------------------------ #
    def filter_date_range(self, start=None, end=None) -> "ProcessMiner":
        def _utc(x):
            ts = pd.Timestamp(x)
            return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")

        d = self.df
        if start is not None:
            d = d[d[TS] >= _utc(start)]
        if end is not None:
            d = d[d[TS] <= _utc(end)]
        return ProcessMiner(d)

    def filter_activities(self, keep: List[str]) -> "ProcessMiner":
        return ProcessMiner(self.df[self.df[ACT].isin(keep)])

    def filter_top_variants(self, coverage: float = 0.8) -> "ProcessMiner":
        """Keep the most frequent variants until `coverage` (0-1) of cases is reached."""
        if not 0 < coverage <= 1:
            raise ValueError("coverage must be in (0, 1].")
        v = self.variants()
        keep = v[v["cumulative_percentage"].shift(fill_value=0) < coverage * 100]["variant"].tolist()
        cv = self._case_variants()
        cases = cv[cv.isin(keep)].index
        return ProcessMiner(self.df[self.df[CASE].isin(cases)])

    def filter_case_duration(self, min_hours: Optional[float] = None, max_hours: Optional[float] = None) -> "ProcessMiner":
        t = self.throughput_times()
        if min_hours is not None:
            t = t[t["duration_hours"] >= min_hours]
        if max_hours is not None:
            t = t[t["duration_hours"] <= max_hours]
        return ProcessMiner(self.df[self.df[CASE].isin(t[CASE])])

    # ------------------------------------------------------------------ #
    # Basic stats
    # ------------------------------------------------------------------ #
    def summary(self) -> Dict:
        t = self.throughput_times()["duration_seconds"]
        return {
            "num_cases": int(self.df[CASE].nunique()),
            "num_events": int(len(self.df)),
            "num_activities": int(self.df[ACT].nunique()),
            "num_variants": int(len(self.variants())),
            "start_time": self.df[TS].min().isoformat(),
            "end_time": self.df[TS].max().isoformat(),
            "avg_throughput": _fmt_duration(t.mean()),
            "median_throughput": _fmt_duration(t.median()),
            "max_throughput": _fmt_duration(t.max()),
            "avg_throughput_hours": round(float(t.mean()) / 3600, 3),
        }

    def activity_frequencies(self) -> pd.DataFrame:
        g = self.df.groupby(ACT).agg(frequency=(CASE, "size"), cases=(CASE, "nunique")).reset_index()
        g = g.rename(columns={ACT: "activity"}).sort_values("frequency", ascending=False)
        return g.reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # Variants
    # ------------------------------------------------------------------ #
    def _case_variants(self) -> pd.Series:
        """Series indexed by case id with the variant tuple as value."""
        return self.df.groupby(CASE, sort=False)[ACT].apply(tuple)

    def variants(self, top_n: Optional[int] = None) -> pd.DataFrame:
        """Patient pathway variants with frequency, share and mean duration."""
        cv = self._case_variants()
        dur = self.throughput_times().set_index(CASE)["duration_seconds"]
        tmp = pd.DataFrame({"variant": cv, "duration_seconds": dur.reindex(cv.index)})
        g = tmp.groupby("variant")["duration_seconds"].agg(["size", "mean", "median"]).reset_index()
        g.columns = ["variant", "count", "mean_duration_seconds", "median_duration_seconds"]
        g = g.sort_values(["count"], ascending=False, kind="mergesort").reset_index(drop=True)
        total = g["count"].sum()
        g["percentage"] = (g["count"] / total * 100).round(2)
        g["cumulative_percentage"] = g["percentage"].cumsum().round(2)
        g["mean_duration_hours"] = (g["mean_duration_seconds"] / 3600).round(2)
        g["path"] = g["variant"].apply(lambda v: " -> ".join(v))
        g["length"] = g["variant"].apply(len)
        g.insert(0, "rank", range(1, len(g) + 1))
        return g.head(top_n) if top_n else g

    # ------------------------------------------------------------------ #
    # Throughput
    # ------------------------------------------------------------------ #
    def throughput_times(self) -> pd.DataFrame:
        """Per-case start, end and duration."""
        g = self.df.groupby(CASE, sort=False)[TS].agg(["min", "max"]).reset_index()
        g.columns = [CASE, "start", "end"]
        g["duration_seconds"] = (g["end"] - g["start"]).dt.total_seconds()
        g["duration_hours"] = g["duration_seconds"] / 3600
        g["duration_days"] = g["duration_seconds"] / 86400
        return g

    def throughput_summary(self) -> Dict[str, float]:
        d = self.throughput_times()["duration_hours"]
        return {
            "mean_hours": round(float(d.mean()), 3),
            "median_hours": round(float(d.median()), 3),
            "min_hours": round(float(d.min()), 3),
            "max_hours": round(float(d.max()), 3),
            "std_hours": round(float(d.std(ddof=0)), 3),
            "p90_hours": round(float(d.quantile(0.9)), 3),
            "p95_hours": round(float(d.quantile(0.95)), 3),
        }

    def long_running_cases(self, percentile: float = 0.9) -> pd.DataFrame:
        t = self.throughput_times()
        cut = t["duration_seconds"].quantile(percentile)
        return t[t["duration_seconds"] >= cut].sort_values("duration_seconds", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # Directly-Follows Graph
    # ------------------------------------------------------------------ #
    def _transitions(self) -> pd.DataFrame:
        d = self.df
        nxt_act = d.groupby(CASE, sort=False)[ACT].shift(-1)
        nxt_ts = d.groupby(CASE, sort=False)[TS].shift(-1)
        t = pd.DataFrame({"source": d[ACT], "target": nxt_act, "wait_seconds": (nxt_ts - d[TS]).dt.total_seconds()})
        return t.dropna(subset=["target"]).reset_index(drop=True)

    def discover_dfg(self) -> Tuple[Dict[Edge, int], Dict[str, int], Dict[str, int]]:
        """PM4Py directly-follows graph: (dfg, start_activities, end_activities)."""
        dfg, start, end = pm4py.discover_dfg(self.df, case_id_key=CASE, activity_key=ACT, timestamp_key=TS)
        return dict(dfg), dict(start), dict(end)

    def performance_dfg(self) -> pd.DataFrame:
        """For each directly-follows edge: count and waiting time statistics."""
        t = self._transitions()
        g = t.groupby(["source", "target"])["wait_seconds"].agg(["size", "mean", "median", "max", "sum"]).reset_index()
        g.columns = ["source", "target", "count", "mean_seconds", "median_seconds", "max_seconds", "total_seconds"]
        g["mean_hours"] = (g["mean_seconds"] / 3600).round(3)
        g["median_hours"] = (g["median_seconds"] / 3600).round(3)
        g["max_hours"] = (g["max_seconds"] / 3600).round(3)
        return g.sort_values("mean_seconds", ascending=False).reset_index(drop=True)

    def dfg_to_dot(self, metric: str = "frequency", min_edge_count: int = 1, rankdir: str = "LR") -> str:
        """Graphviz DOT source. Works with st.graphviz_chart() - no system Graphviz needed."""
        if metric not in ("frequency", "performance"):
            raise ValueError("metric must be 'frequency' or 'performance'")
        dfg, start, end = self.discover_dfg()
        perf = self.performance_dfg().set_index(["source", "target"])
        act_freq = self.df[ACT].value_counts().to_dict()

        edges = {e: c for e, c in dfg.items() if c >= min_edge_count}
        max_c = max(edges.values()) if edges else 1
        max_w = perf["mean_seconds"].max() if len(perf) else 1
        max_w = max_w if max_w and max_w > 0 else 1

        used = {a for e in edges for a in e}
        lines = [
            "digraph CareFlow {",
            f'  rankdir="{rankdir}";',
            '  node [shape=box, style="rounded,filled", fillcolor="#E8F1FA", fontname="Helvetica", color="#2B6CB0"];',
            '  edge [fontname="Helvetica", fontsize=10];',
            '  "START" [shape=circle, fillcolor="#C6F6D5", color="#2F855A", label="Start"];',
            '  "END" [shape=doublecircle, fillcolor="#FED7D7", color="#C53030", label="End"];',
        ]
        for a in sorted(used):
            lines.append(f'  "{_dot_escape(a)}" [label="{_dot_escape(a)}\\n({act_freq.get(a, 0)})"];')
        for a, c in sorted(start.items()):
            if a in used:
                lines.append(f'  "START" -> "{_dot_escape(a)}" [label="{c}", color="#2F855A"];')
        for a, c in sorted(end.items()):
            if a in used:
                lines.append(f'  "{_dot_escape(a)}" -> "END" [label="{c}", color="#C53030"];')
        for (a, b), c in sorted(edges.items()):
            if metric == "frequency":
                width = 1 + 4 * c / max_c
                label = str(c)
                color = "#2B6CB0"
            else:
                w = float(perf.loc[(a, b), "mean_seconds"]) if (a, b) in perf.index else 0.0
                width = 1 + 4 * w / max_w
                label = _fmt_duration(w)
                color = "#C53030" if w >= 0.66 * max_w else ("#DD6B20" if w >= 0.33 * max_w else "#2B6CB0")
            lines.append(f'  "{_dot_escape(a)}" -> "{_dot_escape(b)}" [label="{label}", penwidth={width:.2f}, color="{color}"];')
        lines.append("}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Inductive Miner
    # ------------------------------------------------------------------ #
    def discover_inductive(self, noise_threshold: float = 0.0):
        """Inductive Miner. Returns (petri_net, initial_marking, final_marking)."""
        net, im, fm = pm4py.discover_petri_net_inductive(
            self.df, noise_threshold=noise_threshold,
            activity_key=ACT, case_id_key=CASE, timestamp_key=TS,
        )
        return net, im, fm

    def discover_process_tree(self, noise_threshold: float = 0.0):
        return pm4py.discover_process_tree_inductive(
            self.df, noise_threshold=noise_threshold,
            activity_key=ACT, case_id_key=CASE, timestamp_key=TS,
        )

    def process_tree_text(self, noise_threshold: float = 0.0) -> str:
        return str(self.discover_process_tree(noise_threshold))

    def model_quality(self, noise_threshold: float = 0.0) -> Dict[str, float]:
        """Fitness / precision of the Inductive Miner model (token-based replay)."""
        net, im, fm = self.discover_inductive(noise_threshold)
        fit = pm4py.fitness_token_based_replay(self.df, net, im, fm, activity_key=ACT, case_id_key=CASE, timestamp_key=TS)
        prec = pm4py.precision_token_based_replay(self.df, net, im, fm, activity_key=ACT, case_id_key=CASE, timestamp_key=TS)
        return {
            "fitness": round(float(fit.get("average_trace_fitness", fit.get("log_fitness", 0.0))), 4),
            "precision": round(float(prec), 4),
            "places": len(net.places),
            "transitions": len(net.transitions),
            "arcs": len(net.arcs),
        }

    def save_process_model_image(self, path: str = "process_model.png", noise_threshold: float = 0.0) -> bool:
        """Render the Petri net to an image. Needs system Graphviz; returns False if unavailable."""
        try:
            net, im, fm = self.discover_inductive(noise_threshold)
            pm4py.save_vis_petri_net(net, im, fm, path)
            return os.path.exists(path)
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Bottlenecks
    # ------------------------------------------------------------------ #
    def bottlenecks(self, top_n: int = 10, min_count: int = 1) -> pd.DataFrame:
        """Transitions ranked by mean waiting time (and impact = total waiting time)."""
        p = self.performance_dfg()
        p = p[p["count"] >= min_count].copy()
        p["share_of_total_wait_pct"] = (p["total_seconds"] / p["total_seconds"].sum() * 100).round(2) if p["total_seconds"].sum() > 0 else 0.0
        p["transition"] = p["source"] + " -> " + p["target"]
        return p.sort_values("mean_seconds", ascending=False).head(top_n).reset_index(drop=True)

    def activity_waiting_times(self) -> pd.DataFrame:
        """Average time patients wait BEFORE each activity (time since previous event)."""
        t = self._transitions()
        g = t.groupby("target")["wait_seconds"].agg(["size", "mean", "median", "max"]).reset_index()
        g.columns = ["activity", "count", "mean_wait_seconds", "median_wait_seconds", "max_wait_seconds"]
        g["mean_wait_hours"] = (g["mean_wait_seconds"] / 3600).round(3)
        return g.sort_values("mean_wait_seconds", ascending=False).reset_index(drop=True)

    def bottleneck_alerts(self, threshold_hours: Optional[float] = None, percentile: float = 0.9, min_count: int = 3) -> List[Dict]:
        """Alert list for the dashboard. Flags transitions slower than a fixed threshold
        (hours) or, by default, slower than the given percentile of all edge means."""
        p = self.performance_dfg()
        p = p[p["count"] >= min_count]
        if p.empty:
            return []
        cut = threshold_hours * 3600 if threshold_hours is not None else p["mean_seconds"].quantile(percentile)
        hot = p[p["mean_seconds"] >= cut].sort_values("mean_seconds", ascending=False)
        alerts = []
        for _, r in hot.iterrows():
            severity = "HIGH" if r["mean_seconds"] >= 1.5 * cut else "MEDIUM"
            alerts.append({
                "severity": severity,
                "transition": f"{r['source']} -> {r['target']}",
                "mean_wait": _fmt_duration(r["mean_seconds"]),
                "max_wait": _fmt_duration(r["max_seconds"]),
                "cases_affected": int(r["count"]),
                "message": f"Patients wait on average {_fmt_duration(r['mean_seconds'])} between "
                           f"'{r['source']}' and '{r['target']}' ({int(r['count'])} cases).",
            })
        return alerts

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def export_all(self, output_dir: str = "output") -> Dict[str, str]:
        """Write all analytics to CSV/JSON/DOT files; returns {name: path}."""
        os.makedirs(output_dir, exist_ok=True)
        files = {}

        def _csv(name, frame):
            path = os.path.join(output_dir, name)
            frame.to_csv(path, index=False)
            files[name] = path

        v = self.variants().drop(columns=["variant"])
        _csv("variants.csv", v)
        _csv("throughput_times.csv", self.throughput_times())
        _csv("performance_dfg.csv", self.performance_dfg())
        _csv("bottlenecks.csv", self.bottlenecks(top_n=1000))
        _csv("activity_waiting_times.csv", self.activity_waiting_times())
        _csv("activity_frequencies.csv", self.activity_frequencies())

        for metric in ("frequency", "performance"):
            name = f"dfg_{metric}.dot"
            path = os.path.join(output_dir, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.dfg_to_dot(metric))
            files[name] = path

        report = {
            "summary": self.summary(),
            "throughput": self.throughput_summary(),
            "alerts": self.bottleneck_alerts(),
            "model_quality": self.model_quality(),
        }
        path = os.path.join(output_dir, "analysis_report.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        files["analysis_report.json"] = path
        return files


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python process_mining_backend.py <event_log.csv|xes> [output_dir]")
        sys.exit(1)
    miner = ProcessMiner(load_event_log(sys.argv[1]))
    print(json.dumps(miner.summary(), indent=2))
    out = miner.export_all(sys.argv[2] if len(sys.argv) > 2 else "output")
    print("Wrote:", ", ".join(out))
