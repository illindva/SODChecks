# SODChecks

SODChecks is a robust, lightweight Python application designed to run strictly on Enterprise environments like **RHEL 8** using **Python 3.12**. It provides an active health-checking and dashboarding solution capable of monitoring logs, processes, running remote commands on Linux/Windows, sending Teams notifications, emailing reports, and running various Database queries.

## 🌟 Features
- **Remote Execution**: Connect to Linux via SSH or Windows via WinRM.
- **Log Pattern & Process Monitoring**: Native RHEL8 bash executions (`ps`, `pgrep`, `tail`, `grep`) to securely and quickly monitor logs and processes.
- **Database Querying**: Run direct queries against Oracle, MSSQL, Sybase, and GemFire (Apache Geode) clusters.
- **Format Conversions**: Convert JSON to HTML tables and vice versa.
- **Alerting**: Built-in Microsoft Teams and SMTP Email alerting.
- **Background Scheduling**: Automated background execution (Hourly, Daily, Weekly) using APScheduler.

---

## 🚀 Setup & Installation (RHEL 8)

### 1. Install System Dependencies
Ensure Python 3.12 and the necessary database build tools (like `unixODBC` for Sybase/MSSQL) are installed.
```bash
sudo dnf update -y
sudo dnf install -y python3.12 python3.12-devel gcc gcc-c++ make libffi-devel openssl-devel curl unixODBC unixODBC-devel freetds freetds-devel
```

### 2. Set Up the Python Virtual Environment
Navigate to the project directory and install the required Python packages.
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables (.env)
The application relies on a `.env` file to securely load configuration parameters without hardcoding them into the OS or the scripts. 

Create a file named `.env` in the root of the project directory (`/opt/sodchecks/.env`) and add the necessary configurations (see `.env.example`).

### 4. Start the Application
You can run the application directly for development:
```bash
python app.py
```
*(The SQLite database `healthchecks.db` will be created and patched automatically on startup)*.

---

## 🛠️ Available Health Checks & Utilities

SODChecks allows you to configure dynamic checks directly from the web GUI (`/config`). Here are the available categories:

1. **Process Status**: Verifies if a specific process is running natively on a RHEL8 host (`ps`/`pgrep`) and retrieves its memory consumption and uptime.
2. **Log Pattern**: Scans the tail (last 500 lines) of a log file via RHEL8 bash for a specific keyword or regex pattern.
3. **Linux Command**: Connects to a remote Linux host via SSH and executes a bash command.
4. **Windows Command**: Connects to a remote Windows host using WinRM and executes a `cmd` command.
5. **Teams Notification**: Sends a message to a Microsoft Teams channel via webhook.
6. **Send Email Report**: Sends an email to a designated list of recipients (comma-separated).
7. **JSON/HTML Conversion**: Converts a raw JSON array to an HTML Table, or scrapes an HTML table back to JSON.
8. **Oracle Query**: Connects to an Oracle DB (`Host:Port`, Service Name in Target Path), runs a SQL query, and outputs an HTML table.
9. **MSSQL Query**: Connects to an MSSQL DB (`Host:Port`, Database Name in Target Path), runs a SQL query, and outputs an HTML table.
10. **Sybase Query**: Connects to a Sybase DB via FreeTDS, runs a SQL query, and outputs an HTML table.
11. **GemFire OQL**: Connects to a VMware GemFire Developer REST API, runs an OQL query, and outputs an HTML table.

---

## 🧪 Local Testing & Development

To make it incredibly easy for beginners to understand and modify the underlying execution commands, a suite of standalone test scripts are available in the `tests/` directory.

These scripts allow you to test changes to the `runners.py` execution logic locally on your RHEL8 machine without starting the web server or connecting to the database.

- `python tests/test_log_pattern.py` - Tests tailing a dummy log file.
- `python tests/test_process_stats.py` - Tests checking process statistics against the local python process.
- `python tests/test_email.py` - Tests SMTP notification flows.
- `python tests/test_teams.py` - Tests Teams Webhook flows.
- `python tests/test_linux_command.py` - Tests SSH mock commands.
- `python tests/test_db_queries.py` - Tests DB query runner logic.
- `python tests/test_gemfire_oql.py` - Tests GemFire REST API query logic.
- `python tests/test_json_html.py` - Tests data conversion outputs.

Simply edit the `DummyHealthCheck` inside these scripts to modify target paths or payloads to match your testing environment!

---
*Note: Any remote connection relies on SSH (Linux) or WinRM (Windows) being reachable. Database connections require network firewall rules permitting database port access.*
