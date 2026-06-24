import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from runners import LinuxCommandCheckRunner

class DummyHealthCheck:
    def __init__(self):
        self.host = "localhost" # Connect back to localhost (requires SSH server to be running on localhost)
        self.target_path = "uname -a" # Command to run
        self.ssh_user = os.getlogin() if hasattr(os, 'getlogin') else "user" # Current local user
        
        # If testing locally, you might use your SSH key
        key_path = os.path.expanduser("~/.ssh/id_rsa")
        self.ssh_key_path = key_path if os.path.exists(key_path) else None
        self.encrypted_password = None

def run_test():
    check = DummyHealthCheck()
    runner = LinuxCommandCheckRunner(check)
    
    print(f"\n--- Running LinuxCommandCheckRunner ---")
    print(f"Executing command: {check.target_path} on {check.host}")
    
    # Note: If SSH isn't set up on localhost or the key/user is invalid, this will fail.
    # It catches the failure and displays it safely.
    status, message, metrics = runner.run()
    
    print(f"\n--- Results ---")
    print(f"Status: {status}")
    print(f"Message: {message}")
    print(f"Metrics: {metrics}")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
