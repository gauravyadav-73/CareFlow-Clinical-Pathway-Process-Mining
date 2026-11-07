# CareFlow Clinical Pathway Process Mining

CareFlow is a Streamlit application for exploring clinical event logs,
pathways, conformance, event timing, and dataset quality.

## Run locally

1. Use Python 3.10 or later.
2. Create and activate a virtual environment.
3. Install the application dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. (Optional) Configure a shared initial account in `.streamlit/secrets.toml`:

   ```toml
   [auth]
   email = "you@example.com"
   name = "Your Name"
   password = "your-password"
   ```

   Keep this file private; it is excluded from version control. The `name`
   setting is optional. For compatibility, `username` can still be used in
   place of `email`. Users can also create accounts with their email, name,
   and password from the login page. Registered accounts are stored locally
   in `.streamlit/users.db`, which is also excluded from version control.

5. Start the application:

   ```powershell
   python -m streamlit run app.py
   ```

## Use CareFlow

1. Sign in, or create an account from the login page.
2. Open **Upload Dataset** from the sidebar and upload your event log as a CSV.
   Each row should represent one event for a case, with columns for the case ID,
   activity, and event timestamp. For example:

   ```csv
   case_id,activity,timestamp
   P-1001,Emergency department arrival,2025-01-12 08:15:00
   P-1001,Initial assessment,2025-01-12 08:42:00
   P-1001,Discharge,2025-01-12 12:10:00
   ```

3. In **Event-log column mapping**, choose the columns for case ID, activity,
   and timestamp. They must be three distinct columns. Review the validation
   results and data-quality messages before continuing. The selected mapping
   remains available as you navigate between pages.
4. Optionally filter the event log by case or activity and download the
   filtered CSV. By default, all available cases and activities are selected.
5. Use the sidebar to explore your uploaded data:
   - **Dashboard** — overview metrics and a summary process map.
   - **Process Discovery** — observed transitions, activity frequency, and
     common pathway variants.
   - **Pathway Comparison** — compare the event sequences of two cases.
   - **Case Explorer** — inspect an individual case timeline and its events.
   - **What-if Simulator** — estimate the effect of a hypothetical reduction
     in elapsed gaps between events.
   - **Bottleneck Analysis** — rank activities by observed time to the next
     event.
   - **Conformance Analysis** — compare case sequences with a selected
     frequently observed reference pathway.
   - **Deviation Explorer** — inspect how observed pathway variants differ
     from the most common variant.
   - **Reports** — review data-quality and analysis summaries and download
     reports, tables, or the original dataset.

Analysis pages use events with valid case IDs, activities, and timestamps.
Waiting times are elapsed time between recorded events; they are not
necessarily queue time or treatment duration. Automatically selected
conformance references and common pathways are derived from the uploaded data
and are not prescribed clinical standards.
