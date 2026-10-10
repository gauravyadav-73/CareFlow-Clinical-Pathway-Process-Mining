"""
CLI entry point for the Process Mining Specialist module.

Usage:
    python run_mining.py                                  # uses data/sample_event_log.csv
    python run_mining.py --log data/clean_event_log.csv   # Data Engineer's file
    python run_mining.py --log data/log.xes --out outputs --no-render
"""
import argparse

