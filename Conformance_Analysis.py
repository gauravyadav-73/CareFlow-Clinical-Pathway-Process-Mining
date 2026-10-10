"""
CareFlow - Clinical Pathway Process Mining

What this module does
---------------------
1. Defines the ideal (standard) clinical pathway as a process tree / Petri net.
2. Runs PM4Py token-based replay conformance checking: actual vs. standard.
3. Runs explainable rule-based deviation checks (missing, out-of-order, repeated steps).
4. Finds delay drivers (which transitions are slowest, and slower for deviating cases).
5. Produces plain-English insights + tidy DataFrames the Streamlit UI can display.
"""
