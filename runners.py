import subprocess
import paramiko
import re
import datetime
import os
import json
import utils
from models import HealthCheck
from encryption_utils import decrypt_password

class BaseCheckRunner:
    """
    Base class for all health check runners.
    It provides the basic structure and a helper function to run commands locally or over SSH.
    """
    def __init__(self, check: HealthCheck):
        self.check = check

    def run(self):
        """Executes the check and returns (status, message, metrics_dict)"""
        raise NotImplementedError("Subclasses must implement run()")

    def _execute_command(self, command: str) -> tuple:
        """
        Executes a command locally or remotely via SSH based on the host.
        Returns: (stdout, stderr, return_code)
        """
        host = self.check.host.lower()
        
        # Check if the host is local
        if host in ('localhost', '127.0.0.1', '0.0.0.0'):
            # Run the command locally using Python's subprocess module
            try:
                result = subprocess.run(
                    command, shell=True, 
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                    text=True, timeout=30
                )
                return result.stdout, result.stderr, result.returncode
            except Exception as e:
                return "", str(e), -1
        else:
            # Run the command remotely via SSH
            try:
                ssh = paramiko.SSHClient()
                ssh.load_system_host_keys()
                # Strict banking security requirement: reject unknown hosts to prevent MITM
                ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
                
                user = self.check.ssh_user
                
                pwd = None
                if getattr(self.check, 'encrypted_password', None):
                    pwd = decrypt_password(self.check.encrypted_password)

                connect_kwargs = {'username': user, 'timeout': 10}
                if pwd:
                    connect_kwargs['password'] = pwd
                else:
                    key_path = self.check.ssh_key_path
                    if not key_path or not os.path.exists(key_path):
                        key_path = os.path.expanduser('~/.ssh/id_rsa')
                    connect_kwargs['key_filename'] = key_path
                
                ssh.connect(host, **connect_kwargs)
                stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
                
                out = stdout.read().decode('utf-8')
                err = stderr.read().decode('utf-8')
                exit_status = stdout.channel.recv_exit_status()
                
                ssh.close()
                return out, err, exit_status
            except Exception as e:
                return "", str(e), -1

class LogPatternCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Searches for a specific pattern in the target log file on a Linux RHEL8 system.
        """
        pattern = self.check.search_pattern
        target = self.check.target_path
        
        if not pattern or not target:
            return "ERROR", "Missing target path or search pattern.", {}

        # Escape single quotes so the command doesn't break in bash
        safe_pattern = pattern.replace("'", "'\\''")
        
        # Command checks the last 500 lines of a file for the pattern
        cmd = f"tail -n 500 {target} | grep -E '{safe_pattern}'"
        
        stdout, stderr, rc = self._execute_command(cmd)
        
        if rc == 0 and stdout.strip():
            # Pattern was found successfully
            lines = stdout.strip().split('\n')
            matched_line = lines[-1] if lines else ""
            return "PASS", "Pattern found.", {"matched_line": matched_line}
        elif rc == 1:
            # grep returns 1 if no lines match
            return "FAIL", "Pattern not found in the recent log entries.", {}
        else:
            # Any other return code usually implies an error (e.g., file not found)
            return "ERROR", f"Failed to read log: {stderr.strip()}", {}

class ProcessCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Verifies a process is running on Linux RHEL8, gets uptime and memory consumption.
        The target can be a process ID (PID) or a process name.
        """
        target = self.check.target_path
        
        if not target:
            return "ERROR", "Missing process name or PID.", {}

        # Check if target is just numbers (meaning it's a Process ID / PID)
        if target.isdigit():
            cmd = f"ps -p {target} -o pid=,etime=,rss="
        else:
            # Target is a string (Process Name)
            safe_target = target.replace("'", "'\\''")
            cmd = f"ps -o pid=,etime=,rss= -p $(pgrep -f '{safe_target}') 2>/dev/null | head -n 1"
        
        # Execute the command
        stdout, stderr, rc = self._execute_command(cmd)
        
        # Parse the output
        if stdout and stdout.strip():
            parts = stdout.strip().split()
            # ps command outputs: PID, Elapsed Time (etime), Memory in KB (rss)
            if len(parts) >= 3:
                pid = parts[0]
                etime = parts[1]
                rss_kb = parts[2]
                try:
                    # Convert KB to MB for easier reading
                    memory_mb = round(int(rss_kb) / 1024, 2)
                except ValueError:
                    memory_mb = 0
                return "PASS", f"Process is running (PID: {pid}).", {"uptime": etime, "memory_mb": memory_mb}
        
        # Process not found
        return "FAIL", f"Process '{target}' is not running.", {}

class EmailCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Sends an email with dashboard statistics.
        """
        # Parse comma-separated email addresses
        target_emails = self.check.target_path
        to_emails = [e.strip() for e in target_emails.split(',')] if target_emails else []
        
        subject = self.check.name or "Dashboard Stats"
        body_html = "<h1>Dashboard Stats</h1><p>Placeholder for dashboard stats.</p>"
        
        try:
            utils.send_email(subject, body_html, to_emails)
            return "PASS", "Email sent successfully", {}
        except Exception as e:
            return "ERROR", f"Failed to send email: {str(e)}", {}

class TeamsNotificationCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Sends a notification to Microsoft Teams.
        """
        message = self.check.search_pattern or "Teams Notification Sample"
        
        try:
            output = utils.sendChat(message)
            return "PASS", "Teams notification sent successfully", {"output": output}
        except Exception as e:
            return "ERROR", f"Failed to send Teams notification: {str(e)}", {}

class LinuxCommandCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Runs any raw command directly on the Linux target host.
        """
        host = self.check.host
        command = self.check.target_path
        user = self.check.ssh_user
        pwd = decrypt_password(self.check.encrypted_password) if self.check.encrypted_password else None
        key_path = self.check.ssh_key_path
        
        try:
            out, err, rc = utils.run_linux_command(host, command, user, pwd, key_path)
            if rc == 0:
                return "PASS", "Command executed successfully", {"stdout": out.strip()}
            else:
                return "FAIL", f"Command failed with rc {rc}", {"stderr": err.strip()}
        except Exception as e:
            return "ERROR", f"Failed to execute command: {str(e)}", {}

class WindowsCommandCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Runs a command on a Windows target host using WinRM.
        """
        host = self.check.host
        command = self.check.target_path
        user = self.check.ssh_user
        pwd = decrypt_password(self.check.encrypted_password) if self.check.encrypted_password else None
        
        if not user or not pwd:
            return "ERROR", "Windows Command requires user and password.", {}
            
        try:
            out, err, rc = utils.run_windows_command(host, command, user, pwd)
            if rc == 0:
                return "PASS", "Windows command executed successfully", {"stdout": out.strip()}
            else:
                return "FAIL", f"Windows command failed with rc {rc}", {"stderr": err.strip()}
        except Exception as e:
            return "ERROR", f"Failed to execute windows command: {str(e)}", {}

class JsonToHtmlCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Converts a JSON string into an HTML table.
        """
        json_data = self.check.search_pattern
        if not json_data:
            return "ERROR", "No JSON data provided in search_pattern.", {}
            
        try:
            html = utils.json_to_html_table(json_data)
            return "PASS", "JSON converted to HTML", {"html": html}
        except Exception as e:
            return "ERROR", f"Failed to convert JSON to HTML: {str(e)}", {}

class HtmlToJsonCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Converts an HTML table into a JSON string.
        """
        html_data = self.check.search_pattern
        if not html_data:
            return "ERROR", "No HTML data provided in search_pattern.", {}
            
        try:
            json_str = utils.html_table_to_json(html_data)
            return "PASS", "HTML converted to JSON", {"json": json_str}
        except Exception as e:
            return "ERROR", f"Failed to convert HTML to JSON: {str(e)}", {}

class OracleQueryCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Connects to an Oracle DB and executes a query, returning an HTML table.
        """
        host = self.check.host
        port = "1521"
        if ":" in host:
            host, port = host.split(":", 1)
            
        service_name = self.check.target_path
        user = self.check.ssh_user
        pwd = decrypt_password(self.check.encrypted_password) if self.check.encrypted_password else None
        query = self.check.search_pattern
        
        if not user or not pwd or not query or not service_name:
            return "ERROR", "Oracle check requires host, service_name (target_path), user, password, and query (search_pattern)", {}
            
        try:
            html_table = utils.run_oracle_query(host, port, service_name, user, pwd, query)
            return "PASS", "Oracle query executed successfully", {"html": html_table}
        except Exception as e:
            return "ERROR", str(e), {}

class MssqlQueryCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Connects to an MS SQL Server and executes a query, returning an HTML table.
        """
        host = self.check.host
        port = "1433"
        if ":" in host:
            host, port = host.split(":", 1)
            
        database = self.check.target_path
        user = self.check.ssh_user 
        pwd = decrypt_password(self.check.encrypted_password) if self.check.encrypted_password else None
        query = self.check.search_pattern
        
        if not user or not pwd or not query or not database:
            return "ERROR", "MSSQL check requires host, database (target_path), user, password, and query (search_pattern)", {}
            
        try:
            html_table = utils.run_mssql_query(host, port, database, user, pwd, query)
            return "PASS", "MSSQL query executed successfully", {"html": html_table}
        except Exception as e:
            return "ERROR", str(e), {}

class SybaseQueryCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Connects to a Sybase DB and executes a query, returning an HTML table.
        """
        host = self.check.host
        port = "5000"
        if ":" in host:
            host, port = host.split(":", 1)
            
        database = self.check.target_path 
        user = self.check.ssh_user 
        pwd = decrypt_password(self.check.encrypted_password) if self.check.encrypted_password else None
        query = self.check.search_pattern
        
        if not user or not pwd or not query or not database:
            return "ERROR", "Sybase check requires host, database (target_path), user, password, and query (search_pattern)", {}
            
        try:
            html_table = utils.run_sybase_query(host, port, database, user, pwd, query)
            return "PASS", "Sybase query executed successfully", {"html": html_table}
        except Exception as e:
            return "ERROR", str(e), {}

class GemfireOqlCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Executes an OQL query via the GemFire REST API, returning an HTML table.
        """
        host = self.check.host # Expected format: http://gemfire-rest-api:8080
        user = self.check.ssh_user 
        pwd = decrypt_password(self.check.encrypted_password) if self.check.encrypted_password else None
        query = self.check.search_pattern
        
        if not host or not query:
            return "ERROR", "GemFire check requires Host (REST API URL) and Query (search_pattern)", {}
            
        try:
            html_table = utils.run_gemfire_oql(host, user, pwd, query)
            return "PASS", "GemFire OQL query executed successfully", {"html": html_table}
        except Exception as e:
            return "ERROR", str(e), {}

def execute_check(check: HealthCheck):
    """Factory to execute the right runner based on category"""
    category_name = check.category.name if check.category else ""
    
    if category_name == 'log_pattern':
        runner = LogPatternCheckRunner(check)
    elif category_name == 'process_stats':
        runner = ProcessCheckRunner(check)
    elif category_name == 'send_email':
        runner = EmailCheckRunner(check)
    elif category_name == 'teams_notification':
        runner = TeamsNotificationCheckRunner(check)
    elif category_name == 'linux_command':
        runner = LinuxCommandCheckRunner(check)
    elif category_name == 'windows_command':
        runner = WindowsCommandCheckRunner(check)
    elif category_name == 'json_to_html':
        runner = JsonToHtmlCheckRunner(check)
    elif category_name == 'html_to_json':
        runner = HtmlToJsonCheckRunner(check)
    elif category_name == 'oracle_query':
        runner = OracleQueryCheckRunner(check)
    elif category_name == 'mssql_query':
        runner = MssqlQueryCheckRunner(check)
    elif category_name == 'sybase_query':
        runner = SybaseQueryCheckRunner(check)
    elif category_name == 'gemfire_oql':
        runner = GemfireOqlCheckRunner(check)
    else:
        return "ERROR", f"Unknown category: {category_name}", {}
        
    return runner.run()

