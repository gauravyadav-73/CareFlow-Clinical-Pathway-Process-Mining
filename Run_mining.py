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
