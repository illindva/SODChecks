import sys
import os

# Add the parent directory to the python path so we can import runners
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from runners import GemfireOqlCheckRunner

class DummyHealthCheck:
    def __init__(self):
        # GemFire REST API URL
        self.host = "http://localhost:8080" 
        # Sample OQL query
        self.search_pattern = "SELECT * FROM /customers WHERE id = '12345'" 
        # Optional credentials if the REST API is secured
        self.ssh_user = "gemfire_user" 
        self.encrypted_password = None # We would normally decrypt this

def run_test():
    check = DummyHealthCheck()
    runner = GemfireOqlCheckRunner(check)
    
    print(f"\n--- Running GemfireOqlCheckRunner ---")
    print(f"Target URL: {check.host}")
    print(f"OQL Query: {check.search_pattern}")
    
    # Note: Since there is likely no actual GemFire REST API running on localhost:8080,
    # this test will safely fail and output the connection error. 
    # It demonstrates the expected parameters and flow.
    status, message, metrics = runner.run()
    
    print(f"\n--- Results ---")
    print(f"Status: {status}")
    print(f"Message: {message}")
    print(f"Metrics: {metrics}")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
