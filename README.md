# SODChecks

SODChecks is a robust, lightweight Python application designed to run on Enterprise environments like **RHEL 8** using **Python 3.12**. It provides an active health-checking and dashboarding solution capable of monitoring logs, processes, running remote commands on Linux/Windows, sending Teams notifications, emailing reports, and running various Database queries.

## 🌟 Features
- **Remote Execution**: Connect to Linux via SSH or Windows via WinRM.
- **Log Pattern & Process Monitoring**: Tail remote logs for regex matches or monitor process uptime and memory.
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

Create a file named `.env` in the root of the project directory (`/opt/sodchecks/.env`) and add the following keys:
```ini
# Core Configuration
FLASK_SECRET_KEY=YourSuperSecretKey123!@#

# Microsoft Teams Integration
TEAMS_WEBHOOK_URL=https://your-teams-webhook-url

# Email Notifications Configuration
SMTP_SERVER=smtp.yourbank.internal
SMTP_PORT=25
# SMTP_USER=your_smtp_user (Optional)
# SMTP_PASSWORD=your_smtp_password (Optional)
DEFAULT_FROM_EMAIL=sodchecks@yourbank.internal
```
*(A template is also available in `.env.example`)*.

### 4. Start the Application
You can run the application directly for development:
```bash
python app.py
```
*(The SQLite database `healthchecks.db` will be created and patched automatically on startup)*.

For **Production**, a `sodchecks.service` file is provided to run the app as a background systemd service using Gunicorn. Ensure you update paths inside the service file, copy it to `/etc/systemd/system/`, and enable it.

---

## 🛠️ Available Health Checks & Utilities

SODChecks allows you to configure dynamic checks directly from the web GUI (`/config`). Here are the available categories:

1. **Process Status**: Verifies if a specific process is running on the host and retrieves its memory consumption and uptime.
2. **Log Pattern**: Scans the tail (last 500 lines) of a log file for a specific keyword or regex pattern.
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
*Note: Any remote connection relies on SSH (Linux) or WinRM (Windows) being reachable. Database connections require network firewall rules permitting database port access.*
