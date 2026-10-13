"""
CLI entry point for the Process Mining Specialist module.

Usage:
    python run_mining.py                                  # uses data/sample_event_log.csv
    python run_mining.py --log data/clean_event_log.csv   # Data Engineer's file
    python run_mining.py --log data/log.xes --out outputs --no-render
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd

import process_mining as pmn


def main():
     ap = argparse.ArgumentParser(description="CareFlow process mining analysis")
     ap.add_argument("--log", default="data/sample_event_log.csv", help=".csv or .xes event log")
     ap.add_argument("--out", default="outputs", help="output folder")
     ap.add_argument("--no-render", action="store_true", help="skip Graphviz image rendering")
     args = ap.parse_args()

     if not os.path.exists(args.log):
         if args.log.endswith("sample_event_log.csv"):
            from generate_sample_log import generate
            os.makedirs(os.path.dirname(args.log), exist_ok=True)
            generate().to_csv(args.log, index=False)
            print(f"[info] generated sample log -> {args.log}")
        else:
            sys.exit(f"Event log not found: {args.log}")
            
    pd.set_option("display.width", 200, "display.max_colwidth", 90)
    df = pmn.load_event_log(args.log)
    res = pmn.run_full_analysis(df, args.out, render=not args.no_render)

    s = res["summary"]
    print("\n=== LOG SUMMARY ===")
    print(f"Cases: {s['num_cases']} | Events: {s['num_events']} | "
          f"Activities: {s['num_activities']} | Variants: {s['num_variants']}")
    print(f"Period: {s['start_date']:%Y-%m-%d} to {s['end_date']:%Y-%m-%d}")

    print("\n=== THROUGHPUT TIME (hours) ===")
    for k, v in res["throughput_summary"].items():
        print(f"  {k:12s}: {v}")

    print("\n=== TOP 5 VARIANTS ===")
    print(res["variants"].head(5).to_string(index=False))

    print("\n=== TOP BOTTLENECKS (mean wait between steps) ===")
    print(res["bottlenecks"][["from", "to", "count", "mean_hours", "max_hours",
                              "severity", "x_vs_avg"]].to_string(index=False))
