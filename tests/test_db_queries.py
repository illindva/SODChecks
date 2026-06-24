import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from runners import OracleQueryCheckRunner

class DummyHealthCheck:
    def __init__(self):
        self.host = "localhost"
        self.target_path = "ORCL" # Database / Service Name
        self.ssh_user = "db_user"
        self.search_pattern = "SELECT * FROM dual;" # Query
        self.encrypted_password = None

def run_test():
    check = DummyHealthCheck()
    
    # We use OracleQueryCheckRunner as an example, but this could be MSSQL/Sybase/GemFire
    runner = OracleQueryCheckRunner(check)
    
    print(f"\n--- Running OracleQueryCheckRunner ---")
    print(f"Executing Query: {check.search_pattern} on DB: {check.target_path}")
    
    # Note: Since there is likely no actual database configured locally,
    # this test will fail, but it demonstrates how to call and test it.
    status, message, metrics = runner.run()
    
    print(f"\n--- Results ---")
    print(f"Status: {status}")
    print(f"Message: {message}")
    print(f"Metrics: {metrics}")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
