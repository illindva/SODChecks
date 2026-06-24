import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from runners import TeamsNotificationCheckRunner

class DummyHealthCheck:
    def __init__(self):
        self.host = "localhost"
        self.search_pattern = "Hello from Local Test Script!" # Message to send

def run_test():
    check = DummyHealthCheck()
    runner = TeamsNotificationCheckRunner(check)
    
    print(f"\n--- Running TeamsNotificationCheckRunner ---")
    print(f"Message Content: {check.search_pattern}")
    
    # Note: If no Teams Webhook URL is configured in utils.py, this may fail.
    # It safely catches the error and outputs it.
    status, message, metrics = runner.run()
    
    print(f"\n--- Results ---")
    print(f"Status: {status}")
    print(f"Message: {message}")
    print(f"Metrics: {metrics}")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
