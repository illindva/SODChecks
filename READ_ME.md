# SODChecks Application

SODChecks is a robust, lightweight Python application designed to run on Enterprise environments like **RHEL 8** using **Python 3.12**. It provides an active health-checking and dashboarding solution capable of monitoring logs, processes, running remote commands on Linux/Windows, sending Teams notifications, and emailing reports.

## System Requirements
- Red Hat Enterprise Linux (RHEL) 8
- Python 3.12
- `curl` (for Teams webhook notifications)
- Internet/Intranet access for pulling python packages and reaching targets

---

## Installation & Setup Guide (RHEL 8)

### 1. Install System Dependencies
Python 3.12 and necessary build tools (required for compiling libraries like `psutil` or `cryptography`) must be installed on the RHEL 8 host. Additionally, to support database connections (specifically Sybase/MSSQL via ODBC), you need the `unixODBC` and `freetds` packages.
```bash
sudo dnf update -y
sudo dnf install -y python3.12 python3.12-devel gcc gcc-c++ make libffi-devel openssl-devel curl unixODBC unixODBC-devel freetds freetds-devel
```

### 2. Create a Dedicated Service User
For security, the application should run under a dedicated, non-root user account.
```bash
sudo useradd -r -s /bin/nologin sodadmin
```

### 3. Deploy the Application
Move the application source code to the recommended `/opt` directory and set permissions.
```bash
# Assuming the code is currently in /tmp/SODChecks
sudo cp -r /tmp/SODChecks /opt/sodchecks
sudo chown -R sodadmin:sodadmin /opt/sodchecks
```

### 4. Set Up the Python Virtual Environment
Switch to the `sodadmin` user (or run via sudo) to create the isolated environment and install dependencies.
```bash
sudo -u sodadmin bash -c 'cd /opt/sodchecks && python3.12 -m venv venv'
sudo -u sodadmin bash -c 'cd /opt/sodchecks && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'
```

### 5. Configure Environment Variables
You should configure the necessary environment variables. Edit `/opt/sodchecks/sodchecks.service` to include your secure specific parameters, or define them in `config.py`.

In the `[Service]` section of `sodchecks.service`, modify the placeholders:
```ini
Environment="FLASK_SECRET_KEY=YourSuperSecretKey123!@#"
Environment="TEAMS_WEBHOOK_URL=https://your-teams-webhook-url"
Environment="SMTP_SERVER=smtp.yourbank.internal"
Environment="SMTP_PORT=25"
Environment="DEFAULT_FROM_EMAIL=sodchecks@yourbank.internal"
```

### 6. Install and Start the Systemd Service
The application uses Gunicorn as the production WSGI server. A systemd service file is provided to keep the app running in the background and start it on boot.

```bash
sudo cp /opt/sodchecks/sodchecks.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sodchecks.service
sudo systemctl start sodchecks.service
sudo systemctl status sodchecks.service
```

### 7. Access the Application
By default, Gunicorn runs on `0.0.0.0:5000` (configured in `gunicorn.conf.py`). Ensure the firewall allows this traffic:
```bash
sudo firewall-cmd --zone=public --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```
Navigate to `http://<RHEL-SERVER-IP>:5000` in your web browser.

---

## Available Health Checks & Utilities

SODChecks allows you to configure dynamic checks directly from the web GUI under the **Configuration** tab. Here are the available check types you can configure:

### 1. Process Status (`process_stats`)
- **Description**: Verifies if a specific process is running on the host and retrieves its memory consumption and uptime.
- **How to use**: Specify the Target Host (or `localhost`). In **Target Path**, provide the Process Name or PID.

### 2. Log Pattern Matching (`log_pattern`)
- **Description**: Scans the tail (last 500 lines) of a log file for a specific keyword or regex pattern. If the pattern is found, the check passes.
- **How to use**: Specify the Target Host, SSH credentials if remote, the absolute path to the log file in **Target Path**, and the search string in **Search Pattern**.

### 3. Remote Linux Command (`linux_command_sample`)
- **Description**: Connects to a remote Linux host via SSH and executes an arbitrary bash command.
- **How to use**: Provide the Target Host, SSH User, and Password/Key. Enter the bash command in the **Target Path** field.

### 4. Remote Windows Command (`windows_command_sample`)
- **Description**: Connects to a remote Windows host using WinRM and executes a command from the Windows Command Prompt.
- **How to use**: Provide the Target Host, Windows Username, and Password. Enter the cmd command in the **Target Path** field.

### 5. Send Teams Notification (`teams_notification_sample`)
- **Description**: Sends a message to a Microsoft Teams channel using the configured webhook URL.
- **How to use**: Enter the message text you wish to send in the **Search Pattern** field.

### 6. Send Email Report (`send_email_sample`)
- **Description**: Sends an email to a designated list of recipients.
- **How to use**: Enter comma-separated email addresses in the **Target Path** field. The check's **Name** will be used as the Email Subject.

### 7. JSON to HTML Conversion (`json_to_html_sample`)
- **Description**: Converts a raw JSON array into a formatted HTML Table.
- **How to use**: Paste the JSON string inside the **Search Pattern** field.

### 8. HTML to JSON Conversion (`html_to_json_sample`)
- **Description**: Scrapes an HTML table and converts the data rows into a structured JSON array.
- **How to use**: Paste the HTML table string inside the **Search Pattern** field.

### 9. Oracle Query Check (`oracle_query_sample`)
- **Description**: Connects to an Oracle DB, runs a SQL query, and outputs the result as an HTML table.
- **How to use**: Specify `Host:Port` (e.g., `oracle.db.internal:1521`), put the Oracle Service Name in **Target Path**, enter DB credentials in SSH User/Password fields, and put the SQL query in **Search Pattern**.

### 10. MSSQL Query Check (`mssql_query_sample`)
- **Description**: Connects to an MSSQL DB, runs a SQL query, and outputs the result as an HTML table.
- **How to use**: Specify `Host:Port` (e.g., `mssql.db.internal:1433`), put the Database Name in **Target Path**, enter DB credentials in SSH User/Password fields, and put the SQL query in **Search Pattern**.

### 11. Sybase Query Check (`sybase_query_sample`)
- **Description**: Connects to a Sybase DB, runs a SQL query, and outputs the result as an HTML table.
- **How to use**: Specify `Host:Port` (e.g., `sybase.db.internal:5000`), put the Database Name in **Target Path**, enter DB credentials in SSH User/Password fields, and put the SQL query in **Search Pattern**. Note: Sybase check uses the `FreeTDS` ODBC driver on Linux.

### 12. GemFire OQL Query Check (`gemfire_oql_sample`)
- **Description**: Connects to a VMware GemFire (Apache Geode) cluster via its Developer REST API, runs an OQL query, and outputs the result as an HTML table.
- **How to use**: Specify the full REST API URL in **Host** (e.g., `http://gemfire.internal:8080`), enter Basic Auth credentials in SSH User/Password fields (if authentication is required), and put the raw OQL query in **Search Pattern**.

---
*Note: Any remote connection relies on SSH (Linux) or WinRM (Windows) being enabled and reachable from the RHEL 8 server running SODChecks. Database connections require network firewall rules permitting database port access.*
