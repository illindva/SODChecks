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
    def __init__(self, check: HealthCheck):
        self.check = check

    def run(self):
        """Executes the check and returns (status, message, metrics_dict)"""
        raise NotImplementedError("Subclasses must implement run()")

    def _execute_command(self, command: str) -> tuple:
        """Executes a command locally or remotely via SSH based on the host.
        Returns (stdout, stderr, return_code)
        """
        host = self.check.host.lower()
        if host in ('localhost', '127.0.0.1', '0.0.0.0'):
            # Local execution
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
            # Remote execution via SSH
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
        Searches for a specific pattern in the target log file.
        """
        pattern = self.check.search_pattern
        target = self.check.target_path
        os_type = getattr(self.check, 'os_type', 'linux').lower()
        
        if not pattern or not target:
            return "ERROR", "Missing target path or search pattern.", {}

        if os_type == 'windows':
            ps_pattern = pattern.replace("'", "''")
            cmd = f'powershell -Command "Get-Content -Path \'{target}\' -Tail 500 | Select-String -Pattern \'{ps_pattern}\' -Quiet"'
        else:
            safe_pattern = pattern.replace("'", "'\\''")
            cmd = f"tail -n 500 {target} | grep -E '{safe_pattern}'"
        
        stdout, stderr, rc = self._execute_command(cmd)
        
        if os_type == 'windows':
            if "True" in stdout:
                return "PASS", "Pattern found.", {"matched_line": "Found"}
            elif rc != 0 or "False" in stdout:
                if stderr.strip():
                    return "ERROR", f"Failed to read log: {stderr}", {}
                return "FAIL", "Pattern not found in the recent log entries.", {}
            return "ERROR", f"Failed to read log.", {}
        else:
            if rc == 0 and stdout.strip():
                lines = stdout.strip().split('\n')
                matched_line = lines[-1] if lines else ""
                return "PASS", f"Pattern found.", {"matched_line": matched_line}
            elif rc == 1:
                return "FAIL", "Pattern not found in the recent log entries.", {}
            else:
                return "ERROR", f"Failed to read log: {stderr}", {}

class ProcessCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Verifies process is running, gets uptime and memory consumption.
        """
        target = self.check.target_path
        os_type = getattr(self.check, 'os_type', 'linux').lower()
        
        if not target:
            return "ERROR", "Missing process name or PID.", {}

        if os_type == 'windows':
            if target.isdigit():
                cmd = f'powershell -Command "Get-Process -Id {target} -ErrorAction SilentlyContinue | Select-Object Id, StartTime, WorkingSet | ConvertTo-Json"'
            else:
                cmd = f'powershell -Command "Get-Process -Name \'{target}\' -ErrorAction SilentlyContinue | Select-Object -First 1 Id, StartTime, WorkingSet | ConvertTo-Json"'
            
            stdout, stderr, rc = self._execute_command(cmd)
            
            if stdout and stdout.strip():
                try:
                    data = json.loads(stdout.strip())
                    if not data:
                        return "FAIL", f"Process '{target}' is not running.", {}
                    pid = data.get('Id')
                    memory_mb = round((data.get('WorkingSet', 0) or 0) / 1024 / 1024, 2)
                    return "PASS", f"Process is running (PID: {pid}).", {"memory_mb": memory_mb}
                except Exception as e:
                    return "ERROR", f"Failed to parse process data: {e}", {}
            return "FAIL", f"Process '{target}' is not running.", {}
        else:
            if target.isdigit():
                cmd = f"ps -p {target} -o pid=,etime=,rss="
            else:
                safe_target = target.replace("'", "'\\''")
                cmd = f"ps -o pid=,etime=,rss= -p $(pgrep -f '{safe_target}') 2>/dev/null | head -n 1"
            
            stdout, stderr, rc = self._execute_command(cmd)
            
            if stdout and stdout.strip():
                parts = stdout.strip().split()
                if len(parts) >= 3:
                    pid = parts[0]
                    etime = parts[1]
                    rss_kb = parts[2]
                    try:
                        memory_mb = round(int(rss_kb) / 1024, 2)
                    except ValueError:
                        memory_mb = 0
                    return "PASS", f"Process is running (PID: {pid}).", {"uptime": etime, "memory_mb": memory_mb}
            
        return "FAIL", f"Process '{target}' is not running.", {}

