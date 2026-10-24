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
   username = "your-username"
   password = "your-password"
   ```

   Keep this file private; it is excluded from version control. Users can also
   create their own accounts from the login page. Registered accounts are
   stored locally in `.streamlit/users.db`, which is also excluded from
   version control.

5. Start the application:

   ```powershell
   python -m streamlit run app.py
   ```

Upload a CSV event log, map the case ID, activity, and timestamp columns, and
then select an analysis page from the sidebar.
