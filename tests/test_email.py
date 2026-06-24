import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from runners import EmailCheckRunner

class DummyHealthCheck:
    def __init__(self):
        self.host = "localhost"
        self.name = "Test Dashboard Stats"
        self.target_path = "test1@example.com, test2@example.com" # Comma separated emails

def run_test():
    check = DummyHealthCheck()
    runner = EmailCheckRunner(check)
    
    print(f"\n--- Running EmailCheckRunner ---")
    print(f"Target Emails: {check.target_path}")
    
    # Note: Since utils.send_email actually tries to connect to an SMTP server,
    # running this without an SMTP server configured in utils.py may result in an ERROR status.
    # This test will safely catch and display that error.
    status, message, metrics = runner.run()
    
    print(f"\n--- Results ---")
    print(f"Status: {status}")
    print(f"Message: {message}")
    print(f"Metrics: {metrics}")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