class EmailCheckRunner(BaseCheckRunner):
    def run(self):
        # target_path can store comma separated emails
        to_emails = [e.strip() for e in self.check.target_path.split(',') if e.strip()] if self.check.target_path else []
        subject = self.check.name or "Dashboard Stats"
        body_html = "<h1>Dashboard Stats</h1><p>Placeholder for dashboard stats.</p>"
        
        try:
            utils.send_email(subject, body_html, to_emails)
            return "PASS", "Email sent successfully", {}
        except Exception as e:
            return "ERROR", f"Failed to send email: {str(e)}", {}

class TeamsNotificationCheckRunner(BaseCheckRunner):
    def run(self):
        # search_pattern can store the message text
        message = self.check.search_pattern or "Teams Notification Sample"
        
        try:
            output = utils.sendChat(message)
            return "PASS", "Teams notification sent successfully", {"output": output}
        except Exception as e:
            return "ERROR", f"Failed to send Teams notification: {str(e)}", {}

class LinuxCommandCheckRunner(BaseCheckRunner):
    def run(self):
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
        # search_pattern stores JSON string
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
        # search_pattern stores HTML string
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
        host = self.check.host
        # For db queries, host can be host:port. If port is separate or implied, we can parse it.
        # Assuming format 'host:port' or just 'host' with default 1521
        port = "1521"
        if ":" in host:
            host, port = host.split(":", 1)
            
        service_name = self.check.target_path # We'll use target_path for service_name
        user = self.check.ssh_user # Database user
        pwd = decrypt_password(self.check.encrypted_password) if self.check.encrypted_password else None
        query = self.check.search_pattern # The SQL query
        
        if not user or not pwd or not query or not service_name:
            return "ERROR", "Oracle check requires host, service_name (target_path), user, password, and query (search_pattern)", {}
            
        try:
            html_table = utils.run_oracle_query(host, port, service_name, user, pwd, query)
            return "PASS", "Oracle query executed successfully", {"html": html_table}
        except Exception as e:
            return "ERROR", str(e), {}

class MssqlQueryCheckRunner(BaseCheckRunner):
    def run(self):
        host = self.check.host
        port = "1433"
        if ":" in host:
            host, port = host.split(":", 1)
            
        database = self.check.target_path # database name
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
        host = self.check.host
        port = "5000" # Default sybase port
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
    elif category_name == 'send_email_sample':
        runner = EmailCheckRunner(check)
    elif category_name == 'teams_notification_sample':
        runner = TeamsNotificationCheckRunner(check)
    elif category_name == 'linux_command_sample':
        runner = LinuxCommandCheckRunner(check)
    elif category_name == 'windows_command_sample':
        runner = WindowsCommandCheckRunner(check)
    elif category_name == 'json_to_html_sample':
        runner = JsonToHtmlCheckRunner(check)
    elif category_name == 'html_to_json_sample':
        runner = HtmlToJsonCheckRunner(check)
    elif category_name == 'oracle_query_sample':
        runner = OracleQueryCheckRunner(check)
    elif category_name == 'mssql_query_sample':
        runner = MssqlQueryCheckRunner(check)
    elif category_name == 'sybase_query_sample':
        runner = SybaseQueryCheckRunner(check)
    elif category_name == 'gemfire_oql_sample':
        runner = GemfireOqlCheckRunner(check)
    else:
        return "ERROR", f"Unknown category: {category_name}", {}
        
    return runner.run()
