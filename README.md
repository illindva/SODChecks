# Health Check Dashboard

A Flask-based web application to perform health checks on business applications. It supports dynamic configuration via UI, local/remote log and process monitoring, and daily/monthly stats tracking. Built specifically to be compatible with Python 3.6 on RHEL 8 environments.

## Features
- **Remote Execution**: SSH Key authentication to connect to remote hosts and run checks.
- **Log Pattern Checking**: Tails logs and uses regex/pattern matching to verify status.
- **Process Monitoring**: Verifies process uptime and memory consumption.
- **Background Scheduling**: Automated background execution (Hourly, Daily, Weekly) using APScheduler.
- **Premium UI**: Modern dark-mode interface built with Vanilla HTML/CSS/JS.

---

## 🚀 Running on RHEL 8 (Production Environment)

### Prerequisites
- RHEL 8 host.
- Python 3.6 installed (default on RHEL 8).
- `pip` package manager available.

### Setup Steps
1. **Transfer the files** to your RHEL 8 host.
2. **Create a Virtual Environment**:
   ```bash
   python3.6 -m venv venv
   source venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Start the Application**:
   ```bash
   python app.py
   ```
   The application will start on `http://0.0.0.0:5000`. The SQLite database (`healthchecks.db`) will be created automatically on the first run.

---

## 💻 Testing Locally on Windows (Development)

You can easily test the UI and run local simulated checks directly on your Windows machine.

### Prerequisites
- Python 3.6 or newer installed on your Windows machine.
- Git or a terminal to navigate to the project directory.

### Setup Steps
1. **Open PowerShell or Command Prompt** and navigate to the project folder (`c:\Users\AskiT\source\repos\SODChecks`).
2. **Create a Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
   *Note: If you run into issues installing `paramiko` or `psutil` on a newer Python version on Windows, you may need to upgrade pip first: `python -m pip install --upgrade pip`.*
4. **Start the Application**:
   ```powershell
   python app.py
   ```
5. **Access the App**: Open your browser and navigate to `http://localhost:5000`.

### Running Simulated Checks on Windows
While the app uses standard Linux commands (`ps`, `grep`, `tail`) under the hood for remote SSH targets, you can still test the UI on Windows. 
- You can add mock checks in the `/config` page.
- Note that local process checks or local log parsing relying on `grep`/`ps` will likely fail if run against "localhost" on Windows, because Windows uses different commands. For testing the actual check logic on Windows, use SSH checks targeted at an accessible Linux VM.

---

## 🛠️ Usage Guide

1. **Dashboard (`/`)**: Displays the overall system status and individual status cards for all configured checks. 
2. **Configuration (`/config`)**: 
   - Add new checks (Log Pattern or Process Stats).
   - Specify the target Host (IP or hostname).
   - For remote SSH execution, provide the **SSH User** and **SSH Key Path** (e.g., `/home/user/.ssh/id_rsa`).
   - Enable scheduling (Hourly, Daily, Weekly) or leave unchecked for manual triggers.
3. **History (`/history`)**: View historical execution data from the last 30 days.

## Notes on Architecture
- **Strict Overall Status**: If a single check reports as `FAIL` or `ERROR`, the overall status on the dashboard will turn Red/Fail.
- **Extensibility**: To add new types of checks, you can inherit from `BaseCheckRunner` in `runners.py` and register the new category in the database schema.
