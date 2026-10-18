"""
CareFlow - Process Mining Specialist backend
============================================
Process discovery and core analytics built on PM4Py.

Input : an event log with columns  case_id, activity, timestamp
        (CSV or XES, as produced by the Data Engineer).
Output: plain pandas DataFrames / dicts / PM4Py models that the Streamlit
