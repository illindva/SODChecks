import subprocess
import paramiko
import re
import datetime
import os
from models import HealthCheck

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
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Assuming key-based authentication per user requirements
                key_path = self.check.ssh_key_path
                user = self.check.ssh_user
                if not key_path or not os.path.exists(key_path):
                    # Try default key if not specified
                    key_path = os.path.expanduser('~/.ssh/id_rsa')
                
                ssh.connect(host, username=user, key_filename=key_path, timeout=10)
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
        Uses tail and grep. e.g. tail -n 1000 /path/to/log | grep 'PATTERN'
        """
        pattern = self.check.search_pattern
        target = self.check.target_path
        
        if not pattern or not target:
            return "ERROR", "Missing target path or search pattern.", {}

        # Escape pattern for safety
        safe_pattern = pattern.replace("'", "'\\''")
        
        # Command checks last 500 lines for the pattern
        cmd = f"tail -n 500 {target} | grep -E '{safe_pattern}'"
        
        stdout, stderr, rc = self._execute_command(cmd)
        
        if rc == 0 and stdout.strip():
            # Pattern found
            lines = stdout.strip().split('\n')
            matched_line = lines[-1] if lines else ""
            return "PASS", f"Pattern found.", {"matched_line": matched_line}
        elif rc == 1:
            # grep found nothing
            return "FAIL", "Pattern not found in the recent log entries.", {}
        else:
            # Error executing (e.g., file not found, permission denied)
            return "ERROR", f"Failed to read log: {stderr}", {}

class ProcessCheckRunner(BaseCheckRunner):
    def run(self):
        """
        Verifies process is running, gets uptime and memory consumption.
        Target path is treated as the process name or exact PID.
        Uses ps command.
        """
        target = self.check.target_path
        
        if not target:
            return "ERROR", "Missing process name or PID.", {}

        # Look for process by name (using pgrep) or if it's a digit, assume PID.
        # Format output: PID, ELAPSED (uptime), RSS (memory in KB)
        if target.isdigit():
            # It's a PID
            cmd = f"ps -p {target} -o pid=,etime=,rss="
        else:
            # It's a name, use pgrep to get PIDs, then ps. Get the oldest one if multiple.
            safe_target = target.replace("'", "'\\''")
            cmd = f"ps -o pid=,etime=,rss= -p $(pgrep -f '{safe_target}') 2>/dev/null | head -n 1"
        
        stdout, stderr, rc = self._execute_command(cmd)
        
        if stdout and stdout.strip():
            parts = stdout.strip().split()
            if len(parts) >= 3:
                pid = parts[0]
                etime = parts[1] # e.g. "01:23:45" or "2-01:23:45" (days-hh:mm:ss)
                rss_kb = parts[2]
                
                try:
                    memory_mb = round(int(rss_kb) / 1024, 2)
                except ValueError:
                    memory_mb = 0
                
                return "PASS", f"Process is running (PID: {pid}).", {"uptime": etime, "memory_mb": memory_mb}
        
        # If output is empty or process not found
        return "FAIL", f"Process '{target}' is not running.", {}

def execute_check(check: HealthCheck):
    """Factory to execute the right runner based on category"""
    category_name = check.category.name if check.category else ""
    
    if category_name == 'log_pattern':
        runner = LogPatternCheckRunner(check)
    elif category_name == 'process_stats':
        runner = ProcessCheckRunner(check)
    else:
        return "ERROR", f"Unknown category: {category_name}", {}
        
    return runner.run()
